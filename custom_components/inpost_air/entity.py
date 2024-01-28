"""BlueprintEntity class."""
from __future__ import annotations

from typing import Any, Dict
from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, NAME, VERSION, MANUFACTURER
from .coordinator import InPostAirDataUpdateCoordinator


@dataclass
class InPostAirEntityDescription:
    key: str = None
    name: str = None
    entity_category: str = None

class InPostAirEntity(CoordinatorEntity[InPostAirDataUpdateCoordinator]):
    """InPostAir class."""

    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: InPostAirDataUpdateCoordinator, description: InPostAirEntityDescription = None) -> None:
        """Initialize."""
        super().__init__(coordinator)
        if description:
            self.entity_description = description
        self._attr_unique_id = description.key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN)},
            name=NAME,
            model=VERSION,
            manufacturer=MANUFACTURER,
        )