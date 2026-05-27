"""Thin BLE client wrapper for notify and write operations."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import NOTIFY_CHARACTERISTIC_UUID, WRITE_CHARACTERISTIC_UUID

if TYPE_CHECKING:
    from bleak.backends.characteristic import BleakGATTCharacteristic


class LeifheitBleClient:
    """Encapsulates the BLE connection details for the integration."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        name: str,
        on_notification: Callable[[bytes], None],
        on_disconnect: Callable[[], None] | None = None,
    ) -> None:
        self._hass = hass
        self._address = address
        self._name = name
        self._on_notification = on_notification
        self._on_disconnect = on_disconnect
        self._client: BleakClientWithServiceCache | None = None
        self._is_connected = False

    @property
    def is_connected(self) -> bool:
        """Return whether the client is currently connected."""
        return self._is_connected

    async def async_connect(self) -> None:
        """Connect and subscribe to the device's notify characteristic."""
        if self._client is not None and self._client.is_connected:
            return

        ble_device = bluetooth.async_ble_device_from_address(
            self._hass,
            self._address,
            connectable=True,
        )
        if ble_device is None:
            raise RuntimeError(f"BLE device {self._address} is not available")

        self._client = await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            self._name,
            disconnected_callback=self._handle_disconnect,
            max_attempts=3,
            use_services_cache=True,
        )
        self._is_connected = True
        await self._client.start_notify(
            NOTIFY_CHARACTERISTIC_UUID,
            self._handle_notification,
        )

    async def async_disconnect(self) -> None:
        """Stop notifications and disconnect from the device."""
        if self._client is None:
            self._is_connected = False
            return

        if self._client.is_connected:
            try:
                await self._client.stop_notify(NOTIFY_CHARACTERISTIC_UUID)
            except Exception:
                pass
            await self._client.disconnect()

        self._client = None
        self._is_connected = False

    async def async_write_command(self, payload: bytes, *, response: bool = False) -> None:
        """Write a payload to the device's write characteristic."""
        await self.async_connect()

        if self._client is None:
            raise RuntimeError("BLE client is not connected")

        await self._client.write_gatt_char(
            WRITE_CHARACTERISTIC_UUID,
            payload,
            response=response,
        )

    def _handle_notification(
        self,
        _characteristic: BleakGATTCharacteristic,
        data: bytearray,
    ) -> None:
        """Forward notification data back onto Home Assistant's event loop."""
        self._hass.loop.call_soon_threadsafe(self._on_notification, bytes(data))

    def _handle_disconnect(self, _client: Any) -> None:
        """Handle unexpected disconnects from the BLE stack."""
        self._client = None
        self._is_connected = False
        if self._on_disconnect is not None:
            self._hass.loop.call_soon_threadsafe(self._on_disconnect)
