"""Shared test fixtures for leifheit_ble."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.leifheit_ble.const import CONF_ADDRESS, CONF_NAME, DOMAIN
from custom_components.leifheit_ble.coordinator import LeifheitBleCoordinator
from custom_components.leifheit_ble.models import LeifheitBleRuntimeData
from tests.common import MockConfigEntry

TEST_ADDRESS = "AA:BB:CC:DD:EE:FF"
TEST_NAME = "Leifheit Test Device"


@pytest.fixture
def mock_config_entry(hass) -> MockConfigEntry:
    """Create a config entry with runtime data attached."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_ADDRESS,
        title=TEST_NAME,
        data={CONF_ADDRESS: TEST_ADDRESS, CONF_NAME: TEST_NAME},
    )
    entry.runtime_data = LeifheitBleRuntimeData(
        client=Mock(
            is_connected=True,
            async_write_command=AsyncMock(),
            async_disconnect=AsyncMock(),
        ),
        coordinator=LeifheitBleCoordinator(hass, TEST_ADDRESS),
        address=TEST_ADDRESS,
        name=TEST_NAME,
    )
    return entry
