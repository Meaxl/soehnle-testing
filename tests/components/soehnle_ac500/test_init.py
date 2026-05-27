"""Tests for soehnle_ac500 setup and unload."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.soehnle_ac500 import async_setup_entry, async_unload_entry
from custom_components.soehnle_ac500.const import DOMAIN
from tests.common import MockConfigEntry


@pytest.mark.asyncio
async def test_setup_entry_creates_runtime_data(hass) -> None:
    """Setting up the entry should create runtime data and forward platforms."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="aa:bb:cc:dd:ee:ff",
        title="Soehnle Test Device",
        data={CONF_ADDRESS: "aa:bb:cc:dd:ee:ff", CONF_NAME: "Soehnle Test Device"},
    )

    with (
        patch(
            "custom_components.soehnle_ac500.bluetooth.async_ble_device_from_address",
            return_value=object(),
        ),
        patch(
            "custom_components.soehnle_ac500.SoehnleAc500BleClient.async_connect",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "custom_components.soehnle_ac500.SoehnleAc500Coordinator.async_start",
            new=AsyncMock(),
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new=AsyncMock(),
        ),
    ):
        assert await async_setup_entry(hass, entry) is True

    assert entry.runtime_data.address == "AA:BB:CC:DD:EE:FF"
    assert entry.runtime_data.name == "Soehnle Test Device"


@pytest.mark.asyncio
async def test_setup_entry_raises_not_ready_when_device_missing(hass) -> None:
    """Setup should retry later if the BLE device is not connectable."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="AA:BB:CC:DD:EE:FF",
        title="Soehnle Test Device",
        data={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF", CONF_NAME: "Soehnle Test Device"},
    )

    with patch(
        "custom_components.soehnle_ac500.bluetooth.async_ble_device_from_address",
        return_value=None,
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_unload_entry_stops_coordinator(hass, mock_config_entry) -> None:
    """Unload should unload platforms and stop the coordinator."""
    mock_config_entry.add_to_hass(hass)
    mock_config_entry.runtime_data.coordinator.async_stop = AsyncMock()

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new=AsyncMock(return_value=True),
    ):
        assert await async_unload_entry(hass, mock_config_entry) is True

    mock_config_entry.runtime_data.coordinator.async_stop.assert_awaited_once()
