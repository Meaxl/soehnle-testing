"""Config flow for the Soehnle AC500 integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_NAME

from .const import DEFAULT_NAME, DOMAIN, normalize_address


class SoehnleAC500ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Soehnle AC500."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self,
        discovery_info: BluetoothServiceInfoBleak,
    ) -> ConfigFlowResult:
        """Handle a Bluetooth discovery."""
        normalized_address = normalize_address(discovery_info.address)

        await self.async_set_unique_id(normalized_address)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name or DEFAULT_NAME,
        }
        return await self.async_step_user()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle manual or discovery-assisted setup."""
        if user_input is not None:
            return await self._async_create_entry(user_input)

        suggested_values = {
            CONF_ADDRESS: normalize_address(self._discovery_info.address)
            if self._discovery_info is not None
            else "",
            CONF_NAME: self._discovery_info.name
            if self._discovery_info and self._discovery_info.name
            else DEFAULT_NAME,
        }
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_ADDRESS): str,
                        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    }
                ),
                suggested_values,
            ),
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle reconfiguration for an existing entry."""
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            address = normalize_address(user_input[CONF_ADDRESS])
            name = user_input[CONF_NAME].strip() or DEFAULT_NAME

            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured(
                updates={CONF_ADDRESS: address, CONF_NAME: name}
            )
            return self.async_update_reload_and_abort(
                entry,
                unique_id=address,
                data_updates={CONF_ADDRESS: address, CONF_NAME: name},
                reason="reconfigure_successful",
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_ADDRESS): str,
                        vol.Required(CONF_NAME, default=entry.title): str,
                    }
                ),
                {
                    CONF_ADDRESS: entry.data[CONF_ADDRESS],
                    CONF_NAME: entry.data.get(CONF_NAME, entry.title),
                },
            ),
        )

    async def _async_create_entry(self, user_input: dict[str, Any]) -> ConfigFlowResult:
        """Create the config entry after validating the unique ID."""
        address = normalize_address(user_input[CONF_ADDRESS])
        name = user_input[CONF_NAME].strip() or DEFAULT_NAME

        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=name,
            data={CONF_ADDRESS: address, CONF_NAME: name},
        )
