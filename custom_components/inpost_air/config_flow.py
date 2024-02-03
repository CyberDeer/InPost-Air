"""Config flow for InPost Air integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import InPostApi
from .const import CONF_PARCEL_LOCKER_ID, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PARCEL_LOCKER_ID): str,
    }
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    api_client = InPostApi(hass)
    parcel_locker = await api_client.search_parcel_locker(data[CONF_PARCEL_LOCKER_ID])

    if parcel_locker is None:
        raise UnknownParcelLocker

    try:
        await api_client.find_parcel_locker_id(parcel_locker)
    except Exception:
        raise ParcelLockerWithoutAirData

    return parcel_locker


class InPostAirConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for InPost Air."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                parcel_locker = await validate_input(self.hass, user_input)

                await self.async_set_unique_id(parcel_locker["n"])
                self._abort_if_unique_id_configured()
            except UnknownParcelLocker:
                errors["base"] = "unknown_parcel_locker"
            except ParcelLockerWithoutAirData:
                errors["base"] = "parcel_locker_no_data"
            else:
                return self.async_create_entry(
                    title=f"Parcel locker {parcel_locker['n']}", data=parcel_locker
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class UnknownParcelLocker(HomeAssistantError):
    """Parcel locker with that ID doesn't exist."""


class ParcelLockerWithoutAirData(HomeAssistantError):
    """Parcel locker with that ID doesn't have air data."""
