"""Functions to connect to InPost APIs."""

import asyncio
from dataclasses import dataclass
import logging

from aiohttp import ClientResponse, ClientResponseError
from dacite import Config, from_dict
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from custom_components.inpost_air.models import InPostAirPoint

_LOGGER = logging.getLogger(__name__)


@dataclass
class ParcelLockerListResponse:
    date: str
    page: int
    total_pages: int
    items: list[InPostAirPoint]


# Public points API. The InPost app reads the same payload shape
# (`fromDateTime`, `values`, `standards`, `index`).
AIR_SENSORS_URL = (
    "https://api-pl-points.easypack24.net/v1/points/{locker_code}/air-sensors"
)


@dataclass
class AirSensorReading:
    """Single measurement from the points air-sensors endpoint."""

    name: str
    value: float
    level: str | None = None


@dataclass
class AirSensorIndex:
    """Official air quality index returned with the measurements."""

    name: str
    value: float
    level: str | None = None


@dataclass
class AirSensorStandard:
    """Limit and percentage of a reference standard, such as WHO."""

    name: str
    pollutant: str
    limit: float
    percent: float


@dataclass
class AirSensorWindow:
    """Current measurement window."""

    fromDateTime: str
    tillDateTime: str
    values: list[AirSensorReading]
    index: AirSensorIndex | None = None
    standards: list[AirSensorStandard] | None = None


@dataclass
class ParcelLockerAirDataResponse:
    """Air sensor payload for one parcel locker."""

    current: AirSensorWindow
    sensorOrigin: int | None = None


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
        raise_client_response_error: bool = False,
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
        except ClientResponseError as e:
            if raise_client_response_error:
                raise
            raise InPostAirApiClientError("Something really wrong happened!") from e
        except Exception as exception:  # pylint: disable=broad-except
            raise InPostAirApiClientError(
                "Something really wrong happened!"
            ) from exception

    async def _search_easypack24_locker(
        self, locker_code: str
    ) -> InPostAirPoint | None:
        """Find info about given parcel locker."""
        if not locker_code or locker_code == "":
            return None

        response = await self._request(
            method="get",
            url="https://api-shipx-pl.easypack24.net/v1/points/" + locker_code,
        )
        resp = await response.json()

        error = resp.get("error")
        if error:
            _LOGGER.warning(f"easypack24.net for {locker_code} returned error: {resp}")
            return None

        resp_address = resp.get("address_details", {})
        location = resp.get("location", {"latitude": "0", "longitude": "0"})
        city = resp_address.get("city") or ""

        parcel_locker = {
            "n": resp["name"],
            "t": 1,
            "d": resp["location_description"],
            "m": resp.get("apm_doubled") or "",
            "q": resp.get("partner_id") or "",
            "f": resp.get("physical_type_mapped") or "",
            "c": city,
            "g": city.lower(),
            "e": resp_address.get("street") or "",
            "r": resp_address.get("province") or "",
            "o": resp_address.get("post_code") or "",
            "b": resp_address.get("building_number") or "",
            "h": resp.get("opening_hours") or "",
            "i": "[]",  # Unknown
            "l": {"a": location["latitude"], "o": location["longitude"]},
            "p": 1 if resp.get("payment_type", {"0": ""}) == "0" else 0,
            "s": 1,  # Unkown - most lockers have 1 here
        }
        return parcel_locker

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

        if not parcel_locker:
            parcel_locker = await self._search_easypack24_locker(locker_code)

        return from_dict(InPostAirPoint, parcel_locker) if parcel_locker else None

    async def get_parcel_lockers_list(self) -> list[InPostAirPoint]:
        """Get parcel lockers list."""
        response = await self._request(
            method="get", url="https://inpost.pl/sites/default/files/points.json"
        )
        response_data = from_dict(ParcelLockerListResponse, await response.json())

        return response_data.items

    async def get_parcel_locker_air_data(
        self, locker_code: str
    ) -> ParcelLockerAirDataResponse:
        """Get air data from the public points API."""
        try:
            async with asyncio.timeout(30):
                async with self.session.get(
                    AIR_SENSORS_URL.format(locker_code=locker_code)
                ) as response:
                    if response.status == 404:
                        raise InPostAirApiClientSensorsMissingError(
                            "Air sensors are not available"
                        )

                    response.raise_for_status()
                    payload = await response.json()
        except InPostAirApiClientSensorsMissingError:
            raise
        except TimeoutError as err:
            _LOGGER.warning("Request timed out")
            raise InPostAirApiClientError("Request timed out") from err
        except ClientResponseError as err:
            raise InPostAirApiClientError("Something really wrong happened!") from err
        except Exception as exception:  # pylint: disable=broad-except
            raise InPostAirApiClientError(
                "Something really wrong happened!"
            ) from exception

        return from_dict(
            ParcelLockerAirDataResponse,
            payload,
            config=Config(cast=[float]),
        )


class InPostAirApiClientError(Exception):
    """Exception to indicate a general API error."""


class InPostAirApiClientSensorsMissingError(InPostAirApiClientError):
    """Exception to indicate missing air sensors error"""
