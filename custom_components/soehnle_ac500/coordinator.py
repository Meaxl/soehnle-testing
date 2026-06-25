"""Coordinator and reconnect handling for the Soehnle AC500 integration."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
    async_register_callback as bt_async_register_callback,
)
from homeassistant.components.bluetooth.match import ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .models import SoehnleAc500State

LOGGER = logging.getLogger(__name__)

RECONNECT_INTERVAL = 5
HEARTBEAT_INTERVAL = 8
HEARTBEAT_FAILURES_BEFORE_RECONNECT = 3
CHECK_NIGHT_MODE_INTERVAL = 300
NIGHT_MODE_FALLBACK_INTERVAL = 60
STALE_THRESHOLD = 600


class SoehnleAc500Coordinator(DataUpdateCoordinator[SoehnleAc500State]):
    """Owns reconnects, availability and night-mode behavior."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        super().__init__(hass, logger=LOGGER, name=f"soehnle_ac500_{address}")
        self._address = address
        self._client = None
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._paused_for_night_mode = False
        self._checking_night_mode = False
        self._last_notify_ts = time.monotonic()
        self._last_activity_ts = self._last_notify_ts
        self._last_night_mode_check_ts = 0.0
        self._heartbeat_failures = 0
        self._bt_cancel_callback: Callable[[], None] | None = None
        self.async_set_updated_data(SoehnleAc500State())

    @property
    def client(self):
        """Return the attached BLE client."""
        if self._client is None:
            raise RuntimeError("Coordinator client has not been attached")
        return self._client

    @property
    def state(self) -> SoehnleAc500State:
        """Return the cached device state."""
        return self.data

    @property
    def is_stale(self) -> bool:
        """Return whether the cached state should be considered stale."""
        if not self.state.ever_seen:
            return True
        if self._paused_for_night_mode:
            return False
        return time.monotonic() - self._last_notify_ts > STALE_THRESHOLD

    def attach_client(self, client) -> None:
        """Attach the BLE client after construction."""
        self._client = client
        self._last_notify_ts = getattr(client, "last_notify_ts", 0.0) or self._last_notify_ts
        self._last_activity_ts = (
            getattr(client, "last_activity_ts", 0.0) or self._last_activity_ts
        )
        self.async_set_updated_data(client.state)

    async def async_start(self) -> None:
        """Start the background reconnect loop."""
        self._running = True
        self._task = self.hass.async_create_background_task(
            self._connection_loop(),
            name="soehnle_ac500_connection_loop",
        )

    async def async_stop(self) -> None:
        """Stop background work and disconnect the client."""
        self._running = False
        self._unregister_bt_wakeup_listener()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._client is not None:
            self._client.unregister_callback(self.async_handle_client_update)
            await self._client.async_disconnect()

    async def _async_update_data(self) -> SoehnleAc500State:
        """Return cached state for explicit refresh requests."""
        return self.data

    @callback
    def async_handle_client_update(self) -> None:
        """Push the latest client state to Home Assistant."""
        self._last_notify_ts = max(
            self._last_notify_ts,
            getattr(self.client, "last_notify_ts", 0.0),
        )
        self._last_activity_ts = max(
            self._last_activity_ts,
            getattr(self.client, "last_activity_ts", 0.0),
        )
        state = self.client.state
        if state.night and not self._paused_for_night_mode and not self._checking_night_mode:
            self.hass.async_create_task(self.pause_for_night_mode())
        self.async_set_updated_data(state)

    async def pause_for_night_mode(self) -> None:
        """Pause reconnect attempts while the purifier is in night mode."""
        if self._paused_for_night_mode:
            return
        self._paused_for_night_mode = True
        self._last_night_mode_check_ts = time.monotonic()
        await self.client.async_disconnect()
        self._register_bt_wakeup_listener()
        self.async_update_listeners()
        LOGGER.debug("AC500 paused for night mode")

    def resume_from_night_mode(self) -> None:
        """Resume reconnect attempts after night mode ends."""
        self._paused_for_night_mode = False
        self._checking_night_mode = False
        self._heartbeat_failures = 0
        self._unregister_bt_wakeup_listener()
        self.async_update_listeners()
        LOGGER.debug("AC500 resumed after night mode")

    def _register_bt_wakeup_listener(self) -> None:
        """Register an advertisement callback while paused."""
        if self._bt_cancel_callback is not None:
            return
        self._bt_cancel_callback = bt_async_register_callback(
            self.hass,
            self._on_bt_advertisement,
            {ADDRESS: self.client.address},
            BluetoothScanningMode.ACTIVE,
        )

    def _unregister_bt_wakeup_listener(self) -> None:
        """Remove the advertisement callback."""
        if self._bt_cancel_callback is not None:
            self._bt_cancel_callback()
            self._bt_cancel_callback = None

    @callback
    def _on_bt_advertisement(self, _service_info, _change: BluetoothChange) -> None:
        """React to renewed Bluetooth activity while paused."""
        if not self._paused_for_night_mode or self._checking_night_mode:
            return

        now = time.monotonic()
        if now - self._last_night_mode_check_ts < CHECK_NIGHT_MODE_INTERVAL:
            return

        self._checking_night_mode = True
        self.hass.async_create_task(self._check_night_mode_ended())

    async def _check_night_mode_ended(self) -> None:
        """Perform a cautious probe connect to detect the end of night mode."""
        if not self._paused_for_night_mode:
            self._checking_night_mode = False
            return

        self._last_night_mode_check_ts = time.monotonic()
        try:
            if not await self.client.async_connect():
                return

            update_event = asyncio.Event()

            def _on_update() -> None:
                update_event.set()

            self.client.register_callback(_on_update)
            try:
                await asyncio.wait_for(update_event.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                LOGGER.warning("Night-mode probe connected but no state arrived within 3s")
            finally:
                self.client.unregister_callback(_on_update)

            if not self.client.state.night and self.client.state.connected:
                self.resume_from_night_mode()
                self.async_set_updated_data(self.client.state)
            else:
                await self.client.async_disconnect()
        finally:
            self._checking_night_mode = False

    async def _connection_loop(self) -> None:
        """Keep the BLE connection alive unless night mode is active."""
        while self._running:
            if not self.client.is_connected:
                if self._paused_for_night_mode:
                    if not self._checking_night_mode:
                        now = time.monotonic()
                        if now - self._last_night_mode_check_ts >= NIGHT_MODE_FALLBACK_INTERVAL:
                            self._checking_night_mode = True
                            self.hass.async_create_task(self._check_night_mode_ended())
                    await asyncio.sleep(2)
                    continue

                LOGGER.info("AC500 attempting connection...")
                if not await self.client.async_connect():
                    await asyncio.sleep(RECONNECT_INTERVAL)
                    continue
                now = time.monotonic()
                self._last_activity_ts = getattr(self.client, "last_activity_ts", 0.0) or now
                if getattr(self.client, "last_notify_ts", 0.0):
                    self._last_notify_ts = self.client.last_notify_ts
                self._heartbeat_failures = 0

            await asyncio.sleep(2)

            if self._paused_for_night_mode:
                continue

            elapsed = time.monotonic() - self._last_activity_ts
            if elapsed < HEARTBEAT_INTERVAL:
                continue

            if await self.client.async_send_heartbeat():
                self._last_activity_ts = getattr(
                    self.client,
                    "last_activity_ts",
                    time.monotonic(),
                )
                self._heartbeat_failures = 0
                continue

            self._heartbeat_failures += 1
            LOGGER.warning(
                "AC500 heartbeat failed (%s/%s)",
                self._heartbeat_failures,
                HEARTBEAT_FAILURES_BEFORE_RECONNECT,
            )
            if (
                self._heartbeat_failures >= HEARTBEAT_FAILURES_BEFORE_RECONNECT
                or not self.client.is_connected
            ):
                LOGGER.warning("AC500 forcing reconnect after heartbeat failures")
                await self.client.async_disconnect()
                await asyncio.sleep(RECONNECT_INTERVAL)
