"""Shared test fixtures for soehnle_ac500."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from homeassistant.const import CONF_ADDRESS, CONF_NAME

from custom_components.soehnle_ac500.const import DOMAIN
from custom_components.soehnle_ac500.coordinator import SoehnleAc500Coordinator
from custom_components.soehnle_ac500.models import (
    SoehnleAc500RuntimeData,
    SoehnleAc500State,
)
from tests.common import MockConfigEntry

TEST_ADDRESS = "AA:BB:CC:DD:EE:FF"
TEST_NAME = "Soehnle Test Device"


@pytest.fixture
def mock_config_entry(hass) -> MockConfigEntry:
    """Create a config entry with runtime data attached."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=TEST_ADDRESS,
        title=TEST_NAME,
        data={CONF_ADDRESS: TEST_ADDRESS, CONF_NAME: TEST_NAME},
    )
    coordinator = SoehnleAc500Coordinator(hass, TEST_ADDRESS)
    state = SoehnleAc500State(ever_seen=True, connected=True)
    client = Mock(
        is_connected=True,
        address=TEST_ADDRESS,
        state=state,
        async_write_command=AsyncMock(return_value=True),
        async_disconnect=AsyncMock(),
        unregister_callback=Mock(),
    )
    coordinator.attach_client(client)
    coordinator.async_set_updated_data(state)
    entry.runtime_data = SoehnleAc500RuntimeData(
        client=client,
        coordinator=coordinator,
        address=TEST_ADDRESS,
        name=TEST_NAME,
    )
    return entry
