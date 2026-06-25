"""BLE client wrapper for the Soehnle AC500 integration."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    COMMANDS,
    UUID_EF02,
    UUID_EF03,
    UUID_EF04,
    UUID_FFD2,
    UUID_FFD3,
    UUID_FFD4,
    UUID_FFD5,
    UUID_FFF1,
    UUID_HEARTBEAT_READ,
    UUID_WRITE,
)
from .models import SoehnleAc500State

LOGGER = logging.getLogger(__name__)


class SoehnleAc500BleClient:
    """Encapsulates BLE transport and protocol interaction."""

    def __init__(self, hass: HomeAssistant, address: str, name: str) -> None:
        self._hass = hass
        self._address = address
        self._name = name
        self._client: BleakClientWithServiceCache | None = None
        self._lock = asyncio.Lock()
        self._callbacks: list[Callable[[], None]] = []
        self.state = SoehnleAc500State()
        self._last_notify_ts = 0.0
        self._last_activity_ts = 0.0

    @property
    def address(self) -> str:
        """Return the normalized Bluetooth address."""
        return self._address

    @property
    def is_connected(self) -> bool:
        """Return whether the BLE link is currently active."""
        return bool(self._client and self._client.is_connected)

    @property
    def last_notify_ts(self) -> float:
        """Return the last monotonic timestamp that came from a notify frame."""
        return self._last_notify_ts

    @property
    def last_activity_ts(self) -> float:
        """Return the last monotonic timestamp of successful BLE activity."""
        return self._last_activity_ts

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register a state-change callback."""
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[], None]) -> None:
        """Unregister a state-change callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def async_connect(self) -> bool:
        """Connect to the device and subscribe to notifications."""
        if self._client is not None and self._client.is_connected:
            return True

        ble_device = bluetooth.async_ble_device_from_address(
            self._hass,
            self._address,
            connectable=True,
        )
        if ble_device is None:
            LOGGER.debug("AC500 BLE device %s is not available", self._address)
            self.state.connected = False
            self._notify_home_assistant()
            return False

        try:
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                ble_device,
                self._name,
                disconnected_callback=self._handle_disconnect,
                max_attempts=3,
                use_services_cache=True,
            )
            await self._client.start_notify(UUID_EF02, self._handle_ef02)
            await self._client.start_notify(UUID_EF04, self._handle_ef04)
            try:
                await self._client.start_notify(UUID_EF03, self._handle_ef03)
            except BleakError as err:
                LOGGER.warning("AC500 EF03 not available: %s", err)

            await self._read_d0ff_chars()
            self.state.connected = True
            self._touch_activity()
            self._notify_home_assistant()
            LOGGER.info("AC500 connected via bleak_retry_connector")
            return True
        except (BleakError, Exception) as err:
            LOGGER.error("AC500 connect failed: %s", err)
            self._client = None
            self.state.connected = False
            self._notify_home_assistant()
            return False

    async def async_disconnect(self) -> None:
        """Disconnect and clear the active BLE client."""
        if self._client is not None and self._client.is_connected:
            try:
                await self._client.stop_notify(UUID_EF02)
            except Exception:
                pass
            try:
                await self._client.stop_notify(UUID_EF04)
            except Exception:
                pass
            try:
                await self._client.stop_notify(UUID_EF03)
            except Exception:
                pass
            try:
                await self._client.disconnect()
            except BleakError:
                pass

        self._client = None
        self.state.connected = False
        self._notify_home_assistant()

    async def async_send_heartbeat(self) -> bool:
        """Perform a safe read to keep the GATT session active."""
        if not await self.async_connect():
            return False

        if self._client is None:
            return False

        try:
            await self._client.read_gatt_char(UUID_HEARTBEAT_READ)
        except (BleakError, Exception) as err:
            LOGGER.warning("AC500 heartbeat read failed: %s", err)
            self.state.connected = False
            self._notify_home_assistant()
            return False

        self._touch_activity()
        LOGGER.debug("AC500 heartbeat read succeeded")
        return True

    async def async_write_command(self, command_key: str) -> bool:
        """Write one of the predefined protocol commands."""
        hex_command = COMMANDS.get(command_key)
        if hex_command is None:
            LOGGER.error("Unknown AC500 command: %s", command_key)
            return False

        async with self._lock:
            if not await self.async_connect():
                LOGGER.warning("Cannot send %s while disconnected", command_key)
                return False

            if self._client is None:
                return False

            try:
                await self._client.write_gatt_char(
                    UUID_WRITE,
                    bytearray.fromhex(hex_command),
                    response=False,
                )
                self._touch_activity()
                LOGGER.debug("Sent %s (%s)", command_key, hex_command)
                return True
            except BleakError as err:
                LOGGER.error("Write failed for %s: %s", command_key, err)
                self.state.connected = False
                self._notify_home_assistant()
                return False

    async def _read_d0ff_chars(self) -> None:
        """Read static/raw characteristics after connecting."""
        if self._client is None:
            return

        changed = False
        for name, uuid in (
            ("ffd2", UUID_FFD2),
            ("ffd3", UUID_FFD3),
            ("ffd4", UUID_FFD4),
            ("ffd5", UUID_FFD5),
            ("fff1", UUID_FFF1),
        ):
            try:
                data = bytes(await self._client.read_gatt_char(uuid))
            except BleakError as err:
                LOGGER.warning("AC500 read %s failed: %s", name.upper(), err)
                continue

            value = data.hex()
            attribute = f"{name}_raw_hex"
            if getattr(self.state, attribute) != value:
                setattr(self.state, attribute, value)
                changed = True

        if changed:
            self._notify_home_assistant()

    def _handle_disconnect(self, _client: Any) -> None:
        """Handle an unexpected disconnect from the BLE stack."""
        self._client = None
        self.state.connected = False
        self._hass.loop.call_soon_threadsafe(self._notify_home_assistant)

    def _handle_ef02(self, _characteristic: Any, data: bytearray) -> None:
        """Handle EF02 notifications."""
        payload = bytes(data)
        self._touch_notify()
        LOGGER.debug("EF02 raw (%d bytes): %s", len(payload), payload.hex())
        if self.state.parse_ef02(payload):
            self._hass.loop.call_soon_threadsafe(self._notify_home_assistant)

    def _handle_ef03(self, _characteristic: Any, data: bytearray) -> None:
        """Handle EF03 notifications."""
        self._touch_notify()
        payload = bytes(data).hex()
        if self.state.ef03_raw_hex != payload:
            self.state.ef03_raw_hex = payload
            self._hass.loop.call_soon_threadsafe(self._notify_home_assistant)

    def _handle_ef04(self, _characteristic: Any, data: bytearray) -> None:
        """Handle EF04 notifications."""
        payload = bytes(data)
        self._touch_notify()
        LOGGER.debug("EF04 raw (%d bytes): %s", len(payload), payload.hex())
        if len(payload) > 2 and self.state.parse_ef04(payload):
            self._hass.loop.call_soon_threadsafe(self._notify_home_assistant)

    def _touch_activity(self) -> None:
        """Record successful BLE transport activity."""
        self._last_activity_ts = time.monotonic()

    def _touch_notify(self) -> None:
        """Record successful notify traffic."""
        now = time.monotonic()
        self._last_notify_ts = now
        self._last_activity_ts = now

    def _notify_home_assistant(self) -> None:
        """Fan out state changes to registered callbacks."""
        for callback in tuple(self._callbacks):
            try:
                callback()
            except Exception as err:
                LOGGER.error("Callback error: %s", err)
