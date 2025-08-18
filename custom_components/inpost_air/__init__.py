"""The InPost Air integration."""

from __future__ import annotations
from dataclasses import dataclass
import logging

from dacite import from_dict
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.inpost_air.coordinator import InPostAirDataCoordinator
from custom_components.inpost_air.models import ParcelLocker
from custom_components.inpost_air.utils import get_device_info, get_parcel_locker_url
from custom_components.inpost_air.const import DOMAIN

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


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove legacy 3-tuple devices left by ≤ 1.4.x."""
    if entry.version == 1:  # 1.5.0 → 1.5.1
        dev_reg = dr.async_get(hass)
        ent_reg = er.async_get(hass)

        for device in list(dev_reg.devices.values()):
            if entry.entry_id not in device.config_entries:
                continue

            # Detect an old device with a single 3-element identifier
            old_id = next(
                (i for i in device.identifiers if len(i) == 3 and i[0] == DOMAIN),
                None,
            )
            if not old_id:
                continue

            # Skip if it still has entities (unexpected edge-case)
            device_entities = er.async_entries_for_device(
                registry=ent_reg, device_id=device.id
            )
            if device_entities:
                _LOGGER.warning(
                    "Legacy device %s still has entities; skipping cleanup", device.id
                )
                continue

            # Optionally carry over area/name/disabled flags to the new device
            _, code, _ = old_id
            new_dev = next(
                (
                    d
                    for d in dev_reg.devices.values()
                    if (DOMAIN, code) in d.identifiers
                    and entry.entry_id in d.config_entries
                    and d.id != device.id
                ),
                None,
            )
            if new_dev:
                # Convert string disabled_by to enum if needed
                old_disabled_by = device.disabled_by
                if isinstance(old_disabled_by, str):
                    old_disabled_by = dr.DeviceEntryDisabler(old_disabled_by)

                new_disabled_by = new_dev.disabled_by
                if isinstance(new_disabled_by, str):
                    new_disabled_by = dr.DeviceEntryDisabler(new_disabled_by)

                dev_reg.async_update_device(
                    new_dev.id,
                    area_id=device.area_id or new_dev.area_id,
                    name_by_user=device.name_by_user or new_dev.name_by_user,
                    disabled_by=old_disabled_by or new_disabled_by,
                )

            # Remove the orphaned 3-tuple device
            dev_reg.async_remove_device(device.id)

        entry.version = 2  # mark migration complete
    return True
