from abc import abstractmethod
from datetime import timedelta

from homeassistant.components import recorder
from homeassistant.components.recorder import history
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.util import dt as dt_util

from custom_components.inpost_air import utils
from custom_components.inpost_air.models import ParcelLocker
from custom_components.inpost_air.const import Entities


class AirQualityIndexSensor(SensorEntity):
    """
    Represents a sensor for measuring air quality index.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        parcel_locker: ParcelLocker,
    ) -> None:
        self._attr_device_info = utils.get_device_info(parcel_locker)
        self._attr_icon = "mdi:air-filter"

    @abstractmethod
    async def async_update(self) -> None:
        """
        Update sensor's state
        """

    def get_last_n_hours_data(self, entity_id, n: int):
        """
        Retrieve the last n hours of data for a given entity.
        """
        raw_states = history.state_changes_during_period(
            hass=self.hass,
            start_time=dt_util.utcnow() - timedelta(hours=n),
            end_time=dt_util.utcnow(),
            entity_id=entity_id,
        ).get(entity_id, [])

        return [
            float(item.state) for item in raw_states if utils.can_be_float(item.state)
        ]

    async def get_sensors_data(
        self, sensors: list[tuple[Entities, int]]
    ) -> list[tuple[Entities, list[float]]]:
        """
        Retrieves data from sensors for the specified time period.
        """
        device = device_registry.async_get(self.hass).async_get_device(
            identifiers=self.device_info.get("identifiers")
            if self.device_info is not None
            else None,
            connections=self.device_info.get("connections")
            if self.device_info is not None
            else None,
        )

        if device is None:
            return []

        entities = dict(
            map(
                lambda entity: (
                    ""
                    if entity.translation_key is None
                    else entity.translation_key.upper(),
                    entity,
                ),
                entity_registry.async_entries_for_device(
                    registry=entity_registry.async_get(self.hass), device_id=device.id
                ),
            )
        )
        available_entities = [
            (entities[entity_key], hours)
            for (entity_key, hours) in sensors
            if entity_key in entities
        ]
        values = await recorder.get_instance(self.hass).async_add_executor_job(  # type: ignore
            lambda: [
                (
                    Entities(entity.translation_key.upper()),  # type: ignore
                    self.get_last_n_hours_data(entity.entity_id, hours),
                )
                for (entity, hours) in available_entities
            ]
        )

        return values
