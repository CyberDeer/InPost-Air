"""The InPost Air integration."""

from __future__ import annotations
from dataclasses import dataclass
import logging

from dacite import from_dict
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from custom_components.inpost_air.coordinator import InPostAirDataCoordinator
from custom_components.inpost_air.models import ParcelLocker
from custom_components.inpost_air.utils import get_device_info, get_parcel_locker_url

from .api import InPostAirApiClientError, InPostAirPoint, InPostApi
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
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: InPostAirConfiEntry) -> bool:
    """Set up InPost Air from a config entry."""
    api_client = InPostApi(hass)
    entry.runtime_data = {}
    device_registry = dr.async_get(hass)

    for subentry_id, subentry in entry.subentries.items():
        point = from_dict(InPostAirPoint, dict(subentry.data["parcel_locker"]))
        try:
            parcel_locker_id = await api_client.find_parcel_locker_id(point)
            if parcel_locker_id is None:
                raise InPostAirApiClientError("Parcel locker page has no air sensor ID")

            parcel_locker = ParcelLocker(point.n, parcel_locker_id)
            coordinator = InPostAirDataCoordinator(hass, api_client, parcel_locker)
            await coordinator.async_config_entry_first_refresh()
        except (InPostAirApiClientError, ConfigEntryNotReady) as ex:
            _LOGGER.warning("Skipping unavailable parcel locker %s: %s", point.n, ex)
            continue

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

    if entry.subentries and not entry.runtime_data:
        raise ConfigEntryNotReady("No configured parcel lockers are available")

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
