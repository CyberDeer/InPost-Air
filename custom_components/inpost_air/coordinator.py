"""DataUpdateCoordinator for integration_blueprint."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import (
    InPostAirApiClient,
    InPostAirApiClientAuthenticationError,
    InPostAirApiClientError,
)
from .const import DOMAIN, LOGGER


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class InPostAirDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: InPostAirApiClient,
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.client.async_get_data()
        except InPostAirApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except InPostAirApiClientError as exception:
            raise UpdateFailed(exception) from exception

    async def get_sensors(self):
        results = []
        results.append("air_index_level")
        for sensor in self.data.get("air_sensors"):
            [name, value, norm] = sensor.split(":")
            results.append(name)
            if norm:
                results.append(name + "_norm")
        return results;