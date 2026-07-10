"""Integration tests for migration functionality."""

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.inpost_air import async_migrate_entry
from custom_components.inpost_air.const import DOMAIN


@pytest.mark.asyncio
async def test_migration_integration_end_to_end(hass: HomeAssistant):
    """Test the complete migration process with real device registry."""

    # Create a real device registry
    dev_reg = dr.async_get(hass)

    # Create a mock config entry and add it to the config entry registry
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Entry",
        data={},
        options={},
        source="user",
        entry_id="test_entry_id",
        unique_id=None,
    )

    # Add the config entry to Home Assistant's registry
    hass.config_entries._entries[entry.entry_id] = entry

    # Create a legacy device with 3-tuple identifier
    old_device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "ABC123", "legacy_id")},  # Legacy 3-tuple
        manufacturer="InPost",
        name="Legacy Device",
    )

    # Set some custom properties on the old device
    dev_reg.async_update_device(
        old_device.id,
        area_id="living_room",
        name_by_user="My Custom Locker",
        disabled_by=dr.DeviceEntryDisabler.USER,
    )

    # Create a new device with 2-tuple identifiers
    new_device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "ABC123"), (DOMAIN, "new_id")},  # New 2-tuple format
        manufacturer="InPost",
        name="New Device",
    )

    # Verify initial state
    assert len(dev_reg.devices) == 2
    old_device_fresh = dev_reg.async_get(old_device.id)
    assert old_device_fresh.area_id == "living_room"
    assert old_device_fresh.name_by_user == "My Custom Locker"
    assert old_device_fresh.disabled_by == "user"

    # Run migration
    result = await async_migrate_entry(hass, entry)
    assert result is True
    assert entry.version == 2

    # Verify migration results
    remaining_devices = dev_reg.devices
    assert len(remaining_devices) == 1  # Old device should be removed

    # Verify old device is gone
    assert dev_reg.async_get(old_device.id) is None

    # Verify new device still exists and has inherited settings
    new_device_after = dev_reg.async_get(new_device.id)
    assert new_device_after is not None
    assert new_device_after.area_id == "living_room"  # Inherited from old device
    assert (
        new_device_after.name_by_user == "My Custom Locker"
    )  # Inherited from old device
    assert new_device_after.disabled_by == "user"  # Inherited from old device


@pytest.mark.asyncio
async def test_migration_no_new_device_removes_old(hass: HomeAssistant):
    """Test migration removes orphaned old device when no corresponding new device exists."""

    # Create a real device registry
    dev_reg = dr.async_get(hass)

    # Create a mock config entry and add it to the config entry registry
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Entry",
        data={},
        options={},
        source="user",
        entry_id="test_entry_id",
        unique_id=None,
    )

    # Add the config entry to Home Assistant's registry
    hass.config_entries._entries[entry.entry_id] = entry

    # Create only a legacy device with 3-tuple identifier (no corresponding new device)
    old_device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "ORPHAN123", "legacy_id")},  # Legacy 3-tuple
        manufacturer="InPost",
        name="Orphaned Device",
    )

    # Verify initial state
    assert len(dev_reg.devices) == 1

    # Run migration
    result = await async_migrate_entry(hass, entry)
    assert result is True
    assert entry.version == 2

    # Verify old device is removed
    assert len(dev_reg.devices) == 0
    assert dev_reg.async_get(old_device.id) is None


@pytest.mark.asyncio
async def test_migration_idempotent(hass: HomeAssistant):
    """Test that migration can be run multiple times safely."""

    # Create a real device registry
    dev_reg = dr.async_get(hass)

    # Create a mock config entry and add it to the config entry registry
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Entry",
        data={},
        options={},
        source="user",
        entry_id="test_entry_id",
        unique_id=None,
    )

    # Add the config entry to Home Assistant's registry
    hass.config_entries._entries[entry.entry_id] = entry

    # Create only a new device (no legacy devices)
    new_device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "ABC123"), (DOMAIN, "new_id")},  # New 2-tuple format
        manufacturer="InPost",
        name="New Device",
    )

    # Run migration first time
    result1 = await async_migrate_entry(hass, entry)
    assert result1 is True
    assert entry.version == 2

    # Verify device still exists
    assert len(dev_reg.devices) == 1
    assert dev_reg.async_get(new_device.id) is not None

    # Run migration second time (should be safe)
    result2 = await async_migrate_entry(hass, entry)
    assert result2 is True
    assert entry.version == 2

    # Verify device still exists and nothing changed
    assert len(dev_reg.devices) == 1
    assert dev_reg.async_get(new_device.id) is not None
