"""Entity tests for Leifheit BLE."""

from __future__ import annotations

import pytest

from custom_components.leifheit_ble.button import LeifheitBleButton
from custom_components.leifheit_ble.const import (
    COMMAND_EXAMPLE,
    COMMAND_SWITCH_OFF,
    COMMAND_SWITCH_ON,
)
from custom_components.leifheit_ble.coordinator import LeifheitBleCoordinator
from custom_components.leifheit_ble.switch import LeifheitBleSwitch


@pytest.mark.asyncio
async def test_notify_updates_parsed_state(hass) -> None:
    """Notify data should be parsed into the coordinator state."""
    coordinator = LeifheitBleCoordinator(hass, "AA:BB:CC:DD:EE:FF")

    coordinator.async_handle_notification(b"\x03\x10")

    assert coordinator.data.sensor_value == 4099
    assert coordinator.data.binary_state is True
    assert coordinator.data.switch_state is True
    assert coordinator.data.last_payload == "03 10"


@pytest.mark.asyncio
async def test_button_sends_example_payload(mock_config_entry) -> None:
    """Pressing the button should write the demo payload."""
    entity = LeifheitBleButton(mock_config_entry)

    await entity.async_press()

    mock_config_entry.runtime_data.client.async_write_command.assert_awaited_once_with(
        COMMAND_EXAMPLE
    )


@pytest.mark.asyncio
async def test_switch_writes_on_and_off_payloads(hass, mock_config_entry) -> None:
    """Turning the switch on and off should write the correct payloads."""
    coordinator = LeifheitBleCoordinator(hass, "AA:BB:CC:DD:EE:FF")
    mock_config_entry.runtime_data.coordinator = coordinator

    entity = LeifheitBleSwitch(mock_config_entry)

    await entity.async_turn_on()
    await entity.async_turn_off()

    mock_config_entry.runtime_data.client.async_write_command.assert_any_await(
        COMMAND_SWITCH_ON
    )
    mock_config_entry.runtime_data.client.async_write_command.assert_any_await(
        COMMAND_SWITCH_OFF
    )
    assert coordinator.data.switch_state is False
