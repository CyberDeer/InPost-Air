"""Functions to connect to InPost APIs."""
import asyncio
import logging
import re
from typing import Any

from aiohttp import ClientResponse

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

_LOGGER = logging.getLogger(__name__)


class ParcelLocker:
    """ParcelLocker class."""

    def __init__(self, locker_code: str, locker_id: str) -> None:
        """Init class."""
        self.locker_code = locker_code
        self.locker_id = locker_id


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

        except TimeoutError:
            _LOGGER.warning("Request timed out")
        except Exception as exception:  # pylint: disable=broad-except
            raise InPostAirApiClientError(
                "Something really wrong happened!"
            ) from exception

    async def search_parcel_locker(self, locker_code: str) -> dict[str:Any] | None:
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

        return parcel_locker

    async def find_parcel_locker_id(self, device: ParcelLocker) -> str | None:
        """Find parcel locker ID by its code."""
        special_char_map = {
            ord("ę"): "e",
            ord("ó"): "o",
            ord("ą"): "a",
            ord("ś"): "s",
            ord("ł"): "l",
            ord("ż"): "z",
            ord("ź"): "x",
            ord("ć"): "c",
            ord("ń"): "n",
        }
        g = device["g"]
        n = device["n"].lower()
        e = device["e"].lower().translate(special_char_map)
        r = device["r"].translate(special_char_map)
        response = await self._request(
            method="get",
            url=f"https://inpost.pl/paczkomat-{g}-{n}-{e}-paczkomaty-{r}",
        )

        return re.search(
            r"data-shipx-url=\"/shipx-point-data/(.*?)/(.*?)/air_index_level\"",
            await response.text(),
        ).group(1)

    async def get_parcel_locker_air_data(self, locker_code: str, locker_id: str) -> Any:
        """Get air data from parcel locker."""
        response = await self._request(
            method="post",
            url=f"https://inpost.pl/shipx-point-data/{locker_id}/{locker_code}/air_index_level",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

        return await response.json()


class InPostAirApiClientError(Exception):
    """Exception to indicate a general API error."""
