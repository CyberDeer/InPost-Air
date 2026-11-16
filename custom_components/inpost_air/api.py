"""Functions to connect to InPost APIs."""

import asyncio
from dataclasses import dataclass
import logging
from urllib.parse import quote, urlencode

from aiohttp import ClientError, ClientResponse, ClientResponseError
from dacite import Config, DaciteError, from_dict
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from custom_components.inpost_air.models import StoredLockerPoint
from custom_components.inpost_air.utils import haversine

_LOGGER = logging.getLogger(__name__)


@dataclass
class NearbyLocker:
    """A nearby locker and its distance in metres."""

    name: str
    distance: float
    location_description: str | None


# Public points API. The InPost app reads the same payload shape
# (`fromDateTime`, `values`, `standards`, `index`).
AIR_SENSORS_URL = (
    "https://api-pl-points.easypack24.net/v1/points/{locker_code}/air-sensors"
)
POINTS_URL = "https://api-pl-points.easypack24.net/v1/points"


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
            _LOGGER.warning("Request timed out: %s", url)
            raise InPostAirApiClientError(f"Request timed out: {url}") from e
        except ClientResponseError as e:
            if raise_client_response_error:
                raise
            raise InPostAirApiClientError(
                f"HTTP {e.status} while requesting {url}"
            ) from e
        except Exception as exception:  # pylint: disable=broad-except
            raise InPostAirApiClientError(
                f"Network error while requesting {url}: {exception}"
            ) from exception

    async def search_parcel_locker(self, locker_code: str) -> StoredLockerPoint | None:
        """Find info about given parcel locker."""
        if not locker_code:
            return None

        try:
            response = await self._request(
                method="get",
                url=f"{POINTS_URL}/{quote(locker_code, safe='')}",
                raise_client_response_error=True,
            )
        except ClientResponseError as err:
            if err.status == 404:
                return None

            raise InPostAirApiClientError("Failed to find parcel locker") from err

        try:
            payload = await response.json()
            code = payload["name"]
            address = payload.get("address_details") or {}
        except (ClientError, ValueError, KeyError, TypeError) as err:
            raise InPostAirApiClientError(
                f"Unexpected parcel locker payload: {err}"
            ) from err

        return StoredLockerPoint(
            code=code,
            city=str(address.get("city") or "").lower(),
            street=str(address.get("street") or ""),
            province=str(address.get("province") or ""),
        )

    async def get_parcel_lockers_list(
        self, latitude: float, longitude: float
    ) -> list[NearbyLocker]:
        """Get parcel lockers ordered by distance from the given coordinates."""
        query = urlencode(
            {
                "type": "parcel_locker_only",
                "fields": "name,location,location_description,air_index_level",
                "per_page": 50000,
            }
        )
        response = await self._request(method="get", url=f"{POINTS_URL}?{query}")
        try:
            items = (await response.json())["items"]
        except (ClientError, ValueError, KeyError, TypeError) as err:
            raise InPostAirApiClientError(f"Unexpected points payload: {err}") from err

        lockers = []

        for item in items:
            if not isinstance(item, dict):
                continue

            if item.get("air_index_level") is None:
                continue

            name = item.get("name")
            if not name:
                continue

            location = item.get("location") or {}
            lat, lon = location.get("latitude"), location.get("longitude")

            if lat is None or lon is None:
                continue

            lockers.append(
                NearbyLocker(
                    name=name,
                    distance=haversine(longitude, latitude, float(lon), float(lat))
                    * 1000,
                    location_description=item.get("location_description"),
                )
            )

        return sorted(lockers, key=lambda locker: locker.distance)

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
            raise InPostAirApiClientError(
                f"HTTP {err.status} while requesting air data"
            ) from err
        except Exception as exception:  # pylint: disable=broad-except
            raise InPostAirApiClientError(
                f"Network error while requesting air data: {exception}"
            ) from exception

        try:
            return from_dict(
                ParcelLockerAirDataResponse,
                payload,
                config=Config(cast=[float]),
            )
        except DaciteError as err:
            raise InPostAirApiClientError(
                f"Unexpected air data payload: {err}"
            ) from err


class InPostAirApiClientError(Exception):
    """Exception to indicate a general API error."""


class InPostAirApiClientSensorsMissingError(InPostAirApiClientError):
    """Exception to indicate missing air sensors error"""
