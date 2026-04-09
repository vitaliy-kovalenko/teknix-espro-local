"""Switch platform for Teknix boiler."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TeknixCoordinator
from .entity import TeknixBoilerEntity
from .protocol import BoilerState


@dataclass(frozen=True, kw_only=True)
class TeknixSwitchDescription(SwitchEntityDescription):
    """Describes a Teknix switch. Writes `field` = 1 for ON and 0 for OFF."""

    field: str
    is_on_fn: Callable[[BoilerState], bool]
    teknix_description: str = ""
    teknix_warning: str = ""


SWITCHES: tuple[TeknixSwitchDescription, ...] = (
    TeknixSwitchDescription(
        key="heating",
        field="HEATING_MODE",
        is_on_fn=lambda s: s["HEATING_MODE"] == 1,
        teknix_description=(
            "Main heating on/off (INFO field HEATING_MODE). Equivalent to "
            "pressing the radiator icon on the physical panel. Also bound "
            "to the climate entity's HVAC mode (HEAT/OFF)."
        ),
    ),
    TeknixSwitchDescription(
        key="dhw",
        field="GVS_MODE",
        is_on_fn=lambda s: s["GVS_MODE"] == 1,
        teknix_description=(
            "DHW (domestic hot water) on/off (INFO field GVS_MODE). "
            "Equivalent to pressing the tap icon on the physical panel. "
            "Only meaningful if you have a DHW tank connected."
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
        TeknixSwitch(coordinator, desc) for desc in SWITCHES
    )


class TeknixSwitch(TeknixBoilerEntity, SwitchEntity):
    entity_description: TeknixSwitchDescription

    def __init__(
        self,
        coordinator: TeknixCoordinator,
        description: TeknixSwitchDescription,
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

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_field(self.entity_description.field, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_field(self.entity_description.field, 0)
