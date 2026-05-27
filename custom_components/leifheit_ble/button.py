"""Button platform for Leifheit BLE."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import LeifheitBleConfigEntry
from .const import COMMAND_EXAMPLE
from .entity import LeifheitBleEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LeifheitBleConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    async_add_entities([LeifheitBleButton(entry)])


class LeifheitBleButton(LeifheitBleEntity, ButtonEntity):
    """Send an example write payload to the device."""

    _attr_translation_key = "send_example_command"
    _attr_icon = "mdi:send"

    def __init__(self, entry: LeifheitBleConfigEntry) -> None:
        super().__init__(entry, "send_example_command")

    async def async_press(self) -> None:
        """Send the example payload."""
        await self._entry.runtime_data.client.async_write_command(COMMAND_EXAMPLE)
