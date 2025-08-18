"""Tests for config entry migration."""

import pytest
from unittest.mock import Mock, patch
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.inpost_air import async_migrate_entry
from custom_components.inpost_air.const import DOMAIN


@pytest.fixture
def mock_device_registry():
    """Create a mock device registry."""
    return Mock(spec=dr.DeviceRegistry)


@pytest.fixture
def mock_device():
    """Create a mock device."""
    device = Mock()
    device.id = "test_device_id"
    device.identifiers = set()
    device.config_entries = set()
    device.entities = []
    device.area_id = None
    device.name_by_user = None
    device.disabled_by = None
    return device


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.version = 1
    return entry


async def test_migrate_entry_no_migration_needed_version_2(
    hass: HomeAssistant, mock_config_entry, mock_device_registry
):
    """Test migration when entry is already version 2."""
    mock_config_entry.version = 2

    with patch(
        "homeassistant.helpers.device_registry.async_get",
        return_value=mock_device_registry,
    ):
        result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    mock_device_registry.async_update_device.assert_not_called()
    mock_device_registry.async_remove_device.assert_not_called()


async def test_migrate_entry_no_devices(
    hass: HomeAssistant, mock_config_entry, mock_device_registry
):
    """Test migration when no devices exist."""
    mock_device_registry.devices = {}

    with patch(
        "homeassistant.helpers.device_registry.async_get",
        return_value=mock_device_registry,
    ):
        result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.version == 2
    mock_device_registry.async_update_device.assert_not_called()
    mock_device_registry.async_remove_device.assert_not_called()


async def test_migrate_entry_device_not_in_config_entry(
    hass: HomeAssistant, mock_config_entry, mock_device_registry, mock_device
):
    """Test migration skips devices not belonging to this config entry."""
    mock_device.config_entries = {"other_entry_id"}
    mock_device_registry.devices = {"device1": mock_device}

    with patch(
        "homeassistant.helpers.device_registry.async_get",
        return_value=mock_device_registry,
    ):
        result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.version == 2
    mock_device_registry.async_update_device.assert_not_called()
    mock_device_registry.async_remove_device.assert_not_called()


async def test_migrate_entry_device_no_legacy_identifier(
    hass: HomeAssistant, mock_config_entry, mock_device_registry, mock_device
):
    """Test migration skips devices without legacy 3-tuple identifiers."""
    mock_device.config_entries = {mock_config_entry.entry_id}
    mock_device.identifiers = {
        (DOMAIN, "ABC123"),
        (DOMAIN, "123456"),
    }  # Already new format
    mock_device_registry.devices = {"device1": mock_device}

    with patch(
        "homeassistant.helpers.device_registry.async_get",
        return_value=mock_device_registry,
    ):
        result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.version == 2
    mock_device_registry.async_update_device.assert_not_called()
    mock_device_registry.async_remove_device.assert_not_called()


async def test_migrate_entry_device_has_entities_warning(
    hass: HomeAssistant, mock_config_entry, mock_device_registry, mock_device, caplog
):
    """Test migration logs warning and skips devices that still have entities."""
    mock_device.config_entries = {mock_config_entry.entry_id}
    mock_device.identifiers = {(DOMAIN, "ABC123", "123456")}  # Legacy 3-tuple
    mock_device.entities = ["entity1", "entity2"]  # Has entities
    mock_device_registry.devices = {"device1": mock_device}

    with (
        patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ),
        patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=Mock(),
        ),
        patch(
            "homeassistant.helpers.entity_registry.async_entries_for_device",
            return_value=["entity1", "entity2"],  # Mock entities found
        ),
    ):
        result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.version == 2
    assert (
        "Legacy device test_device_id still has entities; skipping cleanup"
        in caplog.text
    )
    mock_device_registry.async_update_device.assert_not_called()
    mock_device_registry.async_remove_device.assert_not_called()
    mock_device_registry.async_remove_device.assert_not_called()


async def test_migrate_entry_remove_orphaned_device(
    hass: HomeAssistant, mock_config_entry, mock_device_registry, mock_device
):
    """Test migration removes orphaned legacy device when no new device exists."""
    mock_device.config_entries = {mock_config_entry.entry_id}
    mock_device.identifiers = {(DOMAIN, "ABC123", "123456")}  # Legacy 3-tuple
    mock_device.entities = []  # No entities
    mock_device_registry.devices = {"device1": mock_device}

    with patch(
        "homeassistant.helpers.device_registry.async_get",
        return_value=mock_device_registry,
    ):
        result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.version == 2
    mock_device_registry.async_remove_device.assert_called_once_with("test_device_id")
    mock_device_registry.async_update_device.assert_not_called()


