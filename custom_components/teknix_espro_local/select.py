"""Select platform for Teknix boiler."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TeknixCoordinator
from .entity import TeknixBoilerEntity


@dataclass(frozen=True, kw_only=True)
class TeknixSelectDescription(SelectEntityDescription):
    """Describes a select entity backed by a single INFO field.

    `field` = INFO field name to read/write.
    `option_to_raw` maps HA select option → raw integer to write.
    `raw_to_option` maps raw integer → HA select option.
    """

    field: str
    option_to_raw: dict[str, int]
    raw_to_option: dict[int, str]
    teknix_description: str = ""
    teknix_warning: str = ""


def _build_desc(
    key: str,
    field: str,
    options: dict[str, int],
    *,
    entity_category: EntityCategory | None = None,
    description: str = "",
    warning: str = "",
) -> TeknixSelectDescription:
    return TeknixSelectDescription(
        key=key,
        field=field,
        options=list(options.keys()),
        entity_category=entity_category,
        option_to_raw=options,
        raw_to_option={v: k for k, v in options.items()},
        teknix_description=description,
        teknix_warning=warning,
    )


SELECTS: tuple[TeknixSelectDescription, ...] = (
    _build_desc(
        "heating_mode",
        "STEP_LAST_HEATING",
        # Confirmed in live testing: 1 = by coolant, 2 = by air
        {"by_coolant": 1, "by_air": 2},
        description=(
            "How the boiler decides whether to heat. 'By coolant' regulates "
            "the outlet water temperature to the heating setpoint (direct "
            "control). 'By air' uses the room temperature sensor to regulate "
            "the room setpoint (comfort mode)."
        ),
        warning=(
            "Backed by INFO field STEP_LAST_HEATING. The Teknix API Param "
            "enum documents this as a 'last change tracker', but on real "
            "boilers writing 1/2 directly controls the active heating mode. "
            "Switching to 'by coolant' makes the boiler heat hard regardless "
            "of room temperature — the room setpoint and climate entity "
            "target will stop having any effect until you switch back."
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
        TeknixSelect(coordinator, desc) for desc in SELECTS
    )


class TeknixSelect(TeknixBoilerEntity, SelectEntity):
    entity_description: TeknixSelectDescription

    def __init__(
        self,
        coordinator: TeknixCoordinator,
        description: TeknixSelectDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        if (state := self.boiler_state) is None:
            return None
        try:
            raw = state[self.entity_description.field]
        except (KeyError, IndexError):
            return None
        return self.entity_description.raw_to_option.get(raw)

    async def async_select_option(self, option: str) -> None:
        raw = self.entity_description.option_to_raw[option]
        await self.coordinator.async_set_field(self.entity_description.field, raw)
