"""Config flow for Teknix ESPRO Boiler Local."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_TASMOTA_TOPIC, DOMAIN

DEFAULT_TOPIC = "boiler_kotel"


class TeknixEsproLocalConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Teknix boiler integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step: pick the Tasmota topic."""
        errors: dict[str, str] = {}

        if user_input is not None:
            topic: str = user_input[CONF_TASMOTA_TOPIC].strip().strip("/")
            if not topic:
                errors["base"] = "invalid_topic"
            else:
                await self.async_set_unique_id(f"{DOMAIN}_{topic}")
                self._abort_if_unique_id_configured()

                # Require the MQTT integration to be loaded — we can't talk
                # to the boiler without it.
                if not await mqtt.async_wait_for_mqtt_client(self.hass):
                    errors["base"] = "mqtt_not_available"
                else:
                    return self.async_create_entry(
                        title=f"Teknix ESPRO ({topic})",
                        data={CONF_TASMOTA_TOPIC: topic},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TASMOTA_TOPIC, default=DEFAULT_TOPIC): str,
                }
            ),
            errors=errors,
        )