async def test_migrate_entry_transfer_settings_to_new_device(
    hass: HomeAssistant, mock_config_entry, mock_device_registry
):
    """Test migration transfers settings from old device to new device."""
    # Create old device with legacy identifier and custom settings
    old_device = Mock()
    old_device.id = "old_device_id"
    old_device.config_entries = {mock_config_entry.entry_id}
    old_device.identifiers = {(DOMAIN, "ABC123", "123456")}  # Legacy 3-tuple
    old_device.entities = []
    old_device.area_id = "living_room"
    old_device.name_by_user = "My Custom Name"
    old_device.disabled_by = None

    # Create new device with new identifier format but no custom settings
    new_device = Mock()
    new_device.id = "new_device_id"
    new_device.config_entries = {mock_config_entry.entry_id}
    new_device.identifiers = {
        (DOMAIN, "ABC123"),
        (DOMAIN, "123456"),
    }  # New 2-tuple format
    new_device.area_id = None
    new_device.name_by_user = None
    new_device.disabled_by = None

    mock_device_registry.devices = {"old_device": old_device, "new_device": new_device}

    with patch(
        "homeassistant.helpers.device_registry.async_get",
        return_value=mock_device_registry,
    ):
        result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.version == 2

    # Verify old device is removed
    mock_device_registry.async_remove_device.assert_called_once_with("old_device_id")

    # Verify new device gets updated with old device's settings
    mock_device_registry.async_update_device.assert_called_once_with(
        "new_device_id",
        area_id="living_room",
        name_by_user="My Custom Name",
        disabled_by=None,
    )


async def test_migrate_entry_prefer_old_device_settings(
    hass: HomeAssistant, mock_config_entry, mock_device_registry
):
    """Test migration prefers old device settings over new device when old has values."""
    # Create old device with legacy identifier and custom settings
    old_device = Mock()
    old_device.id = "old_device_id"
    old_device.config_entries = {mock_config_entry.entry_id}
    old_device.identifiers = {(DOMAIN, "ABC123", "123456")}  # Legacy 3-tuple
    old_device.entities = []
    old_device.area_id = "living_room"
    old_device.name_by_user = "Old Custom Name"
    old_device.disabled_by = "user"

    # Create new device with new identifier format and existing settings
    new_device = Mock()
    new_device.id = "new_device_id"
    new_device.config_entries = {mock_config_entry.entry_id}
    new_device.identifiers = {
        (DOMAIN, "ABC123"),
        (DOMAIN, "123456"),
    }  # New 2-tuple format
    new_device.area_id = "kitchen"  # Already has area
    new_device.name_by_user = "New Custom Name"  # Already has name
    new_device.disabled_by = None  # Already has disabled status

    mock_device_registry.devices = {"old_device": old_device, "new_device": new_device}

    with patch(
        "homeassistant.helpers.device_registry.async_get",
        return_value=mock_device_registry,
    ):
        result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.version == 2

    # Verify old device is removed
    mock_device_registry.async_remove_device.assert_called_once_with("old_device_id")

    # Verify new device gets old device's settings (since old device has values)
    mock_device_registry.async_update_device.assert_called_once_with(
        "new_device_id",
        area_id="living_room",  # Takes from old device
        name_by_user="Old Custom Name",  # Takes from old device
        disabled_by="user",  # Takes from old device
    )


async def test_migrate_entry_fallback_to_new_device_settings(
    hass: HomeAssistant, mock_config_entry, mock_device_registry
):
    """Test migration falls back to new device settings when old device has None values."""
    # Create old device with legacy identifier but no custom settings
    old_device = Mock()
    old_device.id = "old_device_id"
    old_device.config_entries = {mock_config_entry.entry_id}
    old_device.identifiers = {(DOMAIN, "ABC123", "123456")}  # Legacy 3-tuple
    old_device.entities = []
    old_device.area_id = None  # No area
    old_device.name_by_user = None  # No custom name
    old_device.disabled_by = None  # Not disabled

    # Create new device with new identifier format and existing settings
    new_device = Mock()
    new_device.id = "new_device_id"
    new_device.config_entries = {mock_config_entry.entry_id}
    new_device.identifiers = {
        (DOMAIN, "ABC123"),
        (DOMAIN, "123456"),
    }  # New 2-tuple format
    new_device.area_id = "kitchen"  # Already has area
    new_device.name_by_user = "New Custom Name"  # Already has name
    new_device.disabled_by = "user"  # Already disabled

    mock_device_registry.devices = {"old_device": old_device, "new_device": new_device}

    with patch(
        "homeassistant.helpers.device_registry.async_get",
        return_value=mock_device_registry,
    ):
        result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.version == 2

    # Verify old device is removed
    mock_device_registry.async_remove_device.assert_called_once_with("old_device_id")

    # Verify new device keeps its existing settings (since old device has None values)
    mock_device_registry.async_update_device.assert_called_once_with(
        "new_device_id",
        area_id="kitchen",  # Falls back to new device
        name_by_user="New Custom Name",  # Falls back to new device
        disabled_by="user",  # Falls back to new device
    )


