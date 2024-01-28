"""Sensor platform for integration_blueprint."""
from __future__ import annotations
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
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

SENSORS: tuple[InPostAirSensorEntityDescription, ...] = (
    InPostAirSensorEntityDescription(
        key="air_index_description",
        name="Air Index Description",
        icon="mdi:emoticon-poop",
    ),
    InPostAirSensorEntityDescription(
        key="temperature",
        name="Temperature",
        icon="mdi:thermometer",
    ),
    InPostAirSensorEntityDescription(
        key="humidity",
        name="Humidity",
        icon="mdi:water-percent",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dreame Vacuum sensor based on a config entry."""
    coordinator: InPostAirDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        InPostAirSensorEntity(coordinator, description)
        for description in SENSORS
    )

class InPostAirSensorEntity(InPostAirEntity, SensorEntity):
    """Defines a InPost sensor entity."""

    def __init__(
        self,
        coordinator: InPostAirDataUpdateCoordinator,
        description: InPostAirSensorEntityDescription,
    ) -> None:
        """Initialize a InPost sensor entity."""
        super().__init__(coordinator, description)