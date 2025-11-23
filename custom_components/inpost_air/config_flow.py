"""Config flow for InPost Air integration."""

from __future__ import annotations
from dataclasses import dataclass

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectOptionDict,
)


from .api import InPostAirPoint, InPostApi
from .const import CONF_PARCEL_LOCKER_ID, DOMAIN
from .utils import haversine

_LOGGER = logging.getLogger(__name__)


@dataclass
class SimpleParcelLocker:
    code: str
    description: str
    distance: float


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> InPostAirPoint:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    api_client = InPostApi(hass)
    parcel_locker = await api_client.search_parcel_locker(
        data[CONF_PARCEL_LOCKER_ID].upper()
    )

    if parcel_locker is None:
        raise UnknownParcelLocker

    try:
        parcel_locker_id = await api_client.find_parcel_locker_id(parcel_locker)
        await api_client.get_parcel_locker_air_data(parcel_locker.n, parcel_locker_id)
    except Exception as exc:
        raise ParcelLockerWithoutAirData from exc

    return parcel_locker


class InPostAirConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for InPost Air."""

    VERSION = 2
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                parcel_locker = await validate_input(self.hass, user_input)

                await self.async_set_unique_id(parcel_locker.n)
                self._abort_if_unique_id_configured()
            except UnknownParcelLocker:
                errors["base"] = "unknown_parcel_locker"
            except ParcelLockerWithoutAirData:
                errors["base"] = "parcel_locker_no_data"
            else:
                return self.async_create_entry(
                    title=f"Parcel locker {parcel_locker.n}",
                    data={"parcel_locker": parcel_locker},
                )

        parcel_lockers = [
            SimpleParcelLocker(
                code=locker.n,
                description=locker.d,
                distance=haversine(
                    self.hass.config.longitude,
                    self.hass.config.latitude,
                    locker.l.o,
                    locker.l.a,
                ),
            )
            for locker in await InPostApi(self.hass).get_parcel_lockers_list()
        ]
        options = [
            SelectOptionDict(
                label=f"{locker.code} [{locker.distance:.2f}km] ({locker.description})",
                value=locker.code,
            )
            for locker in sorted(parcel_lockers, key=lambda locker: locker.distance)
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
