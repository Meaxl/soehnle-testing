"""Push coordinator for Leifheit BLE notifications."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .models import LeifheitBleState

LOGGER = logging.getLogger(__name__)


class LeifheitBleCoordinator(DataUpdateCoordinator[LeifheitBleState]):
    """Stores the latest parsed BLE state and pushes updates to entities."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        super().__init__(hass, logger=LOGGER, name=f"{DOMAIN}_{address}")
        self.async_set_updated_data(LeifheitBleState())

    async def _async_update_data(self) -> LeifheitBleState:
        """Return the current cached state for explicit refresh requests."""
        return self.data

    @callback
    def async_handle_notification(self, payload: bytes) -> None:
        """Parse a notification payload into a simple demo device state."""
        previous = self.data
        if not payload:
            self.async_set_updated_data(previous)
            return

        first_byte = payload[0]
        sensor_value = int.from_bytes(payload[:2], byteorder="little", signed=False)
        parsed = LeifheitBleState(
            sensor_value=sensor_value,
            binary_state=bool(first_byte & 0x01),
            switch_state=bool(first_byte & 0x02),
            last_payload=payload.hex(" "),
        )
        self.async_set_updated_data(parsed)

    @callback
    def async_mark_unavailable(self) -> None:
        """Mark the cached state as stale after a disconnect."""
        self.last_update_success = False
        self.async_update_listeners()
