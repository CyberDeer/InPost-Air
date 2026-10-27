"""InPost API data coordinator."""

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import InPostAirApiClientError, InPostApi, ParcelLockerAirDataResponse
from .const import Entities
from .models import ParcelLocker

_LOGGER = logging.getLogger(__name__)


@dataclass
class ValueWithNorm:
    """Value with norm."""

    name: str
    value: float
    norm: float


@dataclass
class ValueWithoutNorm:
    """Value without norm."""

    name: str
    value: float


_SENSOR_BY_NAME = {
    "PM25": Entities.PM2_5,
    "PM10": Entities.PM10,
    "PM1": Entities.PM1,
    "PM4": Entities.PM4,
    "TEMPERATURE": Entities.Temperature,
    "PRESSURE": Entities.Pressure,
    "HUMIDITY": Entities.Humidity,
    "NO2": Entities.NO2,
    "O3": Entities.O3,
}


def readings_from_air_data(
    data: ParcelLockerAirDataResponse,
) -> dict[str, ValueWithNorm | ValueWithoutNorm]:
    """Map the points API payload onto sensor entities."""
    norms = {
        standard.pollutant: standard.percent
        for standard in data.current.standards or []
        if standard.name == "WHO" and standard.pollutant in {"PM25", "PM10"}
    }
    readings: dict[str, ValueWithNorm | ValueWithoutNorm] = {}

    for item in data.current.values:
        entity = _SENSOR_BY_NAME.get(item.name)
        if entity is None:
            continue

        if item.name in norms:
            readings[entity] = ValueWithNorm(entity, item.value, norms[item.name])
        else:
            readings[entity] = ValueWithoutNorm(entity, item.value)

    return readings


class InPostAirDataCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(
        self, hass: HomeAssistant, api_client: InPostApi, parcel_locker: ParcelLocker
    ) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"Parcel Locker {parcel_locker.locker_code} data coordinator",
            update_interval=timedelta(minutes=5),
        )
        self.api_client = api_client
        self.parcel_locker = parcel_locker

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            async with asyncio.timeout(10):
                data = await self.api_client.get_parcel_locker_air_data(
                    self.parcel_locker.locker_code
                )

                return readings_from_air_data(data)
        except InPostAirApiClientError as err:
            raise UpdateFailed(err) from err
        except Exception as err:
            raise UpdateFailed("Error communicating with API") from err
