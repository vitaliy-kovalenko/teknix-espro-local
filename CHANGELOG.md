# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] — Unreleased

### Added
- Initial release.
- Config flow for local MQTT setup (Tasmota topic).
- Automatic Tasmota rule configuration on first setup (SerialDelimiter, Rule1, Rule2).
- Climate entity wrapping heating control (HVAC OFF/HEAT, target temperature, current temperature, HVAC action).
- Sensors: air temperature, coolant temperature, DHW tank temperature, current power, error code (with enum), manufacturing date, diagnostic parameters.
- Binary sensors: legionella cycle, priority consumer input, room thermostat input, weekly programmer status (heating/room/DHW).
- Number controls: heating setpoint, room setpoint, DHW tank setpoint, power level, hysteresis, DHW outlet setpoint, max power and temperature limits (P5/P7/P8/P9).
- Switches: heating on/off, DHW on/off.
- Select: heating mode (by coolant / by air).
- Services: `set_field` (for reaching any raw INFO field by name), `send_raw` (for arbitrary serial commands).
- English and Ukrainian translations.

### Removed / intentionally excluded
- **Phase mode** (`P0_PHASE_MODE`) — wrong value can destroy heating elements.
- **3-way valve** (`P2_THREE_STROKE_VALVE`) — service parameter, can misroute water between heating and DHW circuits.
- **Force pump** (`P1_SWITCH_PUMP`) — running the pump dry can damage it.
- **Thermostat control** (`CTRL_ROOM`) — unverified semantics on real hardware.

These fields can still be written manually via the `set_field` service if you understand the risk.
