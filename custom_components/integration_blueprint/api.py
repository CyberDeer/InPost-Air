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
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Sample API Client."""
        self._username = username
        self._password = password
        self._session = session

    async def async_get_data(self) -> any:
        """Get data from the API."""
        return await self._api_wrapper(
            method="post", 
            url="https://greencity.pl/shipx-point-data/615/x/air_index_level",
            headers={"X-Requested-With": "XMLHttpRequest"},
        )

    async def async_set_title(self, value: str) -> any:
        """Get data from the API."""
        return await self._api_wrapper(
            method="patch",
            url="https://jsonplaceholder.typicode.com/posts/1",
            data={"title": value},
            headers={"Content-type": "application/json; charset=UTF-8"},
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
