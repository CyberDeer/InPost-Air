"""InPost API data coordinator."""

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging
import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .models import ParcelLocker
from .api import InPostApi
from .const import Entities

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


def create_value(sensor_line: str) -> ValueWithNorm | ValueWithoutNorm | None:
    """Create value class from sensor data string."""
    if match := re.match(r"PM25:(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)", sensor_line):
        return ValueWithNorm(
            Entities.PM2_5, float(match.group(1)), float(match.group(2))
        )
    if match := re.match(r"PM10:(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)", sensor_line):
        return ValueWithNorm(
            Entities.PM10, float(match.group(1)), float(match.group(2))
        )
    if match := re.match(r"PM1:(\d+(?:\.\d+)?):", sensor_line):
        return ValueWithoutNorm(Entities.PM1, float(match.group(1)))
    if match := re.match(r"PM4:(\d+(?:\.\d+)?):", sensor_line):
        return ValueWithoutNorm(Entities.PM4, float(match.group(1)))
    if match := re.match(r"TEMPERATURE:(-?\d+(?:\.\d+)?):", sensor_line):
        return ValueWithoutNorm(Entities.Temperature, float(match.group(1)))
    if match := re.match(r"PRESSURE:(\d+(?:\.\d+)?):", sensor_line):
        return ValueWithoutNorm(Entities.Pressure, float(match.group(1)))
    if match := re.match(r"HUMIDITY:(\d+(?:\.\d+)?):", sensor_line):
        return ValueWithoutNorm(Entities.Humidity, float(match.group(1)))
    if match := re.match(r"NO2:(\d+(?:\.\d+)?):", sensor_line):
        return ValueWithoutNorm(Entities.NO2, float(match.group(1)))
    if match := re.match(r"O3:(\d+(?:\.\d+)?):", sensor_line):
        return ValueWithoutNorm(Entities.O3, float(match.group(1)))


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
                    self.parcel_locker.locker_code, self.parcel_locker.locker_id
                )

                return {
                    x.name: x for line in data.air_sensors if (x := create_value(line))
                }
        except Exception as err:
            raise UpdateFailed("Error communicating with API") from err
