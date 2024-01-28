"""Sample API Client."""
from __future__ import annotations

import asyncio
import socket

import aiohttp
import async_timeout


class InPostAirApiClientError(Exception):
    """Exception to indicate a general API error."""


class InPostAirApiClientCommunicationError(
    InPostAirApiClientError
):
    """Exception to indicate a communication error."""


class InPostAirApiClientAuthenticationError(
    InPostAirApiClientError
):
    """Exception to indicate an authentication error."""


class InPostAirApiClient:
    """Sample API Client."""

    def __init__(
        self,
        machine_id: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._session = session

    async def async_get_data(self, machine_id, parcel_locker_id) -> any:
        """Get data from the API."""
        return await self._api_wrapper(
            method="post",
            url="https://greencity.pl/shipx-point-data/" + machine_id + "/"+ parcel_locker_id +"/air_index_level",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

    async def async_get_points(self) -> any:
        """Return points"""
        return await self._api_wrapper(
            method="get",
            url="https://greencity.pl/sites/default/files/points.json"
        )

    async def async_get_parcel_locker_web_details(self, point) -> any:
        """Get Parcel Locker ID"""
        return await self._api_wrapper(
            method="get",
            url=f"https://greencity.pl/paczkomat-{point['g']}-{point['n']}-{point['e']}-paczkomaty-{point['r']}"
        )

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> any:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                )
                if response.status in (401, 403):
                    raise InPostAirApiClientAuthenticationError(
                        "Invalid credentials",
                    )
                response.raise_for_status()
                return await response.json()

        except asyncio.TimeoutError as exception:
            raise InPostAirApiClientCommunicationError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise InPostAirApiClientCommunicationError(
                "Error fetching information",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            raise InPostAirApiClientError(
                "Something really wrong happened!"
            ) from exception
