"""Auswahl-Entität – Timer (aus / 2h / 4h / 8h)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SoehnleAc500ConfigEntry
from .entity import SoehnleAc500Entity

TIMER_OPTIONS  = ["off", "2h", "4h", "8h"]
TIMER_TO_CMD   = {"off": "timer_off", "2h": "timer_2h", "4h": "timer_4h", "8h": "timer_8h"}
VAL_TO_OPTION  = {0: "off", 2: "2h", 4: "4h", 8: "8h"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SoehnleAc500ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    async_add_entities([AC500TimerSelect(entry)])


class AC500TimerSelect(SoehnleAc500Entity, SelectEntity):
    _attr_options = TIMER_OPTIONS
    _attr_icon    = "mdi:timer-outline"

    def __init__(self, entry: SoehnleAc500ConfigEntry) -> None:
        super().__init__(entry, "timer")
        self._attr_name  = "Timer"

    @property
    def current_option(self) -> str:
        return VAL_TO_OPTION.get(self.coordinator.state.timer_hours, "off")

    async def async_select_option(self, option: str) -> None:
        cmd = TIMER_TO_CMD.get(option)
        if cmd:
            await self._entry.runtime_data.client.async_write_command(cmd)
