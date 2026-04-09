"""Binary sensor platform for Teknix boiler."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TeknixCoordinator
from .entity import TeknixBoilerEntity
from .protocol import BoilerState


@dataclass(frozen=True, kw_only=True)
class TeknixBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a binary sensor and how to derive its on/off state."""

    is_on_fn: Callable[[BoilerState], bool]
    teknix_description: str = ""
    teknix_warning: str = ""


BINARY_SENSORS: tuple[TeknixBinarySensorDescription, ...] = (
    TeknixBinarySensorDescription(
        key="legionella_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda s: s["LEGIONELLA_CYCLE"] == 1,
        teknix_description=(
            "ON when the boiler is currently running an anti-legionella "
            "sanitation cycle on the DHW tank (raises DHW temperature briefly "
            "to kill bacteria). Only relevant if DHW is connected."
        ),
    ),
    TeknixBinarySensorDescription(
        key="priority_consumer_input",
        device_class=BinarySensorDeviceClass.POWER,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda s: s["SENSOR_PP"] == 0,
        teknix_description=(
            "Physical 'priority consumer' input (INFO field SENSOR_PP). "
            "ON means an external high-load device is drawing current, so "
            "the boiler reduces its own power per parameter P6."
        ),
        teknix_warning=(
            "Signal is inverted at the hardware level — raw value 1 means "
            "'not active', 0 means 'active'. The entity already flips it so "
            "ON/OFF match intuition."
        ),
    ),
    TeknixBinarySensorDescription(
        key="room_thermostat_input",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda s: s["SENSOR_R"] == 0,
        teknix_description=(
            "Physical room thermostat input (INFO field SENSOR_R). "
            "ON means an external dry-contact thermostat is calling for heat."
        ),
        teknix_warning=(
            "Signal is inverted at the hardware level — raw value 1 means "
            "'not active', 0 means 'active'. The entity already flips it."
        ),
    ),
    TeknixBinarySensorDescription(
        key="programmer_heat_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda s: s["STAT_PROG_OUT"] == 1,
        teknix_description=(
            "ON when the boiler's built-in weekly programmer for heating "
            "water temperature is currently active."
        ),
    ),
    TeknixBinarySensorDescription(
        key="programmer_room_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda s: s["STAT_PROG_ROOM"] == 1,
        teknix_description=(
            "ON when the boiler's weekly programmer for room temperature is "
            "currently active."
        ),
    ),
    TeknixBinarySensorDescription(
        key="programmer_gvs_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda s: s["STAT_PROG_GVS"] == 1,
        teknix_description=(
            "ON when the boiler's weekly programmer for DHW is currently "
            "active."
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TeknixCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        TeknixBinarySensor(coordinator, desc) for desc in BINARY_SENSORS
    )


class TeknixBinarySensor(TeknixBoilerEntity, BinarySensorEntity):
    """A Teknix boiler binary sensor."""

    entity_description: TeknixBinarySensorDescription

    def __init__(
        self,
        coordinator: TeknixCoordinator,
        description: TeknixBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        if (state := self.boiler_state) is None:
            return None
        try:
            return self.entity_description.is_on_fn(state)
        except (KeyError, IndexError, TypeError):
            return None
