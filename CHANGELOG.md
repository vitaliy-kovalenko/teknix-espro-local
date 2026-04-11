# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.1] — 2026-04-11

### Fixed
- **`current_power` sensor was always 4 kW** — INFO fields POWER/POWER_FRACT (29/30) are static factory data (rated nameplate power), not live consumption. Replaced with `rated_power` diagnostic sensor showing 12.0 kW for ESPRO-12.
- **Climate `hvac_action` was always HEATING** — used the same static POWER field. Now inferred from coolant-vs-room temperature delta (coolant > room + 3°C = actively heating).

## [0.1.0] — 2026-04-09

### Added
- Initial release.
- Config flow for local MQTT setup (Tasmota topic).
- Automatic Tasmota rule configuration on first setup (SerialDelimiter, Rule1, Rule2).
- Climate entity wrapping heating control (HVAC OFF/HEAT, target temperature, current temperature, HVAC action).
- Sensors: air temperature, coolant temperature, DHW tank temperature, rated power, error code (with enum), manufacturing date, diagnostic parameters.
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
