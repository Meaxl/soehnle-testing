"""Entity tests for soehnle_ac500."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.soehnle_ac500.fan import AC500Fan
from custom_components.soehnle_ac500.select import AC500TimerSelect
from custom_components.soehnle_ac500.sensor import AC500AirQualitySensor, AC500PM25Sensor
from custom_components.soehnle_ac500.switch import AC500NightModeSwitch, AC500Switch


@pytest.mark.asyncio
async def test_fan_commands_and_percentage(mock_config_entry) -> None:
    """Fan entity should expose the current speed and send commands."""
    state = mock_config_entry.runtime_data.coordinator.state
    state.ever_seen = True
    state.power = True
    state.speed = 2

    entity = AC500Fan(mock_config_entry)

    assert entity.percentage == 75

    await entity.async_set_preset_mode("auto")

    mock_config_entry.runtime_data.client.async_write_command.assert_awaited_with("auto_on")


@pytest.mark.asyncio
async def test_switch_and_timer_send_expected_commands(mock_config_entry) -> None:
    """Switch and timer entities should delegate writes to the client."""
    switch = AC500Switch(mock_config_entry, "UV-C", "uvc", "uvc_on", "uvc_off")
    timer = AC500TimerSelect(mock_config_entry)

    await switch.async_turn_on()
    await timer.async_select_option("4h")

    mock_config_entry.runtime_data.client.async_write_command.assert_any_await("uvc_on")
    mock_config_entry.runtime_data.client.async_write_command.assert_any_await("timer_4h")


@pytest.mark.asyncio
async def test_night_mode_switch_pauses_after_command(mock_config_entry) -> None:
    """Night mode should disconnect after the command succeeds."""
    entity = AC500NightModeSwitch(mock_config_entry)
    mock_config_entry.runtime_data.coordinator.pause_for_night_mode = AsyncMock()

    with patch("custom_components.soehnle_ac500.switch.asyncio.sleep", new=AsyncMock()):
        await entity.async_turn_on()

    mock_config_entry.runtime_data.client.async_write_command.assert_awaited_with("night_on")
    mock_config_entry.runtime_data.coordinator.pause_for_night_mode.assert_awaited_once()


def test_sensor_entities_expose_derived_values(mock_config_entry) -> None:
    """Sensor entities should project the cached coordinator state."""
    state = mock_config_entry.runtime_data.coordinator.state
    state.ever_seen = True
    state.pm25_raw = 80

    pm25 = AC500PM25Sensor(mock_config_entry)
    air_quality = AC500AirQualitySensor(mock_config_entry)

    assert pm25.native_value == 8.0
    assert air_quality.native_value == "good"
