"""Test locker migration and subentry lifecycle."""

from dataclasses import asdict
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, call, patch

import pytest
from homeassistant.config_entries import ConfigSubentry
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.inpost_air import (
    async_setup,
    async_setup_entry,
    async_migrate_entry,
    config_flow,
)
from custom_components.inpost_air.api import (
    AirSensorReading,
    AirSensorWindow,
    InPostAirApiClientError,
    InPostApi,
    NearbyLocker,
    ParcelLockerAirDataResponse,
)
from custom_components.inpost_air.const import DOMAIN
from custom_components.inpost_air.migration import _move_registrations
from custom_components.inpost_air.models import StoredLockerPoint
from tests.test_config_flow import mocked_lockers_list


def _air_response() -> ParcelLockerAirDataResponse:
    """Minimal air data payload as returned by the public points API."""
    return ParcelLockerAirDataResponse(
        current=AirSensorWindow(
            fromDateTime="2026-11-12T05:13:57.071Z",
            tillDateTime="2026-11-12T06:28:57.071Z",
            values=[AirSensorReading("TEMPERATURE", 7.0)],
        )
    )


async def test_setup_keeps_unavailable_locker(hass):
    """A failing locker must not prevent the entry from loading.

    The entry always loads for every configured locker; the failing one
    recovers on its own once a later coordinator refresh succeeds.
    """
    entry, _, _ = legacy_entry(hass, "AAA")
    legacy_entry(hass, "BBB")

    assert await async_setup(hass, {})

    def air_data(locker_code: str) -> ParcelLockerAirDataResponse:
        if locker_code == "BBB":
            raise InPostAirApiClientError("HTTP 500")
        return _air_response()

    with (
        patch.object(InPostApi, "get_parcel_locker_air_data", side_effect=air_data),
        patch("custom_components.inpost_air.coordinator.MAX_ATTEMPTS", 1),
        patch.object(hass.config_entries, "async_forward_entry_setups") as forward,
    ):
        assert await async_setup_entry(hass, entry)

    forward.assert_awaited_once()

    assert {data.parcel_locker.locker_code for data in entry.runtime_data.values()} == {
        "AAA",
        "BBB",
    }
    assert len(entry.subentries) == 2

    coordinators = {
        data.parcel_locker.locker_code: data.coordinator
        for data in entry.runtime_data.values()
    }
    assert coordinators["AAA"].last_update_success
    assert coordinators["AAA"].data is not None
    assert not coordinators["BBB"].last_update_success


@pytest.mark.parametrize("source_subentry_id", [None, "old-subentry"])
def test_move_registrations_legacy_device_registry(hass, source_subentry_id):
    """Keep the migration API supported by Home Assistant 2025.12.4."""
    source = SimpleNamespace(entry_id="source")
    target = SimpleNamespace(entry_id="target")
    device = SimpleNamespace(
        id="device", config_entries_subentries={"source": {source_subentry_id}}
    )
    unrelated = SimpleNamespace(
        id="unrelated", config_entries_subentries={"source": {"other-subentry"}}
    )
    registry = Mock()
    with (
        patch.object(dr, "async_get", return_value=registry),
        patch.object(
            dr, "async_entries_for_config_entry", return_value=[device, unrelated]
        ),
        patch.object(er, "async_entries_for_config_entry", return_value=[]),
    ):
        _move_registrations(hass, source, target, "new-subentry", source_subentry_id)
    assert registry.async_update_device.call_args_list == [
        call(
            "device",
            add_config_entry_id="target",
            add_config_subentry_id="new-subentry",
        ),
        call(
            "device",
            remove_config_entry_id="source",
            remove_config_subentry_id=source_subentry_id,
        ),
    ]


def legacy_entry(hass, code, version=2):
    data = asdict(mocked_lockers_list[0]) | {"n": code}
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Parcel locker {code}",
        unique_id=code,
        version=version,
        data=data if version == 1 else {"parcel_locker": data},
    )
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, code)},
        name=f"Custom {code}",
    )
    entity = er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{code}_temperature",
        config_entry=entry,
        device_id=device.id,
        suggested_object_id=f"{code}_temperature",
    )
    er.async_get(hass).async_update_entity(entity.entity_id, name=f"Custom {code}")
    return entry, device, entity


