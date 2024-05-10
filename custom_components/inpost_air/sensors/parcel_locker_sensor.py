from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.core import callback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.inpost_air.api import ParcelLocker
from custom_components.inpost_air.coordinator import ValueWithNorm, ValueWithoutNorm
from custom_components.inpost_air.utils import get_device_info


@dataclass(kw_only=True)
class ParcelLockerSensorEntityDescription(SensorEntityDescription):
    """Describes Example sensor entity."""

    value_fn: Callable[[dict[str, ValueWithNorm | ValueWithoutNorm]], StateType] = None
    exists_fn: Callable[[dict[str, ValueWithNorm | ValueWithoutNorm]], bool] = None

    def __post_init__(self):
        """Post init."""
        self.exists_fn = (
            (
                lambda data: item.value is not None
                if (item := data.get(self.key)) is not None
                else None
            )
            if self.exists_fn is None
            else self.exists_fn
        )


class ParcelLockerSensor(CoordinatorEntity, SensorEntity):
    """
    Represents a sensor entity for a parcel locker.
    """

    entity_description: ParcelLockerSensorEntityDescription

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
        self._attr_device_info = get_device_info(device)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_native_value = self.entity_description.value_fn(
            self.coordinator.data
        )
        self.async_write_ha_state()
