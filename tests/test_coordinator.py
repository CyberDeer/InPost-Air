"""Coordinator tests: payload mapping, retries and retry_after handling."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.inpost_air.api import (
    AirSensorReading,
    AirSensorStandard,
    AirSensorWindow,
    InPostAirApiClientError,
    InPostAirApiClientSensorsMissingError,
    ParcelLockerAirDataResponse,
)
from custom_components.inpost_air.const import Entities
from custom_components.inpost_air.coordinator import (
    InPostAirDataCoordinator,
    ValueWithNorm,
    ValueWithoutNorm,
    readings_from_air_data,
)
from custom_components.inpost_air.models import ParcelLocker


def _air_response() -> ParcelLockerAirDataResponse:
    return ParcelLockerAirDataResponse(
        current=AirSensorWindow(
            fromDateTime="2026-11-12T05:13:57.071Z",
            tillDateTime="2026-11-12T06:28:57.071Z",
            values=[
                AirSensorReading("PM25", 3.45, "VERY_GOOD"),
                AirSensorReading("PM10", 3.49, "VERY_GOOD"),
                AirSensorReading("TEMPERATURE", 7.11),
                AirSensorReading("HUMIDITY", 99.99),
                AirSensorReading("SOMETHING_NEW", 1.0),
            ],
            standards=[
                AirSensorStandard("WHO", "PM25", 25.0, 14.25),
                AirSensorStandard("WHO", "PM10", 50.0, 7.35),
            ],
        )
    )


def _coordinator(hass, api) -> InPostAirDataCoordinator:
    return InPostAirDataCoordinator(hass, api, ParcelLocker("KUKU01BAPP"))


def test_readings_from_air_data():
    readings = readings_from_air_data(_air_response())

    # Unknown sensor names are skipped, known ones are mapped.
    assert set(readings) == {
        Entities.PM2_5,
        Entities.PM10,
        Entities.Temperature,
        Entities.Humidity,
    }

    pm25 = readings[Entities.PM2_5]
    assert isinstance(pm25, ValueWithNorm)
    assert pm25.value == 3.45
    assert pm25.norm == 14.25

    temperature = readings[Entities.Temperature]
    assert isinstance(temperature, ValueWithoutNorm)
    assert temperature.value == 7.11


async def test_coordinator_fetches_readings(hass):
    api = SimpleNamespace(
        get_parcel_locker_air_data=AsyncMock(return_value=_air_response())
    )
    coordinator = _coordinator(hass, api)

    data = await coordinator._async_update_data()

    assert data[Entities.PM2_5].value == 3.45
    assert data[Entities.Temperature].value == 7.11
    api.get_parcel_locker_air_data.assert_awaited_once_with("KUKU01BAPP")

    # The refresh interval is jittered so multiple lockers never poll at once.
    assert coordinator.update_interval is not None
    assert 300 <= coordinator.update_interval.total_seconds() <= 390


async def test_coordinator_retries_transient_errors(hass):
    api = SimpleNamespace(
        get_parcel_locker_air_data=AsyncMock(
            side_effect=InPostAirApiClientError("HTTP 500")
        )
    )
    coordinator = _coordinator(hass, api)

    with (
        patch("custom_components.inpost_air.coordinator.MAX_ATTEMPTS", 2),
        patch("custom_components.inpost_air.coordinator.RETRY_BACKOFF_SECONDS", (0,)),
    ):
        with pytest.raises(UpdateFailed, match="HTTP 500"):
            await coordinator._async_update_data()

    assert api.get_parcel_locker_air_data.call_count == 2


async def test_coordinator_missing_sensor_backs_off(hass):
    api = SimpleNamespace(
        get_parcel_locker_air_data=AsyncMock(
            side_effect=InPostAirApiClientSensorsMissingError(
                "Air sensors are not available"
            )
        )
    )
    coordinator = _coordinator(hass, api)

    with pytest.raises(UpdateFailed) as err:
        await coordinator._async_update_data()

    assert err.value.retry_after == 3600

    # Missing sensors are a persistent condition - no pointless retries.
    api.get_parcel_locker_air_data.assert_awaited_once()
