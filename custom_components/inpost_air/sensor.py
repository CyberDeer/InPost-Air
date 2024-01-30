"""Sensor utilities and definitions."""

from collections.abc import Callable
from dataclasses import dataclass
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    PERCENTAGE,
    EntityCategory,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import InPostApi, ParcelLocker
from .const import DOMAIN, Entities
from .coordinator import InPostAirDataCoordinator, ValueWithNorm, ValueWithoutNorm

_LOGGER = logging.getLogger(__name__)


@dataclass(kw_only=True)
class ParcelLockerSensorEntityDescription(SensorEntityDescription):
    """Describes Example sensor entity."""

    exists_fn: Callable[[dict[str, ValueWithNorm | ValueWithoutNorm]], bool] = (
        lambda _: True
    )
    value_fn: Callable[[dict[str, ValueWithNorm | ValueWithoutNorm]], StateType]


SENSORS_DESCRIPTIONS = [
    ParcelLockerSensorEntityDescription(
        key=Entities.Temperature,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda data: item.value
        if (item := data.get(Entities.Temperature))
        else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.PM2_5,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM25,
        value_fn=lambda data: item.value
        if (item := data.get(Entities.PM2_5))
        else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.PM2_5_Norm,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:percent",
        value_fn=lambda data: item.norm if (item := data.get(Entities.PM2_5)) else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.Pressure,
        native_unit_of_measurement=UnitOfPressure.HPA,
        device_class=SensorDeviceClass.PRESSURE,
        value_fn=lambda data: item.value
        if (item := data.get(Entities.Pressure))
        else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.Humidity,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        value_fn=lambda data: item.value
        if (item := data.get(Entities.Humidity))
        else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.PM1,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM1,
        value_fn=lambda data: item.value if (item := data.get(Entities.PM1)) else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.PM10,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM10,
        value_fn=lambda data: item.value if (item := data.get(Entities.PM10)) else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.PM10_Norm,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:percent",
        value_fn=lambda data: item.norm if (item := data.get(Entities.PM10)) else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.PM4,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        icon="mdi:molecule",
        value_fn=lambda data: item.value if (item := data.get(Entities.PM4)) else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.NO2,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.NITROGEN_DIOXIDE,
        value_fn=lambda data: item.value if (item := data.get(Entities.NO2)) else None,
    ),
    ParcelLockerSensorEntityDescription(
        key=Entities.O3,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.OZONE,
        value_fn=lambda data: item.value if (item := data.get(Entities.O3)) else None,
    ),
]


class ParcelLockerSensorEntity(CoordinatorEntity, SensorEntity):
    """Represent an Example sensor."""

    entity_description: ParcelLockerSensorEntityDescription
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
        device: ParcelLocker,
        entity_description: ParcelLockerSensorEntityDescription,
    ) -> None:
        """Set up the instance."""
        super().__init__(coordinator, context=device)

        self._device = device
        self.entity_description = entity_description
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{device.locker_code}_{entity_description.key}"
        self._attr_suggested_display_precision = 2
        self._attr_translation_key = entity_description.key.lower()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.locker_code, device.locker_id)},
            name=f"Parcel locker {device.locker_code}",
            manufacturer="InPost",
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = self.entity_description.value_fn(
            self.coordinator.data
        )
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setups sensors from config entry."""
    parcel_locker = hass.data[DOMAIN][entry.entry_id]
    coordinator = InPostAirDataCoordinator(hass, InPostApi(hass), parcel_locker)

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        [
            ParcelLockerSensorEntity(coordinator, parcel_locker, description)
            for description in SENSORS_DESCRIPTIONS
        ],
        update_before_add=True,
    )