@pytest.mark.parametrize("version", [1, 2])
async def test_consolidation(hass, version):
    first, device1, entity1 = legacy_entry(hass, "AAA", version)
    second, device2, entity2 = legacy_entry(hass, "BBB")
    assert await async_setup(hass, {})
    assert hass.config_entries.async_entries(DOMAIN) == [first]
    assert first.version == 3
    assert first.minor_version == 3
    assert first.data == {}
    assert first.title == "InPost Air"
    assert first.unique_id == DOMAIN
    assert {sub.unique_id for sub in first.subentries.values()} == {"AAA", "BBB"}
    for code, device, entity in [("AAA", device1, entity1), ("BBB", device2, entity2)]:
        sub = next(sub for sub in first.subentries.values() if sub.unique_id == code)
        assert set(sub.data["parcel_locker"]) == {"code", "city", "street", "province"}
        updated_device = dr.async_get(hass).async_get(device.id)
        # HA reports deprecated property access outside an integration as an
        # error. Keep this assertion on the API supported by older HA versions.
        with patch.object(
            dr, "_report_deprecated_config_entries_property", create=True
        ):
            assert updated_device.config_entries_subentries == {
                first.entry_id: {sub.subentry_id}
            }
        updated_entity = er.async_get(hass).async_get(entity.entity_id)
        assert updated_entity.config_entry_id == first.entry_id
        assert updated_entity.config_subentry_id == sub.subentry_id
        assert updated_entity.name == f"Custom {code}"
    assert hass.config_entries.async_get_entry(second.entry_id) is None
    assert await async_setup(hass, {})
    assert len(first.subentries) == 2
    removed = next(sub for sub in first.subentries.values() if sub.unique_id == "BBB")
    hass.config_entries.async_remove_subentry(first, removed.subentry_id)
    assert er.async_get(hass).async_get(entity2.entity_id) is None
    assert er.async_get(hass).async_get(entity1.entity_id) is not None


async def test_future_version(hass):
    entry = MockConfigEntry(domain=DOMAIN, version=4, data={})
    entry.add_to_hass(hass)
    assert not await async_migrate_entry(hass, entry)
    assert not await async_setup(hass, {})
    assert entry.version == 4


@pytest.mark.parametrize("minor_version", [1, 2])
async def test_existing_subentry_data_is_trimmed(hass, minor_version):
    """Migrate stored metadata without replacing the subentry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        minor_version=minor_version,
        title="InPost Air",
        data={},
    )
    entry.add_to_hass(hass)
    data = asdict(mocked_lockers_list[0]) | {"unused": "old value"}
    subentry = ConfigSubentry(
        data=MappingProxyType({"parcel_locker": data}),
        subentry_type="parcel_locker",
        title="Parcel locker AJE01BAPP",
        unique_id="AJE01BAPP",
    )
    hass.config_entries.async_add_subentry(entry, subentry)

    assert await async_migrate_entry(hass, entry)
    migrated = entry.subentries[subentry.subentry_id]
    assert migrated.unique_id == subentry.unique_id
    assert migrated.data["parcel_locker"] == {
        "code": "AJE01BAPP",
        "city": "andrzejewo",
        "street": "Warszawska",
        "province": "mazowieckie",
    }
    assert entry.minor_version == 3


async def test_subentry_flow(hass):
    entry = MockConfigEntry(domain=DOMAIN, version=3, title="InPost Air", data={})
    entry.add_to_hass(hass)
    with (
        patch.object(
            InPostApi,
            "get_parcel_lockers_list",
            return_value=[NearbyLocker("AJE01BAPP", 1000, "Market Dino")],
        ),
        patch(
            "custom_components.inpost_air.config_flow.validate_input",
            return_value=StoredLockerPoint(
                "AJE01BAPP", "andrzejewo", "Warszawska", "mazowieckie"
            ),
        ),
    ):
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, "parcel_locker"), context={"source": "user"}
        )
        assert result["type"] == "form"
        result = await hass.config_entries.subentries.async_configure(
            result["flow_id"], {"parcelLockerId": "aje01bapp"}
        )
        assert result["type"] == "create_entry"
        sub = next(iter(entry.subentries.values()))
        assert sub.unique_id == "AJE01BAPP"
        assert sub.data["parcel_locker"] == {
            "code": "AJE01BAPP",
            "city": "andrzejewo",
            "street": "Warszawska",
            "province": "mazowieckie",
        }
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, "parcel_locker"),
            context={"source": "user"},
            data={"parcelLockerId": "AJE01BAPP"},
        )
        assert result["reason"] == "already_configured"


async def test_startup_consolidates_before_entry_setup(hass):
    """Exercise the real integration startup order."""

    first, _, entity1 = legacy_entry(hass, "AAA")
    legacy_entry(hass, "BBB")
    with patch(
        "custom_components.inpost_air.async_setup_entry",
        new=AsyncMock(return_value=True),
    ) as setup:
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()
        setup.assert_awaited_once_with(hass, first)
        assert len(first.subentries) == 2
        assert er.async_get(hass).async_get(entity1.entity_id) is not None


@pytest.mark.parametrize(
    "error,expected",
    [
        ("UnknownParcelLocker", "unknown_parcel_locker"),
        ("ParcelLockerWithoutAirData", "parcel_locker_no_data"),
        ("CannotConnect", "cannot_connect"),
    ],
)
async def test_subentry_validation_errors(hass, error, expected):
    entry = MockConfigEntry(domain=DOMAIN, version=3, title="InPost Air", data={})
    entry.add_to_hass(hass)
    with (
        patch.object(
            InPostApi,
            "get_parcel_lockers_list",
            return_value=[NearbyLocker("AJE01BAPP", 1000, "Market Dino")],
        ),
        patch(
            "custom_components.inpost_air.config_flow.validate_input",
            side_effect=getattr(config_flow, error),
        ),
    ):
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, "parcel_locker"),
            context={"source": "user"},
            data={"parcelLockerId": "AAA"},
        )
        assert result["type"] == "form"
        assert result["errors"] == {"base": expected}
        assert not entry.subentries
