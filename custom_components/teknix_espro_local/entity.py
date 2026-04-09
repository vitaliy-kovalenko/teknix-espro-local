"""Base entity for Teknix boiler."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_MODEL, DOMAIN, MANUFACTURER
from .coordinator import TeknixCoordinator
from .protocol import BoilerState


class TeknixBoilerEntity(CoordinatorEntity[TeknixCoordinator]):
    """Shared base class for all Teknix boiler entities.

    Subclasses set `_attr_translation_key` to the key from `strings.json`
    `entity.<platform>.<key>.name`.

    If `entity_description` has `teknix_description` / `teknix_warning`
    attributes they are exposed via `extra_state_attributes` so users can
    see them in the More Info dialog.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: TeknixCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_translation_key = key
        self._attr_unique_id = f"{coordinator.topic}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.topic)},
            manufacturer=MANUFACTURER,
            model=DEFAULT_MODEL,
            name=f"Teknix ESPRO ({coordinator.topic})",
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def boiler_state(self) -> BoilerState | None:
        return self.coordinator.data

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        desc_obj = getattr(self, "entity_description", None)
        if desc_obj is None:
            return None
        attrs: dict[str, str] = {}
        description = getattr(desc_obj, "teknix_description", "")
        warning = getattr(desc_obj, "teknix_warning", "")
        if description:
            attrs["description"] = description
        if warning:
            attrs["warning"] = warning
        return attrs or None
