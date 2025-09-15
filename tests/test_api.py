import pytest
import pytest_socket
from custom_components.inpost_air.api import InPostApi
from custom_components.inpost_air.models import (
    InPostAirPoint,
    InPostAirPointCoordinates,
)


@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.api
async def test_parcel_lockers_list(hass):
    pytest_socket.enable_socket()
    pytest_socket.socket_allow_hosts(["inpost.pl"])

    api = InPostApi(hass)
    response = await api.get_parcel_lockers_list()
    assert response is not None


@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.api
async def test_parcel_locker_search(hass):
    pytest_socket.enable_socket()
    pytest_socket.socket_allow_hosts(["inpost.pl"])

    api = InPostApi(hass)
    response = await api.search_parcel_locker("AJE01BAPP")
    assert response is not None


@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.api
async def test_find_parcel_locker_id(hass):
    pytest_socket.enable_socket()
    pytest_socket.socket_allow_hosts(["inpost.pl"])

    api = InPostApi(hass)
    response = await api.find_parcel_locker_id(
        InPostAirPoint(
            "AJE01BAPP",
            1,
            "Market Dino",
            "",
            "",
            "006",
            "Andrzejewo",
            "andrzejewo",
            "Warszawska",
            "mazowieckie",
            "07-305",
            "62A",
            "24/7",
            "[]",
            InPostAirPointCoordinates(52.83679, 22.20968),
            0,
            1,
        )
    )
    assert response is not None


@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.api
async def test_air_data(hass):
    pytest_socket.enable_socket()
    pytest_socket.socket_allow_hosts(["inpost.pl"])

    api = InPostApi(hass)
    response = await api.get_parcel_locker_air_data("AJE01BAPP", "56311")
    assert response is not None
