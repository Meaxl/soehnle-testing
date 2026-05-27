"""Switch platform for Leifheit BLE."""

from __future__ import annotations

from dataclasses import replace

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LeifheitBleConfigEntry
from .const import COMMAND_SWITCH_OFF, COMMAND_SWITCH_ON
from .entity import LeifheitBleEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LeifheitBleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    async_add_entities([LeifheitBleSwitch(entry)])


class LeifheitBleSwitch(LeifheitBleEntity, SwitchEntity):
    """Mirror a demo on/off state through BLE writes and notify updates."""

    _attr_translation_key = "example_output"

    def __init__(self, entry: LeifheitBleConfigEntry) -> None:
        super().__init__(entry, "example_output")

    @property
    def is_on(self) -> bool:
        """Return the last known switch state."""
        return bool(self.coordinator.data.switch_state)

    async def async_turn_on(self, **kwargs: object) -> None:
        """Send the demo on command."""
        await self._entry.runtime_data.client.async_write_command(COMMAND_SWITCH_ON)
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, switch_state=True)
        )

    async def async_turn_off(self, **kwargs: object) -> None:
        """Send the demo off command."""
        await self._entry.runtime_data.client.async_write_command(COMMAND_SWITCH_OFF)
        self.coordinator.async_set_updated_data(
            replace(self.coordinator.data, switch_state=False)
        )
