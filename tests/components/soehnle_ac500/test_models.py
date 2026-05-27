"""Model parser tests for soehnle_ac500."""

from __future__ import annotations

from custom_components.soehnle_ac500.models import SoehnleAc500State


def test_parse_ef02_updates_live_state() -> None:
    """EF02 payloads should populate the control state."""
    state = SoehnleAc500State()

    changed = state.parse_ef02(
        bytes.fromhex("aa0da021010467003200d110e002f625ee")
    )

    assert changed is True
    assert state.power is True
    assert state.uvc is True
    assert state.night is True
    assert state.auto is True
    assert state.timer_on is True
    assert state.speed == 1
    assert state.timer_val == 4
    assert state.pm25 == 5.0
    assert state.filter_total_hours == 4320
    assert state.filter_used_hours == 758
    assert state.ever_seen is True


def test_parse_ef04_updates_temperature_and_diagnostics() -> None:
    """EF04 payloads should update temperature and raw history pairs."""
    state = SoehnleAc500State()

    changed = state.parse_ef04(
        bytes.fromhex("003200c8003c00d7004600dc005000e1")
    )

    assert changed is True
    assert state.temperature == 22.5
    assert state.ef04_pair0 == 50
    assert state.ef04_pair2 == 60
    assert state.ef04_pair3 == 215
    assert state.ef04_pair5 == 220
    assert state.ef04_pair6 == 80
    assert state.ef04_pair7 == 225
    assert state.ef04_raw_hex == "003200c8003c00d7004600dc005000e1"
