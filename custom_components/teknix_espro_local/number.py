"""Number platform for Teknix boiler."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TeknixCoordinator
from .entity import TeknixBoilerEntity
from .protocol import BoilerState


@dataclass(frozen=True, kw_only=True)
class TeknixNumberDescription(NumberEntityDescription):
    """Describes a Teknix number entity.

    `value_fn` extracts the display value from BoilerState.
    `field` is the INFO field name (or index) to write.
    `encode_fn` converts the user's display value → the raw integer value
    to send in the T-command.
    """

    field: str
    value_fn: Callable[[BoilerState], float | int | None]
    encode_fn: Callable[[float], int]
    teknix_description: str = ""
    teknix_warning: str = ""


def _identity(v: float) -> int:
    return int(v)


def _x10(v: float) -> int:
    """Multiply by 10 (for TEMPER_DIFF which stores 0.1°C units)."""
    return int(round(v * 10))


def _half_kw(v: float) -> int:
    """Divide by 2 (for P4_MAX_POWER_HEAT which stores kW/2)."""
    return int(v) // 2


NUMBERS: tuple[TeknixNumberDescription, ...] = (
    TeknixNumberDescription(
        key="heating_setpoint",
        field="TEMPER_BOILER_OUT",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=30,
        native_max_value=80,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda s: s["TEMPER_BOILER_OUT"],
        encode_fn=_identity,
        teknix_description=(
            "Target water temperature at the boiler outlet in heating mode "
            "(INFO field TEMPER_BOILER_OUT, range 30–80°C). Used when heating "
            "mode is 'by coolant'; in 'by air' mode this is the upper cap."
        ),
    ),
    TeknixNumberDescription(
        key="room_setpoint",
        field="TEMPER_ROOM_WHOLE",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=10,
        native_max_value=26,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda s: s["TEMPER_ROOM_WHOLE"],
        encode_fn=_identity,
        teknix_description=(
            "Target room air temperature (INFO field TEMPER_ROOM_WHOLE, "
            "range 10–26°C). Used only when heating mode is 'by air'. "
            "Also bound to the climate entity's target temperature."
        ),
    ),
    TeknixNumberDescription(
        key="power_level",
        field="P4_MAX_POWER_HEAT",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=2,
        native_max_value=12,
        native_step=2,
        mode=NumberMode.SLIDER,
        value_fn=lambda s: s["P4_MAX_POWER_HEAT"] * 2,
        encode_fn=_half_kw,
        teknix_description=(
            "Maximum heating power in kilowatts (service parameter P4). "
            "Stored internally as number of active heating element relays; "
            "each relay = 2 kW. For a 12 kW boiler the max is 6 relays."
        ),
        teknix_warning=(
            "Do not exceed your boiler's nameplate power rating. The raw "
            "field range is 0–9 relays but actual maximum depends on "
            "hardware (how many elements are installed)."
        ),
    ),
    TeknixNumberDescription(
        key="hysteresis",
        field="TEMPER_DIFF",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0.1,
        native_max_value=2.0,
        native_step=0.1,
        mode=NumberMode.SLIDER,
        value_fn=lambda s: round(s["TEMPER_DIFF"] / 10, 1),
        encode_fn=_x10,
        teknix_description=(
            "Temperature hysteresis (differential) for heating cycles: how "
            "far the outlet temperature drifts from setpoint before the "
            "boiler kicks in. Stored in 0.1°C units, so 0.5°C = raw value 5. "
            "Smaller = tighter control but more cycling; larger = fewer "
            "cycles but more temperature swing."
        ),
    ),
    TeknixNumberDescription(
        key="p7_max_heating_temp",
        field="P7_LIMIT_MAX_TEMPER_HEAT",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=30,
        native_max_value=80,
        native_step=1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda s: s["P7_LIMIT_MAX_TEMPER_HEAT"],
        encode_fn=_identity,
        teknix_description=(
            "Service parameter P7: upper safety limit for outlet water "
            "temperature in heating mode. The boiler refuses to heat beyond "
            "this value. Factory default is 80°C."
        ),
        teknix_warning=(
            "Do not lower below your heating setpoint, otherwise heating "
            "will be capped by the safety limit and you'll never reach the "
            "requested temperature."
        ),
    ),
    # ---- DHW (tap water heating) ----
    TeknixNumberDescription(
        key="dhw_tank_setpoint",
        field="TEMPER_TANK",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=30,
        native_max_value=60,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda s: s["TEMPER_TANK"],
        encode_fn=_identity,
        teknix_description=(
            "Target temperature for the DHW (domestic hot water) tank "
            "(INFO field TEMPER_TANK, range 30–60°C). Only meaningful if "
            "you have an indirect DHW tank connected."
        ),
    ),
    TeknixNumberDescription(
        key="dhw_out_setpoint",
        field="TEMPER_BOILER_OUT_GVS",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=30,
        native_max_value=80,
        native_step=1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda s: s["TEMPER_BOILER_OUT_GVS"],
        encode_fn=_identity,
        teknix_description=(
            "Target water temperature at the boiler outlet when running "
            "DHW heating (INFO field TEMPER_BOILER_OUT_GVS). Typically higher "
            "than the tank setpoint to speed up DHW recovery."
        ),
    ),
    TeknixNumberDescription(
        key="p5_max_power_gvs",
        field="P5_MAX_POWER_GVS",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        native_min_value=2,
        native_max_value=12,
        native_step=2,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda s: s["P5_MAX_POWER_GVS"] * 2,
        encode_fn=_half_kw,
        teknix_description=(
            "Service parameter P5: maximum heating power when operating in "
            "DHW mode. Stored as relay count, shown in kW. Equivalent to P4 "
            "but for the DHW cycle."
        ),
    ),
    TeknixNumberDescription(
        key="p8_max_dhw_tank",
        field="P8_LIMIT_MAX_TEMPER_TANK_GVS",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=30,
        native_max_value=60,
        native_step=1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda s: s["P8_LIMIT_MAX_TEMPER_TANK_GVS"],
        encode_fn=_identity,
        teknix_description=(
            "Service parameter P8: safety limit for DHW tank temperature. "
            "Factory default is 60°C. The boiler refuses to heat the DHW tank "
            "above this value regardless of the user setpoint."
        ),
    ),
    TeknixNumberDescription(
        key="p9_max_boiler_gvs",
        field="P9_LIMIT_MAX_TEMPER_BOILER_GVS",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=30,
        native_max_value=80,
        native_step=1,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda s: s["P9_LIMIT_MAX_TEMPER_BOILER_GVS"],
        encode_fn=_identity,
        teknix_description=(
            "Service parameter P9: safety limit for boiler outlet temperature "
            "while running DHW cycle. Factory default is 80°C."
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
        TeknixNumber(coordinator, desc) for desc in NUMBERS
    )


class TeknixNumber(TeknixBoilerEntity, NumberEntity):
    """A settable numeric parameter."""

    entity_description: TeknixNumberDescription

    def __init__(
        self,
        coordinator: TeknixCoordinator,
        description: TeknixNumberDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        if (state := self.boiler_state) is None:
            return None
        try:
            return self.entity_description.value_fn(state)
        except (KeyError, IndexError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        raw = self.entity_description.encode_fn(value)
        await self.coordinator.async_set_field(self.entity_description.field, raw)
