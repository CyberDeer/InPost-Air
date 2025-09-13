"""Functions to connect to InPost APIs."""

import asyncio
from dataclasses import dataclass
import logging
import re
from aiohttp import ClientResponse
from dacite import from_dict
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from custom_components.inpost_air.models import InPostAirPoint
from custom_components.inpost_air.utils import get_parcel_locker_url

_LOGGER = logging.getLogger(__name__)


@dataclass
class ParcelLockerListResponse:
    date: str
    page: int
    total_pages: int
    items: list[InPostAirPoint]


@dataclass
class ParcelLockerAirDataResponse:
    message: str
    air_index_level: str
    air_sensors: list[str]


class InPostApi:
    """Helper functions for the Air integration."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Init class."""
        self.hass = hass
        self.session = async_create_clientsession(hass)

    async def _request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
    ) -> ClientResponse:
        """Get information from the API."""
        try:
            async with asyncio.timeout(30):
                response = await self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                )
                response.raise_for_status()

                return response

        except TimeoutError as e:
            _LOGGER.warning("Request timed out")
            raise InPostAirApiClientError("Request timed out") from e
        except Exception as exception:  # pylint: disable=broad-except
            raise InPostAirApiClientError(
                "Something really wrong happened!"
            ) from exception

    async def search_parcel_locker(self, locker_code: str) -> InPostAirPoint | None:
        """Find info about given parcel locker."""
        if not locker_code or locker_code == "":
            return None

        response = await self._request(
            method="get", url="https://inpost.pl/sites/default/files/points.json"
        )
        parcel_locker = next(
            (
                x
                for x in (await response.json()).get("items")
                if x.get("n") == locker_code
            ),
            None,
        )

        return from_dict(InPostAirPoint, parcel_locker) if parcel_locker else None

    async def get_parcel_lockers_list(self) -> list[InPostAirPoint]:
        """Get parcel lockers list."""
        response = await self._request(
            method="get", url="https://inpost.pl/sites/default/files/points.json"
        )
        response_data = from_dict(ParcelLockerListResponse, await response.json())

        return response_data.items

    async def find_parcel_locker_id(self, point: InPostAirPoint) -> str | None:
        """Find parcel locker ID by its code."""
        response = await self._request(
            method="get",
            url=get_parcel_locker_url(point),
        )
        match = re.search(
            r"data-shipx-url=\"/shipx-point-data/(.*?)/(.*?)/air_index_level\"",
            await response.text(),
        )

        return None if match is None else match.group(1)

    async def get_parcel_locker_air_data(
        self, locker_code: str, locker_id: str
    ) -> ParcelLockerAirDataResponse:
        """Get air data from parcel locker."""
        response = await self._request(
            method="post",
            url=f"https://inpost.pl/shipx-point-data/{locker_id}/{locker_code}/air_index_level",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        return from_dict(ParcelLockerAirDataResponse, await response.json())


class InPostAirApiClientError(Exception):
    """Exception to indicate a general API error."""
