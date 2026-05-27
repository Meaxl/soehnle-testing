"""Tests for Leifheit BLE setup and unload."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.leifheit_ble import async_setup_entry, async_unload_entry
from custom_components.leifheit_ble.const import DOMAIN
from tests.common import MockConfigEntry


@pytest.mark.asyncio
async def test_setup_entry_creates_runtime_data(hass) -> None:
    """Setting up the entry should create runtime data and forward platforms."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="AA:BB:CC:DD:EE:FF",
        title="Leifheit Test Device",
        data={"address": "AA:BB:CC:DD:EE:FF", "name": "Leifheit Test Device"},
    )

    with (
        patch(
            "custom_components.leifheit_ble.bluetooth.async_ble_device_from_address",
            return_value=object(),
        ),
        patch(
            "custom_components.leifheit_ble.LeifheitBleClient.async_connect",
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
    assert entry.runtime_data.name == "Leifheit Test Device"


@pytest.mark.asyncio
async def test_setup_entry_raises_not_ready_when_device_missing(hass) -> None:
    """Setup should retry later if the BLE device is not connectable."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="AA:BB:CC:DD:EE:FF",
        title="Leifheit Test Device",
        data={"address": "AA:BB:CC:DD:EE:FF", "name": "Leifheit Test Device"},
    )

    with patch(
        "custom_components.leifheit_ble.bluetooth.async_ble_device_from_address",
        return_value=None,
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_unload_entry_disconnects_client(hass, mock_config_entry) -> None:
    """Unload should unload platforms and disconnect the BLE client."""
    mock_config_entry.add_to_hass(hass)

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new=AsyncMock(return_value=True),
    ):
        assert await async_unload_entry(hass, mock_config_entry) is True

    mock_config_entry.runtime_data.client.async_disconnect.assert_awaited_once()
