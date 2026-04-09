"""Sensor platform for Teknix boiler."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
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
class TeknixSensorDescription(SensorEntityDescription):
    """Describes a Teknix sensor and how to extract its value from BoilerState."""

    value_fn: Callable[[BoilerState], float | int | str | None]
    teknix_description: str = ""
    teknix_warning: str = ""


# Code-to-label map for the CODE_ERROR sensor.
ERROR_CODES: dict[int, str] = {
    0: "ok",
    1: "e1_current_leak",
    2: "e2_water_flow",
    3: "e3_coolant_sensor",
    4: "e4_air_sensor",
    5: "e5_dhw_sensor",
    6: "e6_overheat",
    7: "e7_no_connection",
}


def _error_code(state: BoilerState) -> str:
    return ERROR_CODES.get(state["CODE_ERROR"], f"e{state['CODE_ERROR']}")


def _issue_date(state: BoilerState) -> str | None:
    year = state["ISSUE_YEAR"]
    month = state["ISSUE_MONTH"]
    day = state["ISSUE_DAY"]
    if year == 0:
        return None
    return f"20{year:02d}-{month:02d}-{day:02d}"


SENSORS: tuple[TeknixSensorDescription, ...] = (
    TeknixSensorDescription(
        key="air_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda s: round(s["SENSOR_ROOM"] / 10, 1),
        teknix_description=(
            "Room air temperature read by the boiler's external NTC sensor "
            "(INFO field SENSOR_ROOM, 0.1°C precision). Per the Teknix manual "
            "this sensor must be installed at least 50 cm away from the boiler "
            "to avoid heat bias."
        ),
    ),
    TeknixSensorDescription(
        key="coolant_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda s: round(s["SENSOR_BOILER_OUT"] / 10, 1),
        teknix_description=(
            "Water temperature at the boiler outlet, measured at the "
            "heating element outlet (INFO field SENSOR_BOILER_OUT). "
            "This is the main 'system temperature' reading."
        ),
    ),
    TeknixSensorDescription(
        key="current_power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        value_fn=lambda s: round(s["POWER"] * 2 + s["POWER_FRACT"] / 10, 1),
        teknix_description=(
            "Current power draw reported by the boiler MCU. Derived from "
            "POWER (whole part) and POWER_FRACT (fractional part)."
        ),
        teknix_warning=(
            "Formula (POWER × 2 + POWER_FRACT / 10) is based on field names "
            "from the Teknix API Param enum and has NOT been verified against "
            "a real kWh meter. Treat the value as approximate."
        ),
    ),
    TeknixSensorDescription(
        key="error_code",
        device_class=SensorDeviceClass.ENUM,
        options=list(ERROR_CODES.values()),
        value_fn=_error_code,
        teknix_description=(
            "Current boiler error code. E1=current leak, E2=water flow fault, "
            "E3=coolant sensor fault, E4=air sensor fault, E5=DHW sensor fault, "
            "E6=overheat, E7=no remote connection. E1 and E3 are dangerous — "
            "stop using the boiler."
        ),
    ),
    TeknixSensorDescription(
        key="dhw_tank_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda s: round(s["SENSOR_TANK_GVS"] / 10, 1),
        teknix_description=(
            "Temperature sensor for the DHW (domestic hot water) tank, used "
            "when the boiler is connected to an indirect hot water tank."
        ),
        teknix_warning=(
            "If your boiler is heating-only and has no DHW tank connected, "
            "this reading reflects the ambient temperature at the NTC sensor "
            "input, not actual water temperature."
        ),
    ),
    # --- Diagnostic ---
    TeknixSensorDescription(
        key="issue_date",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_issue_date,
        teknix_description=(
            "Boiler manufacturing date, decoded from INFO fields "
            "ISSUE_YEAR / ISSUE_MONTH / ISSUE_DAY."
        ),
    ),
    TeknixSensorDescription(
        key="p6_consumer_priority",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s["P6_CONSUMER_PRIORITY"] * 2,
        teknix_description=(
            "Service parameter P6: power limit applied when the boiler's "
            "'priority consumer' physical input is active (e.g. when a "
            "high-load appliance on the same circuit draws current). Stored "
            "internally as relay count, shown here in kW."
        ),
    ),
    TeknixSensorDescription(
        key="legionella_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s["LEGIONELLA_MODE"],
        teknix_description=(
            "Anti-legionella cycle configuration value (INFO field "
            "LEGIONELLA_MODE). Only relevant if DHW is connected."
        ),
    ),
    TeknixSensorDescription(
        key="step_last_heating",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s["STEP_LAST_HEATING"],
        teknix_description=(
            "Internal tracker for the last-used heating control step "
            "(1 = regulate by coolant temperature, 2 = regulate by room air). "
            "Updates when you change 'Heating mode'."
        ),
    ),
    TeknixSensorDescription(
        key="step_last_gvs",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s["STEP_LAST_GVS"],
        teknix_description=(
            "Internal tracker for the last DHW control step. Equivalent to "
            "step_last_heating but for DHW mode."
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
        TeknixSensor(coordinator, desc) for desc in SENSORS
    )


class TeknixSensor(TeknixBoilerEntity, SensorEntity):
    """A Teknix boiler sensor."""

    entity_description: TeknixSensorDescription

    def __init__(
        self,
        coordinator: TeknixCoordinator,
        description: TeknixSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | str | None:
        if (state := self.boiler_state) is None:
            return None
        try:
            return self.entity_description.value_fn(state)
        except (KeyError, IndexError, TypeError, ValueError):
            return None
