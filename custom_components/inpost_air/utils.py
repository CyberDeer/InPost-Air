from math import asin, cos, radians, sin, sqrt

from homeassistant.helpers.device_registry import DeviceInfo
from slugify import slugify

from custom_components.inpost_air.const import DOMAIN
from custom_components.inpost_air.models import InPostAirPoint, ParcelLocker


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    # Radius of earth in kilometers is 6371
    km = 6371 * c

    return km


def can_be_float(element: str) -> bool:
    """
    Check if the given element can be converted to a float.
    """
    try:
        float(element)
        return True
    except ValueError:
        return False


def get_device_info(parcel_locker: ParcelLocker) -> DeviceInfo:
    """
    Get the device information for a given parcel locker.
    """
    return DeviceInfo(
        identifiers={
            (DOMAIN, parcel_locker.locker_code),
            (DOMAIN, parcel_locker.locker_id),
        },
    )


def get_parcel_locker_url(point: InPostAirPoint) -> str:
    """
    Generates a URL for a parcel locker based on the provided InPostAirPoint.
    """
    pathname = slugify(
        f"paczkomat-{point.g}-{point.n}-{point.e}-paczkomaty-{point.r}",
        lowercase=True,
    )
    return f"https://greencity.pl/{pathname}"
