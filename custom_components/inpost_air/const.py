"""Constants for the InPost Air integration."""

from enum import StrEnum

DOMAIN = "inpost_air"
CONF_PARCEL_LOCKER_ID = "parcelLockerId"


class Entities(StrEnum):
    """Available sensor entities."""

    Temperature = "TEMPERATURE"
    PM2_5 = "PM25"
    PM2_5_Norm = "PM25_NORM"
    Pressure = "PRESSURE"
    PM1 = "PM1"
    PM10 = "PM10"
    PM10_Norm = "PM10_NORM"
    Humidity = "HUMIDITY"
    PM4 = "PM4"
    NO2 = "NO2"
    O3 = "O3"
