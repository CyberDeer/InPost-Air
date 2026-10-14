from unittest.mock import AsyncMock, Mock, patch
import pytest
import pytest_socket
import os
import socket
from aiohttp.resolver import ThreadedResolver
from homeassistant.helpers import aiohttp_client
from custom_components.inpost_air.api import InPostApi
from custom_components.inpost_air.models import (
    InPostAirPoint,
    InPostAirPointCoordinates,
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
    pytest_socket.socket_allow_hosts(["inpost.pl"])


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


@pytest.mark.skipif(
    os.environ.get("CI") == "true", reason="InPost blocks Github IP address"
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.api
async def test_find_parcel_locker_id(hass, _allow_inpost_requests):
    response = await InPostApi(hass).find_parcel_locker_id(
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


@pytest.mark.skipif(
    os.environ.get("CI") == "true", reason="InPost blocks Github IP address"
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.api
async def test_air_data(hass, _allow_inpost_requests):
    response = await InPostApi(hass).get_parcel_locker_air_data("AJE01BAPP", "56311")
    assert response is not None


def _mock_page(html: str) -> Mock:
    page = Mock()
    page.text = AsyncMock(return_value=html)
    return page


async def test_find_parcel_locker_id_falls_back_to_english_page(hass):
    """Locker without a Polish page is resolved from its English page."""
    point = Mock(spec=InPostAirPoint)
    point.n = "KUKU01BAPP"
    point.g = "kuków"
    point.e = "Kuków"
    point.r = "małopolskie"
    api = InPostApi(hass)
    marker = (
        '<div data-shipx-url="/en/shipx-point-data/12345/KUKU01BAPP/air_index_level">'
    )

    with patch.object(
        api,
        "_request",
        side_effect=[_mock_page("<html>finder</html>"), _mock_page(marker)],
    ) as request:
        assert await api.find_parcel_locker_id(point) == "12345"

    en_url = "https://inpost.pl/en/parcel-locker-kukow-kuku01bapp-kukow-paczkomaty-malopolskie"
    assert request.call_args.kwargs["url"] == en_url
    assert api._parcel_locker_urls["KUKU01BAPP"] == en_url


async def test_find_parcel_locker_id_without_any_page(hass):
    """Locker missing in both languages has no ID."""
    point = Mock(spec=InPostAirPoint)
    point.n = "KUKU02APP"
    point.g = "kuków"
    point.e = "Kuków"
    point.r = "małopolskie"
    api = InPostApi(hass)

    with patch.object(
        api, "_request", side_effect=[_mock_page(""), _mock_page("")]
    ) as request:
        assert await api.find_parcel_locker_id(point) is None

    assert request.call_count == 2
