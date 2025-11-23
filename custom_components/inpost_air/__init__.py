"""The InPost Air integration."""

from __future__ import annotations
from dataclasses import dataclass
import logging

from dacite import from_dict
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, ConfigEntryError
from homeassistant.helpers import device_registry as dr

from custom_components.inpost_air.coordinator import InPostAirDataCoordinator
from custom_components.inpost_air.models import ParcelLocker
from custom_components.inpost_air.utils import get_device_info, get_parcel_locker_url

from .api import InPostAirPoint, InPostApi

_LOGGER = logging.getLogger(__name__)


@dataclass
class InPostAirData:
    """
    Represents data related to InPost Air service.
    """

    parcel_locker: ParcelLocker
    coordinator: InPostAirDataCoordinator


type InPostAirConfiEntry = ConfigEntry[InPostAirData]

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: InPostAirConfiEntry) -> bool:
    """Set up InPost Air from a config entry."""
    api_client = InPostApi(hass)
    entry_data = entry.data.get("parcel_locker")

    if (
        point := None
        if entry_data is None
        else entry_data
        if isinstance(entry_data, InPostAirPoint)
        else from_dict(InPostAirPoint, entry_data)
    ) is None:
        return False

    if (parcel_locker_id := await api_client.find_parcel_locker_id(point)) is None:
        return False

    parcel_locker = ParcelLocker(point.n, parcel_locker_id)
    coordinator = InPostAirDataCoordinator(hass, api_client, parcel_locker)

    entry.runtime_data = InPostAirData(parcel_locker, coordinator)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady as ex:
        if "Air sensors are not available" in str(ex):
            raise ConfigEntryError(ex)
        raise ex

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers=get_device_info(parcel_locker).get("identifiers"),
        name=f"Parcel locker {parcel_locker.locker_code}",
        manufacturer="InPost",
        configuration_url=get_parcel_locker_url(point),
        entry_type=dr.DeviceEntryType.SERVICE,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: InPostAirConfiEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, config_entry: InPostAirConfiEntry):
    """Migrate old entry."""
    _LOGGER.debug(
        "Migrating %s from version %s", config_entry.title, config_entry.version
    )

    if config_entry.version > 2:
        # This means the user has downgraded from a future version
        return False

    if config_entry.version == 1:
        hass.config_entries.async_update_entry(
            config_entry,
            data={"parcel_locker": from_dict(InPostAirPoint, config_entry.data)},
            version=2,
        )

    _LOGGER.debug(
        "Migrating %s to version %s completed", config_entry.title, config_entry.version
    )

    return True
