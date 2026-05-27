"""Sensor platform for Leifheit BLE."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LeifheitBleConfigEntry
from .entity import LeifheitBleEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LeifheitBleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities([LeifheitBleSensor(entry)])


class LeifheitBleSensor(LeifheitBleEntity, SensorEntity):
    """Expose an example numeric value from notify data."""

    _attr_translation_key = "notify_value"
    _attr_icon = "mdi:counter"
    _attr_suggested_display_precision = 0

    def __init__(self, entry: LeifheitBleConfigEntry) -> None:
        super().__init__(entry, "notify_value")

    @property
    def native_value(self) -> int | None:
        """Return the latest parsed sensor value."""
        return self.coordinator.data.sensor_value
