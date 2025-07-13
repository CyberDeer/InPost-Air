import statistics
from enum import IntEnum, auto

from custom_components.inpost_air.models import ParcelLocker
from custom_components.inpost_air.const import Entities
from custom_components.inpost_air.sensors.air_quality_index import AirQualityIndexSensor


class PolishAirQualityIndexCategory(IntEnum):
    """
    Enumeration representing the categories of the Polish Air Quality Index (PAQI).
    """

    VERY_GOOD = auto()
    GOOD = auto()
    MODERATE = auto()
    SUFFICIENT = auto()
    BAD = auto()
    VERY_BAD = auto()


class PolishAirQualityIndexSensor(AirQualityIndexSensor):
    """
    Represents a sensor for calculating the Polish Air Quality Index.
    """

    def __init__(self, parcel_locker: ParcelLocker) -> None:
        super().__init__(parcel_locker)
        self._attr_name = "Polish Air Quality Index"
        self._attr_unique_id = f"{parcel_locker.locker_code}_paqi"

    def calculate_sub_index(self, sensor_data: tuple[Entities, float | None]):
        """
        Calculates the sub-index for a given air quality parameter value. Based on: https://powietrze.gios.gov.pl/pjp/content/health_informations
        """
        match sensor_data:
            case (_, None):
                return None
            case (Entities.PM10, value):
                if value <= 20:
                    return PolishAirQualityIndexCategory.VERY_GOOD
                if value <= 50:
                    return PolishAirQualityIndexCategory.GOOD
                if value <= 80:
                    return PolishAirQualityIndexCategory.MODERATE
                if value <= 110:
                    return PolishAirQualityIndexCategory.SUFFICIENT
                if value <= 150:
                    return PolishAirQualityIndexCategory.BAD
                if value > 150:
                    return PolishAirQualityIndexCategory.VERY_BAD
            case (Entities.PM2_5, value):
                if value <= 13:
                    return PolishAirQualityIndexCategory.VERY_GOOD
                if value <= 35:
                    return PolishAirQualityIndexCategory.GOOD
                if value <= 55:
                    return PolishAirQualityIndexCategory.MODERATE
                if value <= 75:
                    return PolishAirQualityIndexCategory.SUFFICIENT
                if value <= 110:
                    return PolishAirQualityIndexCategory.BAD
                if value > 110:
                    return PolishAirQualityIndexCategory.VERY_BAD
            case (Entities.O3, value):
                if value <= 70:
                    return PolishAirQualityIndexCategory.VERY_GOOD
                if value <= 120:
                    return PolishAirQualityIndexCategory.GOOD
                if value <= 150:
                    return PolishAirQualityIndexCategory.MODERATE
                if value <= 180:
                    return PolishAirQualityIndexCategory.SUFFICIENT
                if value <= 240:
                    return PolishAirQualityIndexCategory.BAD
                if value > 240:
                    return PolishAirQualityIndexCategory.VERY_BAD
            case (Entities.NO2, value):
                if value <= 40:
                    return PolishAirQualityIndexCategory.VERY_GOOD
                if value <= 100:
                    return PolishAirQualityIndexCategory.GOOD
                if value <= 150:
                    return PolishAirQualityIndexCategory.MODERATE
                if value <= 230:
                    return PolishAirQualityIndexCategory.SUFFICIENT
                if value <= 400:
                    return PolishAirQualityIndexCategory.BAD
                if value > 400:
                    return PolishAirQualityIndexCategory.VERY_BAD

    async def async_update(self) -> None:
        sensors_data = await self.get_sensors_data(
            [
                (Entities.PM2_5, 1),
                (Entities.PM10, 1),
                (Entities.NO2, 1),
                (Entities.O3, 1),
            ]
        )
        mean_data = [
            (entity, statistics.fmean(x)) for (entity, x) in sensors_data if len(x) > 0
        ]
        sub_indices = [
            sub_index
            for sub_index in map(self.calculate_sub_index, mean_data)
            if sub_index is not None
        ]

        self._attr_native_value = (
            PolishAirQualityIndexCategory(max(sub_indices)).name
            if len(sub_indices) > 0
            else None
        )
