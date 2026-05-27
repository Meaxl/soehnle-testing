"""Typed runtime models for the Soehnle AC500 integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .const import FLAG_AUTO, FLAG_NIGHT, FLAG_POWER, FLAG_TIMER, FLAG_UVC

if TYPE_CHECKING:
    from .ble_client import SoehnleAc500BleClient
    from .coordinator import SoehnleAc500Coordinator

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SoehnleAc500State:
    """Latest parsed device state."""

    power: bool = False
    uvc: bool = False
    night: bool = False
    auto: bool = False
    timer_on: bool = False
    speed: int = 0
    timer_val: int = 0
    pm25_raw: int = 0
    temperature: float | None = None
    ef04_pair0: int | None = None
    ef04_pair2: int | None = None
    ef04_pair3: int | None = None
    ef04_pair5: int | None = None
    ef04_pair6: int | None = None
    ef04_pair7: int | None = None
    ef04_raw_hex: str | None = None
    ef03_raw_hex: str | None = None
    ffd2_raw_hex: str | None = None
    ffd3_raw_hex: str | None = None
    ffd4_raw_hex: str | None = None
    ffd5_raw_hex: str | None = None
    fff1_raw_hex: str | None = None
    filter_total_hours: int = 0
    filter_used_hours: int = 0
    connected: bool = False
    ever_seen: bool = False

    @property
    def pm25(self) -> float:
        """Return PM2.5 in ug/m3."""
        return round(self.pm25_raw / 10, 1)

    @property
    def filter_pct_used(self) -> float | None:
        """Return filter usage percentage."""
        if self.filter_total_hours == 0:
            return None
        return round(self.filter_used_hours / self.filter_total_hours * 100, 1)

    @property
    def filter_remaining_hours(self) -> int | None:
        """Return remaining filter lifetime in hours."""
        if self.filter_total_hours == 0:
            return None
        return max(0, self.filter_total_hours - self.filter_used_hours)

    @property
    def timer_hours(self) -> int:
        """Return the active timer setting."""
        return self.timer_val if self.timer_on else 0

    def parse_ef02(self, data: bytes) -> bool:
        """Parse a live status frame."""
        if len(data) != 17 or data[0] != 0xAA or data[-1] != 0xEE:
            return False

        payload = data[4:-1]
        expected = (
            payload[0]
            + payload[1]
            + payload[2]
            + payload[4]
            + payload[6]
            + payload[9]
            + payload[10]
            + 0xBE
        ) & 0xFF
        if expected != payload[11]:
            LOGGER.warning(
                "EF02 checksum mismatch: expected 0x%02x got 0x%02x - raw: %s",
                expected,
                payload[11],
                data.hex(),
            )

        previous = (
            self.power,
            self.uvc,
            self.night,
            self.auto,
            self.timer_on,
            self.timer_val,
            self.speed,
            self.pm25_raw,
            self.filter_total_hours,
            self.filter_used_hours,
        )

        flags = payload[2]
        self.power = bool(flags & FLAG_POWER)
        self.uvc = bool(flags & FLAG_UVC)
        self.night = bool(flags & FLAG_NIGHT)
        self.auto = bool(flags & FLAG_AUTO)
        self.timer_on = bool(flags & FLAG_TIMER)
        self.speed = payload[0]
        self.timer_val = payload[1]
        self.pm25_raw = payload[4]
        self.filter_total_hours = int.from_bytes(payload[7:9], "big")
        self.filter_used_hours = int.from_bytes(payload[9:11], "big")
        self.ever_seen = True

        current = (
            self.power,
            self.uvc,
            self.night,
            self.auto,
            self.timer_on,
            self.timer_val,
            self.speed,
            self.pm25_raw,
            self.filter_total_hours,
            self.filter_used_hours,
        )
        return previous != current

    def parse_ef04(self, data: bytes) -> bool:
        """Parse the EF04 history buffer."""
        if len(data) < 4 or len(data) % 2 != 0:
            return False

        pairs = [int.from_bytes(data[i : i + 2], "big") for i in range(0, len(data), 2)]
        previous = (
            self.temperature,
            self.ef04_pair0,
            self.ef04_pair2,
            self.ef04_pair3,
            self.ef04_pair5,
            self.ef04_pair6,
            self.ef04_pair7,
            self.ef04_raw_hex,
        )

        for index in range(1, len(pairs), 2):
            if pairs[index] != 0xFFFF:
                self.temperature = round(pairs[index] / 10, 1)

        diagnostics = {
            0: "ef04_pair0",
            2: "ef04_pair2",
            3: "ef04_pair3",
            5: "ef04_pair5",
            6: "ef04_pair6",
            7: "ef04_pair7",
        }
        for index, attribute in diagnostics.items():
            if len(pairs) > index and pairs[index] != 0xFFFF:
                setattr(self, attribute, pairs[index])

        self.ef04_raw_hex = data.hex()

        current = (
            self.temperature,
            self.ef04_pair0,
            self.ef04_pair2,
            self.ef04_pair3,
            self.ef04_pair5,
            self.ef04_pair6,
            self.ef04_pair7,
            self.ef04_raw_hex,
        )
        return previous != current


@dataclass(slots=True)
class SoehnleAc500RuntimeData:
    """Objects attached to a config entry at runtime."""

    client: SoehnleAc500BleClient
    coordinator: SoehnleAc500Coordinator
    address: str
    name: str
