"""Config flow for InPost Air integration."""

from __future__ import annotations
from dataclasses import asdict

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectOptionDict,
)


from .api import InPostApi
from .const import CONF_PARCEL_LOCKER_ID, DOMAIN
from .models import StoredLockerPoint

_LOGGER = logging.getLogger(__name__)


async def validate_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> StoredLockerPoint:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    api_client = InPostApi(hass)
    parcel_locker = await api_client.search_parcel_locker(
        data[CONF_PARCEL_LOCKER_ID].strip().upper()
    )

    if parcel_locker is None:
        raise UnknownParcelLocker

    try:
        await api_client.get_parcel_locker_air_data(parcel_locker.code)
    except Exception as exc:
        raise ParcelLockerWithoutAirData from exc

    return parcel_locker


class InPostAirConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create the single InPost Air entry."""

    VERSION = 3
    MINOR_VERSION = 3

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry):
        """Allow adding parcel lockers to the integration."""
        return {"parcel_locker": ParcelLockerSubentryFlow}

    async def async_step_user(self, user_input=None):
        """Create the integration; parcel lockers are added as subentries."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title="InPost Air", data={})


class ParcelLockerSubentryFlow(config_entries.ConfigSubentryFlow):
    """Add a parcel locker to the integration."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                parcel_locker = await validate_input(self.hass, user_input)

                if any(
                    subentry.unique_id == parcel_locker.code
                    for subentry in self._get_entry().subentries.values()
                ):
                    return self.async_abort(reason="already_configured")
            except UnknownParcelLocker:
                errors["base"] = "unknown_parcel_locker"
            except ParcelLockerWithoutAirData:
                errors["base"] = "parcel_locker_no_data"
            else:
                return self.async_create_entry(
                    title=f"Parcel locker {parcel_locker.code}",
                    data={"parcel_locker": asdict(parcel_locker)},
                    unique_id=parcel_locker.code,
                )

        parcel_lockers = await InPostApi(self.hass).get_parcel_lockers_list(
            self.hass.config.latitude, self.hass.config.longitude
        )
        options = [
            SelectOptionDict(
                label=f"{locker.name} [{locker.distance / 1000:.2f}km] ({locker.location_description or ''})",
                value=locker.name,
            )
            for locker in parcel_lockers
        ]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PARCEL_LOCKER_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            custom_value=True,
                        )
                    ),
                }
            ),
            errors=errors,
        )


class UnknownParcelLocker(HomeAssistantError):
    """Parcel locker with that ID doesn't exist."""


class ParcelLockerWithoutAirData(HomeAssistantError):
    """Parcel locker with that ID doesn't have air data."""
