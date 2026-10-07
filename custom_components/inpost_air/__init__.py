"""The InPost Air integration."""

from __future__ import annotations
from dataclasses import dataclass

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
from . import migration


@dataclass
class InPostAirData:
    """
    Represents data related to InPost Air service.
    """

    parcel_locker: ParcelLocker
    coordinator: InPostAirDataCoordinator


type InPostAirConfiEntry = ConfigEntry[dict[str, InPostAirData]]

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: InPostAirConfiEntry) -> bool:
    """Set up InPost Air from a config entry."""
    api_client = InPostApi(hass)
    entry.runtime_data = {}
    device_registry = dr.async_get(hass)

    for subentry_id, subentry in entry.subentries.items():
        point = from_dict(InPostAirPoint, dict(subentry.data["parcel_locker"]))
        parcel_locker_id = await api_client.find_parcel_locker_id(point)

        if parcel_locker_id is None:
            return False

        parcel_locker = ParcelLocker(point.n, parcel_locker_id)
        coordinator = InPostAirDataCoordinator(hass, api_client, parcel_locker)

        try:
            await coordinator.async_config_entry_first_refresh()
        except ConfigEntryNotReady as ex:
            if "Air sensors are not available" in str(ex):
                raise ConfigEntryError(ex)
            raise ex

        entry.runtime_data[subentry_id] = InPostAirData(parcel_locker, coordinator)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            config_subentry_id=subentry_id,
            identifiers=get_device_info(parcel_locker).get("identifiers"),
            name=f"Parcel locker {parcel_locker.locker_code}",
            manufacturer="InPost",
            configuration_url=get_parcel_locker_url(point),
            entry_type=dr.DeviceEntryType.SERVICE,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass: HomeAssistant, entry: InPostAirConfiEntry) -> None:
    """Reload when parcel lockers are added or removed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: InPostAirConfiEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Consolidate stored entries before Home Assistant sets them up."""
    return await migration.async_consolidate_entries(hass)


async def async_migrate_entry(hass: HomeAssistant, config_entry: InPostAirConfiEntry):
    """Migrate old entry."""
    return await migration.async_migrate_entry(hass, config_entry)
