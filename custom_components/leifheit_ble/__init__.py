"""The Leifheit BLE integration."""

from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .ble_client import LeifheitBleClient
from .const import CONF_ADDRESS, CONF_NAME, DOMAIN, PLATFORMS
from .coordinator import LeifheitBleCoordinator
from .models import LeifheitBleRuntimeData

LeifheitBleConfigEntry = ConfigEntry[LeifheitBleRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: LeifheitBleConfigEntry) -> bool:
    """Set up Leifheit BLE from a config entry."""
    address = entry.data[CONF_ADDRESS]
    name = entry.data.get(CONF_NAME, entry.title)

    if bluetooth.async_ble_device_from_address(hass, address, connectable=True) is None:
        raise ConfigEntryNotReady(f"BLE device {address} is not reachable")

    coordinator = LeifheitBleCoordinator(hass, address)
    client = LeifheitBleClient(
        hass,
        address,
        name,
        on_notification=coordinator.async_handle_notification,
        on_disconnect=coordinator.async_mark_unavailable,
    )

    try:
        await client.async_connect()
    except Exception as err:
        await client.async_disconnect()
        raise ConfigEntryNotReady(f"Could not connect to BLE device {address}") from err

    entry.runtime_data = LeifheitBleRuntimeData(
        client=client,
        coordinator=coordinator,
        address=address,
        name=name,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LeifheitBleConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.client.async_disconnect()
    return unload_ok
