"""The InPost Air integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import InPostApi, ParcelLocker
from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up InPost Air from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    parcel_locker_id = await InPostApi(hass).find_parcel_locker_id(entry.data)
    parcel_locker = ParcelLocker(entry.data["n"], parcel_locker_id)
    hass.data[DOMAIN][entry.entry_id] = parcel_locker

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
