from unittest.mock import AsyncMock, Mock
import pytest
import pytest_socket
import socket
from aiohttp import ClientResponseError
from aiohttp.resolver import ThreadedResolver
from homeassistant.helpers import aiohttp_client
from custom_components.inpost_air.api import (
    InPostAirApiClientError,
    InPostAirApiClientSensorsMissingError,
    InPostApi,
)
from custom_components.inpost_air.const import Entities
from custom_components.inpost_air.coordinator import (
    ValueWithNorm,
    readings_from_air_data,
)

_real_getaddrinfo = socket.getaddrinfo


@pytest.fixture()
def _allow_inpost_requests(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _real_getaddrinfo)

    def make_resolver(*args, **kwargs):
        resolver = ThreadedResolver()
        # The HA test plugin calls real_close when cleaning up shared resolvers.
        resolver.real_close = resolver.close
        return resolver

    # Live API tests need real DNS without starting Home Assistant's Zeroconf.
    monkeypatch.setattr(
        aiohttp_client,
        "_async_make_resolver",
        make_resolver,
    )
    pytest_socket.enable_socket()
    pytest_socket.socket_allow_hosts(
        ["inpost.pl", "api-pl-points.easypack24.net", "easypack24.net"],
        allow_unix_socket=True,
    )


@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.api
async def test_parcel_lockers_list(hass, _allow_inpost_requests):
    response = await InPostApi(hass).get_parcel_lockers_list()
    assert response is not None


@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.api
async def test_parcel_locker_search(hass, _allow_inpost_requests):
    response = await InPostApi(hass).search_parcel_locker("AJE01BAPP")
    assert response is not None


@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.api
async def test_air_data(hass, _allow_inpost_requests):
    response = await InPostApi(hass).get_parcel_locker_air_data("AJE01BAPP")
    readings = readings_from_air_data(response)
    assert readings[Entities.PM2_5].value > 0
    assert readings[Entities.Temperature].value is not None


@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.api
async def test_air_data_missing_sensors_live(hass, _allow_inpost_requests):
    """A locker without a sensor is a missing-data error, not a client failure."""
    with pytest.raises(InPostAirApiClientSensorsMissingError):
        await InPostApi(hass).get_parcel_locker_air_data("SPA01N")


def _points_payload() -> dict:
    return {
        "current": {
            "fromDateTime": "2026-10-27T09:43:40.385Z",
            "tillDateTime": "2026-10-27T10:58:40.385Z",
            "values": [
                {"name": "PM1", "value": 5, "level": None},
                {"name": "PM25", "value": 13.14, "level": "GOOD"},
                {"name": "PM10", "value": 26.91, "level": "GOOD"},
                {"name": "TEMPERATURE", "value": 14.26, "level": None},
                {"name": "NO2", "value": 8.5, "level": None},
                {"name": "UNKNOWN", "value": 1, "level": None},
            ],
            "index": {"name": "PIJP", "value": 24.54, "level": "GOOD"},
            "standards": [
                {"name": "WHO", "pollutant": "PM25", "limit": 25, "percent": 52.57},
                {"name": "WHO", "pollutant": "PM10", "limit": 50, "percent": 53.83},
                {"name": "EU", "pollutant": "PM25", "limit": 20, "percent": 65},
            ],
        },
        "sensorOrigin": 2,
    }


async def test_air_data_parses_points_payload(hass):
    """Measurements and WHO percentages come from the points API payload."""
    response = Mock()
    response.status = 200
    response.json = AsyncMock(return_value=_points_payload())
    response.raise_for_status = Mock()
    session = Mock()
    session.get.return_value.__aenter__ = AsyncMock(return_value=response)
    session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    api = InPostApi(hass)
    api.session = session
    data = await api.get_parcel_locker_air_data("WAW644M")

    session.get.assert_called_once_with(
        "https://api-pl-points.easypack24.net/v1/points/WAW644M/air-sensors"
    )
    readings = readings_from_air_data(data)
    pm25 = readings[Entities.PM2_5]
    assert isinstance(pm25, ValueWithNorm)
    assert pm25.value == 13.14
    assert pm25.norm == 52.57
    assert readings[Entities.PM10].norm == 53.83
    assert readings[Entities.PM1].value == 5
    assert readings[Entities.NO2].value == 8.5
    assert Entities.O3 not in readings


async def test_air_data_missing_sensors(hass):
    """HTTP 404 means this locker has no air sensors."""
    response = Mock()
    response.status = 404
    session = Mock()
    session.get.return_value.__aenter__ = AsyncMock(return_value=response)
    session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    api = InPostApi(hass)
    api.session = session
    with pytest.raises(InPostAirApiClientSensorsMissingError):
        await api.get_parcel_locker_air_data("SPA01N")


async def test_air_data_http_error(hass):
    """Other HTTP failures stay generic client errors."""
    response = Mock()
    response.status = 500
    response.raise_for_status.side_effect = ClientResponseError(
        Mock(), (), status=500, message="error"
    )
    session = Mock()
    session.get.return_value.__aenter__ = AsyncMock(return_value=response)
    session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    api = InPostApi(hass)
    api.session = session
    with pytest.raises(InPostAirApiClientError) as err:
        await api.get_parcel_locker_air_data("WAW644M")
    assert not isinstance(err.value, InPostAirApiClientSensorsMissingError)
