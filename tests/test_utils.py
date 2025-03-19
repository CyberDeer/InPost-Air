"""Utils tests."""

from unittest.mock import Mock
from custom_components.inpost_air.api import ParcelLocker
from custom_components.inpost_air.const import DOMAIN
from custom_components.inpost_air.utils import can_be_float, get_device_info, haversine
from homeassistant.helpers.device_registry import DeviceInfo


def test_haversine():
    """Test haversine function."""

    # Test case 1: Same point
    assert haversine(0, 0, 0, 0) == 0

    # Test case 2: Known distance
    # Distance between New York (40.7128° N, 74.0060° W) and London (51.5074° N, 0.1278° W)
    ny_lon, ny_lat = -74.0060, 40.7128
    lon_lon, lon_lat = -0.1278, 51.5074
    expected_distance = 5570  # Approximate distance in kilometers
    assert round(haversine(ny_lon, ny_lat, lon_lon, lon_lat)) == expected_distance

    # Test case 3: Known distance
    # Distance between Paris (48.8566° N, 2.3522° E) and Berlin (52.5200° N, 13.4050° E)
    paris_lon, paris_lat = 2.3522, 48.8566
    berlin_lon, berlin_lat = 13.4050, 52.5200
    expected_distance = 877  # Approximate distance in kilometers
    assert (
        round(haversine(paris_lon, paris_lat, berlin_lon, berlin_lat))
        == expected_distance
    )


def test_can_be_float():
    """Test can_be_float function."""

    # Test case 1: Valid float string
    assert can_be_float("123.456") is True

    # Test case 2: Valid integer string
    assert can_be_float("789") is True

    # Test case 3: Invalid string
    assert can_be_float("abc") is False

    # Test case 4: Empty string
    assert can_be_float("") is False

    # Test case 5: String with spaces
    assert can_be_float(" 123.456 ") is True

    # Test case 6: String with special characters
    assert can_be_float("123.45.67") is False

    # Test case 7: String with negative number
    assert can_be_float("-123.456") is True


def test_get_device_info():
    """Test get_device_info function."""

    # Create a mock ParcelLocker object
    mock_parcel_locker = Mock(spec=ParcelLocker)
    mock_parcel_locker.locker_code = "ABC123"
    mock_parcel_locker.locker_id = "123456"

    # Expected DeviceInfo
    expected_device_info = DeviceInfo(
        identifiers={
            (DOMAIN, "ABC123"),
            (DOMAIN, "123456"),
        },
        name="Parcel locker ABC123",
        manufacturer="InPost",
    )

    # Test case: Check if the returned DeviceInfo matches the expected DeviceInfo
    assert get_device_info(mock_parcel_locker) == expected_device_info
