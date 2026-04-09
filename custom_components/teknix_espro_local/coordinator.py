"""DataUpdateCoordinator for the Teknix boiler integration.

State comes in via MQTT push (Tasmota Rule1 forwards serial data to
`stat/<topic>/serial`), so there's no interval-based polling from HA's side.
Tasmota Rule2 polls the MCU every 30s on its own.
"""

from __future__ import annotations

import logging

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CMND_TOPIC_TEMPLATE,
    COMMAND_REFRESH_DELAY_UNITS,
    DOMAIN,
    INFO_FIELD_INDICES,
    STAT_SERIAL_TOPIC_TEMPLATE,
    TASMOTA_POLL_INTERVAL_SECONDS,
    TASMOTA_RULE1,
    TASMOTA_RULE2,
    TASMOTA_SERIAL_DELIMITER,
)
from .protocol import BoilerState, build_backlog_payload, build_t_command

_LOGGER = logging.getLogger(__name__)


class TeknixCoordinator(DataUpdateCoordinator[BoilerState]):
    """Coordinator that subscribes to serial MQTT and exposes boiler state."""

    def __init__(self, hass: HomeAssistant, topic: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}:{topic}",
            update_interval=None,  # MQTT-driven
        )
        self.topic = topic
        self.state_topic = STAT_SERIAL_TOPIC_TEMPLATE.format(topic=topic)
        self.cmnd_topic = CMND_TOPIC_TEMPLATE.format(topic=topic)
        self._unsub_mqtt = None

    async def async_start(self) -> None:
        """Subscribe to MQTT, ensure Tasmota rules, trigger first poll."""
        self._unsub_mqtt = await mqtt.async_subscribe(
            self.hass, self.state_topic, self._handle_message
        )
        await self._ensure_tasmota_rules()
        # Trigger an immediate INFO poll so we don't wait 30s for first data.
        await self._publish(f"{self.cmnd_topic}/SerialSend1", "INFO")

    async def async_stop(self) -> None:
        if self._unsub_mqtt is not None:
            self._unsub_mqtt()
            self._unsub_mqtt = None

    async def _ensure_tasmota_rules(self) -> None:
        """Configure the Tasmota-side rules and settings we rely on.

        This is best-effort; we don't verify the existing config first, we just
        overwrite. Rule1 forwards serial data, Rule2 polls INFO every 30s.
        """
        await self._publish(
            f"{self.cmnd_topic}/SerialDelimiter", str(TASMOTA_SERIAL_DELIMITER)
        )
        await self._publish(f"{self.cmnd_topic}/SerialLog", "0")
        await self._publish(f"{self.cmnd_topic}/SetOption65", "1")
        await self._publish(
            f"{self.cmnd_topic}/Rule1", TASMOTA_RULE1.format(topic=self.topic)
        )
        await self._publish(f"{self.cmnd_topic}/Rule1", "1")  # enable
        await self._publish(f"{self.cmnd_topic}/Rule2", TASMOTA_RULE2)
        await self._publish(f"{self.cmnd_topic}/Rule2", "1")  # enable
        await self._publish(
            f"{self.cmnd_topic}/RuleTimer1", str(TASMOTA_POLL_INTERVAL_SECONDS)
        )

    @callback
    def _handle_message(self, msg: mqtt.ReceiveMessage) -> None:
        state = BoilerState.from_frame(msg.payload)
        if state is None:
            # Not an INFO frame (could be OK/ER/OER echo or fragment)
            return
        self.async_set_updated_data(state)

    async def async_set_field(self, field_name: str, value: int) -> None:
        """Set a single INFO field by name."""
        if field_name not in INFO_FIELD_INDICES:
            raise ValueError(f"Unknown field: {field_name}")
        await self.async_set_field_index(INFO_FIELD_INDICES[field_name], value)

    async def async_set_field_index(self, field_index: int, value: int) -> None:
        """Set a single INFO field by its index."""
        cmd = build_t_command(field_index, value)
        payload = build_backlog_payload(cmd, COMMAND_REFRESH_DELAY_UNITS)
        await self._publish(f"{self.cmnd_topic}/Backlog", payload)

    async def async_send_raw(self, command: str) -> None:
        """Send a raw serial command (e.g. pre-built T-command)."""
        payload = build_backlog_payload(command, COMMAND_REFRESH_DELAY_UNITS)
        await self._publish(f"{self.cmnd_topic}/Backlog", payload)

    async def _publish(self, topic: str, payload: str) -> None:
        await mqtt.async_publish(self.hass, topic, payload)
