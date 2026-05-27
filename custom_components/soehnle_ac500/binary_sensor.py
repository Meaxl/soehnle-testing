"""Binärsensor – BLE-Verbindungsstatus."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SoehnleAc500ConfigEntry
from .entity import SoehnleAc500Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SoehnleAc500ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    async_add_entities([AC500ConnectivitySensor(entry)])


class AC500ConnectivitySensor(SoehnleAc500Entity, BinarySensorEntity):
    """Zeigt den aktuellen BLE-Verbindungsstatus. Immer verfügbar (zeigt 'off' bei Trennung)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_registry_enabled_default = False

    def __init__(self, entry: SoehnleAc500ConfigEntry) -> None:
        super().__init__(entry, "connectivity")
        self._attr_name = "Connection"

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.state.connected
