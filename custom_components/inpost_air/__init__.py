"""The InPost Air integration."""

from __future__ import annotations
from dataclasses import dataclass

from dacite import from_dict
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr

from custom_components.inpost_air.coordinator import InPostAirDataCoordinator
from custom_components.inpost_air.models import ParcelLocker, StoredLockerPoint
from custom_components.inpost_air.utils import (
    get_device_identifiers,
    get_parcel_locker_url,
)

from .api import InPostApi
from .const import DOMAIN
from . import migration

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


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
        point = from_dict(StoredLockerPoint, dict(subentry.data["parcel_locker"]))
        parcel_locker = ParcelLocker(point.code)
        coordinator = InPostAirDataCoordinator(hass, api_client, parcel_locker)

        entry.runtime_data[subentry_id] = InPostAirData(parcel_locker, coordinator)
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            config_subentry_id=subentry_id,
            identifiers=get_device_identifiers(parcel_locker),
            name=f"Parcel locker {parcel_locker.locker_code}",
            manufacturer="InPost",
            configuration_url=get_parcel_locker_url(point),
            entry_type=dr.DeviceEntryType.SERVICE,
        )

        await coordinator.async_refresh()

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
