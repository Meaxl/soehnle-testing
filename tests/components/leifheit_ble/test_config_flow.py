"""Tests for the Leifheit BLE config flow."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.leifheit_ble.const import CONF_ADDRESS, CONF_NAME, DOMAIN
from tests.common import MockConfigEntry

TEST_ADDRESS = "AA:BB:CC:DD:EE:FF"
TEST_NAME = "Leifheit Test Device"


@pytest.mark.asyncio
async def test_user_flow_creates_entry(hass) -> None:
    """Manual setup should create a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_ADDRESS: TEST_ADDRESS, CONF_NAME: TEST_NAME},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_NAME
    assert result["data"] == {CONF_ADDRESS: TEST_ADDRESS, CONF_NAME: TEST_NAME}


@pytest.mark.asyncio
async def test_bluetooth_flow_prefills_discovered_device(hass) -> None:
    """Bluetooth discovery should show a prefilled form first."""
    discovery_info = SimpleNamespace(name=TEST_NAME, address=TEST_ADDRESS)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=discovery_info,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_duplicate_device_aborts(hass) -> None:
    """A duplicate BLE address should abort the flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_ADDRESS,
        title=TEST_NAME,
        data={CONF_ADDRESS: TEST_ADDRESS, CONF_NAME: TEST_NAME},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={CONF_ADDRESS: TEST_ADDRESS, CONF_NAME: TEST_NAME},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_reconfigure_updates_existing_entry(hass) -> None:
    """Reconfigure should update and reload the existing entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_ADDRESS,
        title=TEST_NAME,
        data={CONF_ADDRESS: TEST_ADDRESS, CONF_NAME: TEST_NAME},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        data={CONF_ADDRESS: TEST_ADDRESS, CONF_NAME: "Updated Name"},
    )

    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_NAME] == "Updated Name"
