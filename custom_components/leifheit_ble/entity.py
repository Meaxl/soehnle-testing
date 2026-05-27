"""Shared entity helpers for Leifheit BLE."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LeifheitBleConfigEntry
from .const import DOMAIN
from .coordinator import LeifheitBleCoordinator


class LeifheitBleEntity(CoordinatorEntity[LeifheitBleCoordinator]):
    """Common entity behavior for Leifheit BLE platforms."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: LeifheitBleConfigEntry, entity_key: str) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id or entry.runtime_data.address}_{entity_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.runtime_data.address)},
            connections={(CONNECTION_BLUETOOTH, entry.runtime_data.address)},
            name=entry.runtime_data.name,
            manufacturer="Leifheit",
        )

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return self._entry.runtime_data.client.is_connected
