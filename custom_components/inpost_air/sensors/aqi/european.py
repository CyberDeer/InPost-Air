from enum import IntEnum, auto
import statistics
from custom_components.inpost_air.api import ParcelLocker
from custom_components.inpost_air.const import Entities
from custom_components.inpost_air.sensors.air_quality_index import AirQualityIndexSensor


class EuropeanAirQualityIndexCategory(IntEnum):
    """
    Enumeration representing the categories of the European Air Quality Index (EAQI).
    """

    GOOD = auto()
    FAIR = auto()
    MODERATE = auto()
    POOR = auto()
    VERY_POOR = auto()
    EXTREMELY_POOR = auto()


class EuropeanAirQualityIndexSensor(AirQualityIndexSensor):
    """
    Represents a sensor for calculating the European Air Quality Index.
    """

    def __init__(self, parcel_locker: ParcelLocker) -> None:
        super().__init__(parcel_locker)
        self._attr_name = "European Air Quality Index"
        self._attr_unique_id = f"{parcel_locker.locker_code}_eaqi"

    def calculate_sub_index(self, sensor_data: tuple[Entities, float | None]):
        """
        Calculates the sub-index for a given air quality parameter value. Based on: https://www.eea.europa.eu/themes/air/air-quality-index
        """
        match sensor_data:
            case (_, None):
                return None
            case (Entities.PM10, value):
                if value <= 20:
                    return EuropeanAirQualityIndexCategory.GOOD
                if value <= 40:
                    return EuropeanAirQualityIndexCategory.FAIR
                if value <= 50:
                    return EuropeanAirQualityIndexCategory.MODERATE
                if value <= 100:
                    return EuropeanAirQualityIndexCategory.POOR
                if value <= 150:
                    return EuropeanAirQualityIndexCategory.VERY_POOR
                if value > 150:
                    return EuropeanAirQualityIndexCategory.EXTREMELY_POOR
            case (Entities.PM2_5, value):
                if value <= 10:
                    return EuropeanAirQualityIndexCategory.GOOD
                if value <= 20:
                    return EuropeanAirQualityIndexCategory.FAIR
                if value <= 25:
                    return EuropeanAirQualityIndexCategory.MODERATE
                if value <= 50:
                    return EuropeanAirQualityIndexCategory.POOR
                if value <= 75:
                    return EuropeanAirQualityIndexCategory.VERY_POOR
                if value > 75:
                    return EuropeanAirQualityIndexCategory.EXTREMELY_POOR
            case (Entities.O3, value):
                if value <= 50:
                    return EuropeanAirQualityIndexCategory.GOOD
                if value <= 100:
                    return EuropeanAirQualityIndexCategory.FAIR
                if value <= 130:
                    return EuropeanAirQualityIndexCategory.MODERATE
                if value <= 240:
                    return EuropeanAirQualityIndexCategory.POOR
                if value <= 380:
                    return EuropeanAirQualityIndexCategory.VERY_POOR
                if value > 380:
                    return EuropeanAirQualityIndexCategory.EXTREMELY_POOR
            case (Entities.NO2, value):
                if value <= 40:
                    return EuropeanAirQualityIndexCategory.GOOD
                if value <= 90:
                    return EuropeanAirQualityIndexCategory.FAIR
                if value <= 120:
                    return EuropeanAirQualityIndexCategory.MODERATE
                if value <= 230:
                    return EuropeanAirQualityIndexCategory.POOR
                if value <= 340:
                    return EuropeanAirQualityIndexCategory.VERY_POOR
                if value > 340:
                    return EuropeanAirQualityIndexCategory.EXTREMELY_POOR

    async def async_update(self) -> None:
        sensors_data = await self.get_sensors_data(
            [
                (Entities.PM2_5, 24),
                (Entities.PM10, 24),
                (Entities.NO2, 1),
                (Entities.O3, 1),
            ]
        )
        mean_data = [
            (entity, statistics.fmean(x)) for (entity, x) in sensors_data if len(x) > 0
        ]
        sub_indexes = list(
            filter(
                lambda item: item is not None,
                map(self.calculate_sub_index, mean_data),
            )
        )

        self._attr_native_value = (
            EuropeanAirQualityIndexCategory(max(sub_indexes)).name
            if len(sub_indexes) > 0
            else None
        )
