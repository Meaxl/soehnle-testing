"""Binary sensor platform for Leifheit BLE."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LeifheitBleConfigEntry
from .entity import LeifheitBleEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LeifheitBleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    async_add_entities([LeifheitBleBinarySensor(entry)])


class LeifheitBleBinarySensor(LeifheitBleEntity, BinarySensorEntity):
    """Expose an example boolean flag from notify data."""

    _attr_translation_key = "notify_flag"

    def __init__(self, entry: LeifheitBleConfigEntry) -> None:
        super().__init__(entry, "notify_flag")

    @property
    def is_on(self) -> bool | None:
        """Return the latest parsed binary flag."""
        return self.coordinator.data.binary_state
