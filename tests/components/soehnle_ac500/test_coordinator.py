"""Coordinator tests for soehnle_ac500."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from homeassistant.components.bluetooth import BluetoothChange

from custom_components.soehnle_ac500.coordinator import (
    CHECK_NIGHT_MODE_INTERVAL,
    HEARTBEAT_FAILURES_BEFORE_RECONNECT,
    HEARTBEAT_INTERVAL,
    SoehnleAc500Coordinator,
)
from custom_components.soehnle_ac500.models import SoehnleAc500State


@pytest.mark.asyncio
async def test_pause_for_night_mode_disconnects_and_suppresses_stale(hass) -> None:
    """Night mode pause should disconnect the client and keep the last state valid."""
    coordinator = SoehnleAc500Coordinator(hass, "AA:BB:CC:DD:EE:FF")
    state = SoehnleAc500State(ever_seen=True, connected=True, night=True)
    client = Mock(
        address="AA:BB:CC:DD:EE:FF",
        state=state,
        async_disconnect=AsyncMock(),
        unregister_callback=Mock(),
        is_connected=False,
        last_notify_ts=0.0,
        last_activity_ts=0.0,
    )
    coordinator.attach_client(client)

    await coordinator.pause_for_night_mode()

    client.async_disconnect.assert_awaited_once()
    assert coordinator.is_stale is False


@pytest.mark.asyncio
async def test_probe_resumes_when_state_returns_from_night_mode(hass) -> None:
    """A successful probe with live state should resume reconnects."""
    coordinator = SoehnleAc500Coordinator(hass, "AA:BB:CC:DD:EE:FF")
    state = SoehnleAc500State(ever_seen=True, connected=True, night=False)

    def register_callback(callback):
        callback()

    client = Mock(
        address="AA:BB:CC:DD:EE:FF",
        state=state,
        async_connect=AsyncMock(return_value=True),
        async_disconnect=AsyncMock(),
        register_callback=Mock(side_effect=register_callback),
        unregister_callback=Mock(),
        is_connected=False,
        last_notify_ts=0.0,
        last_activity_ts=0.0,
    )
    coordinator.attach_client(client)
    coordinator._paused_for_night_mode = True

    await coordinator._check_night_mode_ended()

    assert coordinator._paused_for_night_mode is False
    client.async_disconnect.assert_not_awaited()


def test_advertisement_schedules_probe_when_paused(hass) -> None:
    """Renewed Bluetooth activity should schedule a probe while paused."""
    coordinator = SoehnleAc500Coordinator(hass, "AA:BB:CC:DD:EE:FF")
    client = Mock(
        address="AA:BB:CC:DD:EE:FF",
        state=SoehnleAc500State(ever_seen=True, night=True),
        is_connected=False,
        last_notify_ts=0.0,
        last_activity_ts=0.0,
    )
    coordinator.attach_client(client)
    coordinator._paused_for_night_mode = True
    coordinator._last_night_mode_check_ts = 0.0

    def _capture_task(coro):
        coro.close()

    with patch.object(hass, "async_create_task", side_effect=_capture_task) as create_task, patch(
        "custom_components.soehnle_ac500.coordinator.time.monotonic",
        return_value=CHECK_NIGHT_MODE_INTERVAL + 1,
    ):
        coordinator._on_bt_advertisement(None, BluetoothChange.ADVERTISEMENT)

    create_task.assert_called_once()


@pytest.mark.asyncio
async def test_connection_loop_uses_heartbeat_before_reconnect(hass) -> None:
    """Successful heartbeats should keep a silent connection open."""
    coordinator = SoehnleAc500Coordinator(hass, "AA:BB:CC:DD:EE:FF")
    state = SoehnleAc500State(ever_seen=True, connected=True)
    client = Mock(
        address="AA:BB:CC:DD:EE:FF",
        state=state,
        is_connected=True,
        async_send_heartbeat=AsyncMock(return_value=True),
        async_disconnect=AsyncMock(),
        last_notify_ts=0.0,
        last_activity_ts=0.0,
    )
    coordinator.attach_client(client)
    coordinator._running = True
    coordinator._last_activity_ts = 0.0

    sleep_calls = 0

    async def _sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 1:
            coordinator._running = False

    with (
        patch("custom_components.soehnle_ac500.coordinator.asyncio.sleep", side_effect=_sleep),
        patch(
            "custom_components.soehnle_ac500.coordinator.time.monotonic",
            side_effect=[HEARTBEAT_INTERVAL + 1, HEARTBEAT_INTERVAL + 2],
        ),
    ):
        await coordinator._connection_loop()

    client.async_send_heartbeat.assert_awaited_once()
    client.async_disconnect.assert_not_awaited()


@pytest.mark.asyncio
async def test_connection_loop_reconnects_after_repeated_heartbeat_failures(hass) -> None:
    """Repeated heartbeat failures should force a reconnect."""
    coordinator = SoehnleAc500Coordinator(hass, "AA:BB:CC:DD:EE:FF")
    state = SoehnleAc500State(ever_seen=True, connected=True)
    client = Mock(
        address="AA:BB:CC:DD:EE:FF",
        state=state,
        is_connected=True,
        async_send_heartbeat=AsyncMock(return_value=False),
        async_disconnect=AsyncMock(),
        last_notify_ts=0.0,
        last_activity_ts=0.0,
    )
    coordinator.attach_client(client)
    coordinator._running = True
    coordinator._last_activity_ts = 0.0

    sleep_calls = 0

    async def _sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= HEARTBEAT_FAILURES_BEFORE_RECONNECT + 1:
            coordinator._running = False

    monotonic_values = []
    for idx in range(HEARTBEAT_FAILURES_BEFORE_RECONNECT):
        monotonic_values.extend(
            [
                HEARTBEAT_INTERVAL + 1 + idx,
                HEARTBEAT_INTERVAL + 2 + idx,
            ]
        )

    with (
        patch("custom_components.soehnle_ac500.coordinator.asyncio.sleep", side_effect=_sleep),
        patch(
            "custom_components.soehnle_ac500.coordinator.time.monotonic",
            side_effect=monotonic_values,
        ),
    ):
        await coordinator._connection_loop()

    assert client.async_send_heartbeat.await_count == HEARTBEAT_FAILURES_BEFORE_RECONNECT
    client.async_disconnect.assert_awaited_once()
