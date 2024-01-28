"""Sensor platform for integration_blueprint."""
from __future__ import annotations
from dataclasses import dataclass
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import InPostAirDataUpdateCoordinator
from .entity import InPostAirEntity, InPostAirEntityDescription


@dataclass
class InPostAirSensorEntityDescription(
    InPostAirEntityDescription, SensorEntityDescription
):
    """Describes InPostAir sensor entity."""
    
SENSORS = {
    "air_index_level": InPostAirSensorEntityDescription(
        property_key="air_index_level",
        name="Air Index Level",
        # device_class=SensorDeviceClass.AQI,
    ),
    "PM1": InPostAirSensorEntityDescription(
        property_key="PM1",
        name="PM1",
        native_unit_of_measurement="µg/m³",
        device_class=SensorDeviceClass.PM1,
    ),
    "PM4": InPostAirSensorEntityDescription(
        property_key="PM4",
        name="PM4",
        icon="mdi:molecule",
        native_unit_of_measurement="µg/m³",
    ),
    "PM10": InPostAirSensorEntityDescription(
        property_key="PM10",
        name="PM10",
        native_unit_of_measurement="µg/m³",
        device_class=SensorDeviceClass.PM10,
    ),
    "PM25": InPostAirSensorEntityDescription(
        property_key="PM25",
        name="PM25",
        native_unit_of_measurement="µg/m³",
        device_class=SensorDeviceClass.PM25,
    ),
    "NO2": InPostAirSensorEntityDescription(
        property_key="NO2",
        name="NO2",
        native_unit_of_measurement="µg/m³",
        device_class=SensorDeviceClass.NITROGEN_DIOXIDE,
    ),
    "O3": InPostAirSensorEntityDescription(
        property_key="O3",
        name="O3",
        native_unit_of_measurement="µg/m³",
        device_class=SensorDeviceClass.OZONE,
    ),
    "TEMPERATURE": InPostAirSensorEntityDescription(
        property_key="TEMPERATURE",
        name="Temperature",
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    "PRESSURE": InPostAirSensorEntityDescription(
        property_key="PRESSURE",
        name="Pressure",
        native_unit_of_measurement="hPa",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
    ),
    "HUMIDITY": InPostAirSensorEntityDescription(
        property_key="HUMIDITY",
        name="Humidity",
        native_unit_of_measurement="%",
        device_class=SensorDeviceClass.HUMIDITY,
    ),
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up InPost sensor based on a config entry."""
    coordinator: InPostAirDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    fetched_sensors = await coordinator.get_sensors()


    for fetched_sensor in fetched_sensors:
        if fetched_sensor in SENSORS:
            async_add_entities([InPostAirSensorEntity(coordinator, SENSORS[fetched_sensor])])
        elif "norm" in fetched_sensor:
            async_add_entities([InPostAirSensorEntity(coordinator, InPostAirSensorEntityDescription(property_key=fetched_sensor, name=fetched_sensor.replace('_',' '), native_unit_of_measurement="%"))])
        else:
            async_add_entities([InPostAirSensorEntity(coordinator, InPostAirSensorEntityDescription(property_key=fetched_sensor, name=fetched_sensor))])
            
class InPostAirSensorEntity(InPostAirEntity, SensorEntity):
    """Defines a InPost sensor entity."""

    def __init__(
        self,
        coordinator: InPostAirDataUpdateCoordinator,
        description: InPostAirSensorEntityDescription,
    ) -> None:
        """Initialize a InPost sensor entity."""
        super().__init__(coordinator, description)

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        if self.entity_description.property_key == "air_index_level" :
            return self.coordinator.data.get("air_index_level")
        
        for sensor in self.coordinator.data.get("air_sensors"):
            [name, value, norm] = sensor.split(":")
            key = self.entity_description.property_key
            if name == key:
                return value
            if "norm" in key and len(norm) > 0 and name in key:
                return norm
            
        raise NotImplementedError(f"Missing sensor support: {self.entity_description.property_key}")