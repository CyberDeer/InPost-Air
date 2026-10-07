"""Define tests for config flow"""

from unittest.mock import AsyncMock, patch
from custom_components.inpost_air import config_flow
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
