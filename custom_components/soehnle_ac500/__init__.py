"""The Soehnle AC500 integration."""
from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .ble_client import SoehnleAc500BleClient
from .const import DEFAULT_NAME, DOMAIN, PLATFORMS, normalize_address
from .coordinator import SoehnleAc500Coordinator
from .models import SoehnleAc500RuntimeData

SoehnleAc500ConfigEntry = ConfigEntry[SoehnleAc500RuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: SoehnleAc500ConfigEntry) -> bool:
    """Set up Soehnle AC500 from a config entry."""
    normalized_address = normalize_address(entry.data[CONF_ADDRESS])
    name = entry.data.get(CONF_NAME, entry.title or DEFAULT_NAME)

    if normalized_address != entry.data[CONF_ADDRESS] or entry.unique_id != normalized_address:
        new_data = dict(entry.data)
        new_data[CONF_ADDRESS] = normalized_address
        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            unique_id=normalized_address,
        )

    if bluetooth.async_ble_device_from_address(hass, normalized_address, connectable=True) is None:
        raise ConfigEntryNotReady(f"BLE device {normalized_address} is not reachable")

    coordinator = SoehnleAc500Coordinator(hass, normalized_address)
    client = SoehnleAc500BleClient(hass, normalized_address, name)
    coordinator.attach_client(client)
    client.register_callback(coordinator.async_handle_client_update)

    if not await client.async_connect():
        await client.async_disconnect()
        raise ConfigEntryNotReady(f"Could not connect to BLE device {normalized_address}")

    await coordinator.async_start()
    entry.runtime_data = SoehnleAc500RuntimeData(
        client=client,
        coordinator=coordinator,
        address=normalized_address,
        name=name,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SoehnleAc500ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.coordinator.async_stop()
    return unload_ok
