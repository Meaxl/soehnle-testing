"""Schalter-Entitäten – UV-C, Nachtmodus."""
from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import SoehnleAc500ConfigEntry
from .entity import SoehnleAc500Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SoehnleAc500ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    async_add_entities([
        AC500Switch(entry, "UV-C", "uvc", "uvc_on", "uvc_off"),
        AC500NightModeSwitch(entry),
    ])


class AC500Switch(SoehnleAc500Entity, SwitchEntity):
    def __init__(
        self,
        entry: SoehnleAc500ConfigEntry,
        feature: str,
        state_attr: str,
        cmd_on: str,
        cmd_off: str,
    ) -> None:
        super().__init__(entry, state_attr)
        self._state_attr = state_attr
        self._cmd_on = cmd_on
        self._cmd_off = cmd_off
        self._attr_name = feature

    @property
    def is_on(self) -> bool:
        return bool(getattr(self.coordinator.state, self._state_attr, False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._entry.runtime_data.client.async_write_command(self._cmd_on)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._entry.runtime_data.client.async_write_command(self._cmd_off)


class AC500NightModeSwitch(SoehnleAc500Entity, SwitchEntity):
    """
    Nachtmodus-Schalter mit BLE-Disconnect-Logik:
    Beim Einschalten wird die BLE-Verbindung nach dem Befehl getrennt,
    damit das Gerät nicht sofort wieder aus dem Nachtmodus geweckt wird.
    Beim Ausschalten wird der Reconnect wieder freigegeben – der Verbindungsaufbau
    selbst weckt das Gerät aus dem Nachtmodus (Geräteverhalten).
    """

    def __init__(self, entry: SoehnleAc500ConfigEntry) -> None:
        super().__init__(entry, "night")
        self._attr_name = "Night Mode"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.state.night)

    async def async_turn_on(self, **kwargs: Any) -> None:
        success = await self._entry.runtime_data.client.async_write_command("night_on")
        if success:
            await asyncio.sleep(1.0)
            await self.coordinator.pause_for_night_mode()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self._entry.runtime_data.client.is_connected:
            await self._entry.runtime_data.client.async_write_command("night_off")

        self.coordinator.resume_from_night_mode()
        self.async_write_ha_state()
