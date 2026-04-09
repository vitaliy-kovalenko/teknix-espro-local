"""Climate platform for Teknix boiler.

Exposes a single native HA climate entity that wraps:
- target_temperature      → TEMPER_ROOM_WHOLE (field 1)
- current_temperature     → SENSOR_ROOM (field 39, ÷10)
- hvac_mode (OFF/HEAT)    → HEATING_MODE (field 10)
- hvac_action             → inferred from heating state + sensor delta
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TeknixCoordinator
from .entity import TeknixBoilerEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: TeknixCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TeknixClimate(coordinator)])


_CLIMATE_DESCRIPTION = (
    "Native HA climate entity wrapping the boiler's heating control: "
    "HVAC mode (OFF/HEAT) is bound to HEATING_MODE (field 10), target "
    "temperature to the room setpoint TEMPER_ROOM_WHOLE (field 1), current "
    "temperature to SENSOR_ROOM (field 39), and HVAC action is inferred "
    "from the current power draw (POWER field > 0 = HEATING, else IDLE)."
)

_CLIMATE_WARNING = (
    "For the climate entity to make sense, set 'Heating mode' to 'by air' — "
    "otherwise the boiler regulates by coolant temperature and ignores the "
    "room setpoint."
)


class TeknixClimate(TeknixBoilerEntity, ClimateEntity):
    """Teknix boiler as a native HA climate entity."""

    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 10
    _attr_max_temp = 26
    _attr_target_temperature_step = 1
    _attr_translation_key = "boiler"

    def __init__(self, coordinator: TeknixCoordinator) -> None:
        super().__init__(coordinator, "boiler")

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        return {
            "description": _CLIMATE_DESCRIPTION,
            "warning": _CLIMATE_WARNING,
        }

    @property
    def current_temperature(self) -> float | None:
        if (state := self.boiler_state) is None:
            return None
        try:
            return round(state["SENSOR_ROOM"] / 10, 1)
        except (KeyError, IndexError):
            return None

    @property
    def target_temperature(self) -> float | None:
        if (state := self.boiler_state) is None:
            return None
        try:
            return float(state["TEMPER_ROOM_WHOLE"])
        except (KeyError, IndexError):
            return None

    @property
    def hvac_mode(self) -> HVACMode | None:
        if (state := self.boiler_state) is None:
            return None
        try:
            return HVACMode.HEAT if state["HEATING_MODE"] == 1 else HVACMode.OFF
        except (KeyError, IndexError):
            return None

    @property
    def hvac_action(self) -> HVACAction | None:
        if (state := self.boiler_state) is None:
            return None
        try:
            if state["HEATING_MODE"] != 1:
                return HVACAction.OFF
            # Use current power draw (field 29 = 0 means idle)
            return HVACAction.HEATING if state["POWER"] > 0 else HVACAction.IDLE
        except (KeyError, IndexError):
            return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        await self.coordinator.async_set_field("TEMPER_ROOM_WHOLE", int(temp))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        target = 1 if hvac_mode == HVACMode.HEAT else 0
        await self.coordinator.async_set_field("HEATING_MODE", target)

    async def async_turn_on(self) -> None:
        await self.coordinator.async_set_field("HEATING_MODE", 1)

    async def async_turn_off(self) -> None:
        await self.coordinator.async_set_field("HEATING_MODE", 0)
