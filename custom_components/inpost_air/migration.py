"""Migrate and consolidate InPost Air config entries."""

from dataclasses import asdict
import logging
from types import MappingProxyType

from dacite import from_dict
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .api import InPostAirPoint
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _move_registrations(
    hass: HomeAssistant,
    source: ConfigEntry,
    target: ConfigEntry,
    subentry_id: str,
    source_subentry_id: str | None = None,
) -> None:
    """Transfer registrations before removing their old config entry."""
    entity_registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(entity_registry, source.entry_id):
        if entity.config_subentry_id == source_subentry_id:
            entity_registry.async_update_entity(
                entity.entity_id,
                config_entry_id=target.entry_id,
                config_subentry_id=subentry_id,
            )

    device_registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_registry, source.entry_id):
        if source_subentry_id not in device.config_entries_subentries[source.entry_id]:
            continue

        device_registry.async_update_device(
            device.id,
            add_config_entry_id=target.entry_id,
            add_config_subentry_id=subentry_id,
        )
        device_registry.async_update_device(
            device.id,
            remove_config_entry_id=source.entry_id,
            remove_config_subentry_id=source_subentry_id,
        )


async def async_consolidate_entries(hass: HomeAssistant) -> bool:
    """Consolidate stored entries before Home Assistant sets them up."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        return True

    # Do not modify entries from a newer, unsupported configuration version.
    if any(entry.version > 3 for entry in entries):
        return False

    for entry in entries:
        if not await async_migrate_entry(hass, entry):
            return False

    parent = entries[0]

    for source in entries[1:]:
        for subentry in source.subentries.values():
            existing = next(
                (
                    item
                    for item in parent.subentries.values()
                    if item.unique_id == subentry.unique_id
                ),
                None,
            )

            if existing is None:
                hass.config_entries.async_add_subentry(parent, subentry)
                existing = subentry

            _move_registrations(
                hass, source, parent, existing.subentry_id, subentry.subentry_id
            )

        await hass.config_entries.async_remove(source.entry_id)

    hass.config_entries.async_update_entry(parent, unique_id=DOMAIN)

    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug(
        "Migrating %s from version %s", config_entry.title, config_entry.version
    )

    if config_entry.version > 3:
        # This means the user has downgraded from a future version
        return False

    if config_entry.version == 1:
        hass.config_entries.async_update_entry(
            config_entry,
            data={"parcel_locker": from_dict(InPostAirPoint, config_entry.data)},
            version=2,
        )

    if config_entry.version == 2:
        entry_data = config_entry.data["parcel_locker"]
        point = (
            entry_data
            if isinstance(entry_data, InPostAirPoint)
            else from_dict(InPostAirPoint, entry_data)
        )
        subentry = ConfigSubentry(
            data=MappingProxyType({"parcel_locker": asdict(point)}),
            subentry_type="parcel_locker",
            title=f"Parcel locker {point.n}",
            unique_id=point.n,
        )
        hass.config_entries.async_add_subentry(config_entry, subentry)
        _move_registrations(hass, config_entry, config_entry, subentry.subentry_id)
        hass.config_entries.async_update_entry(
            config_entry,
            data={},
            title="InPost Air",
            version=3,
            minor_version=1,
        )

    _LOGGER.debug(
        "Migrating %s to version %s completed", config_entry.title, config_entry.version
    )

    return True
