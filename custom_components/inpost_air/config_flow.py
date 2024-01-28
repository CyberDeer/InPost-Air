"""Adds config flow for Blueprint."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_ID
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectOptionDict,
    SelectSelectorMode
)

from .api import (
    InPostAirApiClient,
    InPostAirApiClientAuthenticationError,
    InPostAirApiClientCommunicationError,
    InPostAirApiClientError,
)
from .const import DOMAIN, LOGGER


class BlueprintFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                await self._test_credentials(
                    id=user_input[CONF_ID],
                )
            except InPostAirApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except InPostAirApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except InPostAirApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_ID],
                    data=user_input,
                )
            
        client = InPostAirApiClient(
            machine_id=id,
            session=async_create_clientsession(self.hass),
        )

        points = await client.async_get_points()
        options = [SelectOptionDict(value=x['n'], label=f"{x['n']} ({x['d']})") for x in points['items']]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ID): SelectSelector(
                        SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                    ),
                }
            ),
            errors=_errors,
        )

    async def _test_credentials(self, parcel_locker_id: str) -> None:
        """Validate credentials."""
        # dostanie machine_id
        await client.async_get_data(machine_id, parcel_locker_id)
