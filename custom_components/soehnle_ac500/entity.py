"""Shared entity helpers for the Soehnle AC500 integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SoehnleAc500ConfigEntry
from .const import DOMAIN
from .coordinator import SoehnleAc500Coordinator


class SoehnleAc500Entity(CoordinatorEntity[SoehnleAc500Coordinator]):
    """Common entity behavior for Soehnle AC500 platforms."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: SoehnleAc500ConfigEntry, entity_key: str) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._entry = entry
        identifier = entry.unique_id or entry.runtime_data.address
        self._attr_unique_id = f"{identifier}_{entity_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            connections={(CONNECTION_BLUETOOTH, entry.runtime_data.address)},
            name=entry.runtime_data.name,
            manufacturer="Soehnle",
            model="Airfresh Clean Connect 500",
            sw_version="Jan 25 2018",
        )

    @property
    def available(self) -> bool:
        """Return whether the entity should be available."""
        return self.coordinator.state.ever_seen and not self.coordinator.is_stale
