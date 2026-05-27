"""Typed runtime models for the Leifheit BLE integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ble_client import LeifheitBleClient
    from .coordinator import LeifheitBleCoordinator


@dataclass(slots=True)
class LeifheitBleState:
    """Parsed device state from the latest BLE notification."""

    sensor_value: int | None = None
    binary_state: bool | None = None
    switch_state: bool | None = None
    last_payload: str | None = None


@dataclass(slots=True)
class LeifheitBleRuntimeData:
    """Objects attached to a config entry at runtime."""

    client: LeifheitBleClient
    coordinator: LeifheitBleCoordinator
    address: str
    name: str
