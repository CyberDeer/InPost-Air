"""Sensor utilities and definitions."""

from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from custom_components.inpost_air import InPostAirConfiEntry
from custom_components.inpost_air.coordinator import ValueWithNorm
from custom_components.inpost_air.sensors.aqi.european import (
    EuropeanAirQualityIndexSensor,
)
from custom_components.inpost_air.sensors.aqi.polish import PolishAirQualityIndexSensor
from custom_components.inpost_air.sensors.parcel_locker_sensor import (
    ParcelLockerSensor,
    ParcelLockerSensorEntityDescription,
)
from .const import Entities

# pylint: disable=locally-disabled, unexpected-keyword-arg
PARCEL_LOCKER_SENSORS = [
    ParcelLockerSensorEntityDescription(
        key=Entities.Temperature,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda data: item.value
        if (item := data.get(Entities.Temperature))
        else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.PM2_5,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PM25,
        value_fn=lambda data: item.value
        if (item := data.get(Entities.PM2_5))
        else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.PM2_5_Norm,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:percent",
        exists_fn=lambda data: item.value is not None
        if (item := data.get(Entities.PM10)) is not None
        else False,
        value_fn=lambda data: item.norm
        if (item := data.get(Entities.PM2_5)) and isinstance(item, ValueWithNorm)
        else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.Pressure,
        native_unit_of_measurement=UnitOfPressure.HPA,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PRESSURE,
        value_fn=lambda data: item.value
        if (item := data.get(Entities.Pressure))
        else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.Humidity,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.HUMIDITY,
        value_fn=lambda data: item.value
        if (item := data.get(Entities.Humidity))
        else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.PM1,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PM1,
        value_fn=lambda data: item.value if (item := data.get(Entities.PM1)) else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.PM10,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PM10,
        value_fn=lambda data: item.value if (item := data.get(Entities.PM10)) else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.PM10_Norm,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:percent",
        exists_fn=lambda data: item.value is not None
        if (item := data.get(Entities.PM10)) is not None
        else False,
        value_fn=lambda data: item.norm
        if (item := data.get(Entities.PM10)) and isinstance(item, ValueWithNorm)
        else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.PM4,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:molecule",
        value_fn=lambda data: item.value if (item := data.get(Entities.PM4)) else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.NO2,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.NITROGEN_DIOXIDE,
        value_fn=lambda data: item.value if (item := data.get(Entities.NO2)) else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.O3,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.OZONE,
        value_fn=lambda data: item.value if (item := data.get(Entities.O3)) else None,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InPostAirConfiEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setups sensors from config entry."""
    parcel_locker = entry.runtime_data.parcel_locker
    coordinator = entry.runtime_data.coordinator

    await coordinator.async_config_entry_first_refresh()

    base_sensors = [
        ParcelLockerSensor(coordinator, parcel_locker, description)
        for description in PARCEL_LOCKER_SENSORS
        if description.exists_fn(coordinator.data)
    ]

    async_add_entities(
        [
            *base_sensors,
            PolishAirQualityIndexSensor(parcel_locker),
            EuropeanAirQualityIndexSensor(parcel_locker),
        ],
        update_before_add=True,
    )
