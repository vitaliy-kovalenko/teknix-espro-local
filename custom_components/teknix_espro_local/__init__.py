"""The Teknix ESPRO Boiler Local integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr

from .const import CONF_TASMOTA_TOPIC, DOMAIN, INFO_FIELD_INDICES
from .coordinator import TeknixCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

SERVICE_SET_FIELD = "set_field"
SERVICE_SEND_RAW = "send_raw"

SET_FIELD_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Required("field"): vol.All(str, vol.In(INFO_FIELD_INDICES)),
        vol.Required("value"): vol.All(int, vol.Range(min=0, max=99)),
    }
)

SEND_RAW_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Required("command"): str,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    topic = entry.data[CONF_TASMOTA_TOPIC]
    coordinator = TeknixCoordinator(hass, topic)
    await coordinator.async_start()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _register_services(hass)
    return True


def _register_services(hass: HomeAssistant) -> None:
    """Register integration-wide services (once)."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_FIELD):
        return

    def _coordinator_for_device(device_id: str) -> TeknixCoordinator | None:
        device = dr.async_get(hass).async_get(device_id)
        if device is None:
            return None
        for entry_id in device.config_entries:
            coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
            if coordinator is not None:
                return coordinator
        return None

    async def set_field(call: ServiceCall) -> None:
        coordinator = _coordinator_for_device(call.data["device_id"])
        if coordinator is None:
            raise ValueError("No Teknix boiler found for the given device_id")
        await coordinator.async_set_field(call.data["field"], call.data["value"])

    async def send_raw(call: ServiceCall) -> None:
        coordinator = _coordinator_for_device(call.data["device_id"])
        if coordinator is None:
            raise ValueError("No Teknix boiler found for the given device_id")
        await coordinator.async_send_raw(call.data["command"])

    hass.services.async_register(DOMAIN, SERVICE_SET_FIELD, set_field, schema=SET_FIELD_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SEND_RAW, send_raw, schema=SEND_RAW_SCHEMA)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: TeknixCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_stop()
        # If this was the last entry, remove services
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_SET_FIELD)
            hass.services.async_remove(DOMAIN, SERVICE_SEND_RAW)
    return unload_ok
