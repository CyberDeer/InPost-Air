"""Define tests for config flow"""

from unittest import mock
from unittest.mock import patch
from custom_components.inpost_air import config_flow
from custom_components.inpost_air.api import InPostApi
from custom_components.inpost_air.models import (
    InPostAirPoint,
    InPostAirPointCoordinates,
)

mocked_lockers_list: list[InPostAirPoint] = [
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
    ),
]


async def test_flow_init(hass):
    """Test the initial flow."""
    with patch.object(InPostApi, "get_parcel_lockers_list") as get_parcel_lockers_list:
        get_parcel_lockers_list.return_value = mocked_lockers_list

        result = await hass.config_entries.flow.async_init(
            config_flow.DOMAIN, context={"source": "user"}
        )

    assert {
        "data_schema": mock.ANY,
        "description_placeholders": None,
        "errors": {},
        "flow_id": mock.ANY,
        "handler": "inpost_air",
        "step_id": "user",
        "type": "form",
        "last_step": None,
        "preview": None,
    } == result