async def test_migrate_entry_multiple_legacy_devices(
    hass: HomeAssistant, mock_config_entry, mock_device_registry
):
    """Test migration handles multiple legacy devices."""
    # Create first old device
    old_device1 = Mock()
    old_device1.id = "old_device_1"
    old_device1.config_entries = {mock_config_entry.entry_id}
    old_device1.identifiers = {(DOMAIN, "ABC123", "123456")}
    old_device1.entities = []
    old_device1.area_id = "living_room"
    old_device1.name_by_user = None
    old_device1.disabled_by = None

    # Create second old device
    old_device2 = Mock()
    old_device2.id = "old_device_2"
    old_device2.config_entries = {mock_config_entry.entry_id}
    old_device2.identifiers = {(DOMAIN, "XYZ789", "987654")}
    old_device2.entities = []
    old_device2.area_id = None
    old_device2.name_by_user = "Custom Device 2"
    old_device2.disabled_by = "user"

    # Create corresponding new devices
    new_device1 = Mock()
    new_device1.id = "new_device_1"
    new_device1.config_entries = {mock_config_entry.entry_id}
    new_device1.identifiers = {(DOMAIN, "ABC123"), (DOMAIN, "123456")}
    new_device1.area_id = None
    new_device1.name_by_user = None
    new_device1.disabled_by = None

    new_device2 = Mock()
    new_device2.id = "new_device_2"
    new_device2.config_entries = {mock_config_entry.entry_id}
    new_device2.identifiers = {(DOMAIN, "XYZ789"), (DOMAIN, "987654")}
    new_device2.area_id = None
    new_device2.name_by_user = None
    new_device2.disabled_by = None

    mock_device_registry.devices = {
        "old_device_1": old_device1,
        "old_device_2": old_device2,
        "new_device_1": new_device1,
        "new_device_2": new_device2,
    }

    with patch(
        "homeassistant.helpers.device_registry.async_get",
        return_value=mock_device_registry,
    ):
        result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.version == 2

    # Verify both old devices are removed
    assert mock_device_registry.async_remove_device.call_count == 2
    mock_device_registry.async_remove_device.assert_any_call("old_device_1")
    mock_device_registry.async_remove_device.assert_any_call("old_device_2")

    # Verify both new devices are updated
    assert mock_device_registry.async_update_device.call_count == 2
    mock_device_registry.async_update_device.assert_any_call(
        "new_device_1",
        area_id="living_room",  # Takes from old device
        name_by_user=None,  # Old device has None, so None is used
        disabled_by=None,  # Old device has None, so None is used
    )
    mock_device_registry.async_update_device.assert_any_call(
        "new_device_2",
        area_id=None,  # Old device has None, so None is used
        name_by_user="Custom Device 2",  # Takes from old device
        disabled_by="user",  # Takes from old device
    )


async def test_migrate_entry_mixed_identifier_formats(
    hass: HomeAssistant, mock_config_entry, mock_device_registry
):
    """Test migration ignores non-domain and non-3-tuple identifiers."""
    # Create device with mixed identifier formats
    device = Mock()
    device.id = "mixed_device_id"
    device.config_entries = {mock_config_entry.entry_id}
    device.identifiers = {
        (DOMAIN, "ABC123", "123456"),  # Legacy 3-tuple (should be processed)
        (DOMAIN, "XYZ789"),  # New 2-tuple (should be ignored)
        ("other_domain", "test", "value"),  # Different domain (should be ignored)
        ("single_value",),  # Single value (should be ignored)
    }
    device.entities = []
    device.area_id = None
    device.name_by_user = None
    device.disabled_by = None

    mock_device_registry.devices = {"device1": device}

    with patch(
        "homeassistant.helpers.device_registry.async_get",
        return_value=mock_device_registry,
    ):
        result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.version == 2

    # Should remove the device since it has a legacy 3-tuple identifier
    mock_device_registry.async_remove_device.assert_called_once_with("mixed_device_id")


async def test_migrate_entry_invalid_old_identifier_format(
    hass: HomeAssistant, mock_config_entry, mock_device_registry
):
    """Test migration handles edge case where 3-tuple doesn't unpack correctly."""
    # This shouldn't happen in practice, but we test the robustness
    device = Mock()
    device.id = "invalid_device_id"
    device.config_entries = {mock_config_entry.entry_id}
    device.identifiers = {(DOMAIN, "only_two_elements")}  # Not a 3-tuple
    device.entities = []

    mock_device_registry.devices = {"device1": device}

    with patch(
        "homeassistant.helpers.device_registry.async_get",
        return_value=mock_device_registry,
    ):
        result = await async_migrate_entry(hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.version == 2

    # Should not process this device since it doesn't have a 3-tuple
    mock_device_registry.async_remove_device.assert_not_called()
    mock_device_registry.async_update_device.assert_not_called()
