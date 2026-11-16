"""Define tests for config flow"""

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.inpost_air import config_flow
from custom_components.inpost_air.api import InPostAirApiClientError, InPostApi
from custom_components.inpost_air.const import DOMAIN
from custom_components.inpost_air.models import (
    LegacyLockerPoint,
    InPostAirPointCoordinates,
    StoredLockerPoint,
)

mocked_lockers_list: list[LegacyLockerPoint] = [
    LegacyLockerPoint(
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
    ),
]


async def test_flow_init(hass):
    """Test that initial setup creates the parent without a confirmation form."""
    with patch(
        "custom_components.inpost_air.async_setup_entry",
        new=AsyncMock(return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            config_flow.DOMAIN, context={"source": "user"}
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "InPost Air"
    assert result["data"] == {}

    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    assert result["reason"] == "single_instance_allowed"


async def test_validate_input_locker_lookup_unreachable(hass):
    """Transport errors during lookup are reported as cannot_connect."""
    with patch.object(
        InPostApi,
        "search_parcel_locker",
        side_effect=InPostAirApiClientError("HTTP 503"),
    ):
        with pytest.raises(config_flow.CannotConnect):
            await config_flow.validate_input(hass, {"parcelLockerId": "AJE01BAPP"})


async def test_validate_input_air_data_unreachable(hass):
    """A network failure on the air-sensors call is not 'no air data'."""
    point = StoredLockerPoint("AJE01BAPP", "andrzejewo", "Warszawska", "mazowieckie")
    with (
        patch.object(InPostApi, "search_parcel_locker", return_value=point),
        patch.object(
            InPostApi,
            "get_parcel_locker_air_data",
            side_effect=InPostAirApiClientError("Request timed out"),
        ),
    ):
        with pytest.raises(config_flow.CannotConnect):
            await config_flow.validate_input(hass, {"parcelLockerId": "AJE01BAPP"})


async def test_subentry_form_survives_unreachable_locker_list(hass):
    """The form still allows manual entry when the locker list is down."""
    entry = MockConfigEntry(
        domain=DOMAIN, version=3, minor_version=3, title="InPost Air", data={}
    )
    entry.add_to_hass(hass)
    with patch.object(
        InPostApi,
        "get_parcel_lockers_list",
        side_effect=InPostAirApiClientError("HTTP 503"),
    ):
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, "parcel_locker"), context={"source": "user"}
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "cannot_connect"}
