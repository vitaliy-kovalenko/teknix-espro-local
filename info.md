# Teknix ESPRO Boiler Local

Home Assistant integration for **Teknix ESPRO** (and compatible LEMAX / TRIANCO) electric heating boilers — 100% local control via the stock Tasmota Wi-Fi module. No Teknix cloud account required.

## Features

- Native **climate entity** for thermostat-style control
- Live sensors: room / coolant / DHW temperatures, current power, error code
- Number controls: heating setpoint, room setpoint, DHW setpoint, power level, hysteresis, safety limits
- Switches: heating on/off, DHW on/off, force pump
- Selects: heating mode (by coolant/air), 3-way valve, phase mode
- Services: `set_field` (write any INFO field) and `send_raw` (advanced debugging)
- English and Ukrainian translations

## How it works

The boiler's Wi-Fi module runs Tasmota internally and talks to the MCU over UART. The integration:

1. Subscribes to the Tasmota serial topic via MQTT
2. Parses the boiler's `I1&...Z` status frame into ~45 named fields
3. Configures Tasmota rules for 30s INFO polling automatically
4. Sends T-prefix write commands (with checksum) to change settings
5. Uses `Backlog` to refresh state within ~1 second of any change

## Prerequisite

**Your boiler's Wi-Fi module must already be connected to your local MQTT broker** (not `api.teknix.pro`). This is a one-time reconfiguration — see the full README for step-by-step instructions. Switching to local MQTT also means the Teknix mobile app stops working, because the Tasmota module can only connect to one broker at a time.

## Requirements

- Teknix / LEMAX / TRIANCO boiler with stock Wi-Fi module
- MQTT integration configured in Home Assistant and connected to the same broker as the boiler
- Home Assistant 2024.4.0+

## Setup

After installation, add via Settings → Devices & Services → Add Integration → "Teknix ESPRO Boiler Local". Enter your Tasmota topic (e.g. `boiler_kotel`) and the integration handles the rest.

See the [full README](https://github.com/vitaliy-kovalenko/teknix-espro-local) for protocol details, field mapping, and the reverse-engineering story.
