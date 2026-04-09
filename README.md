# Teknix ESPRO Boiler Local

Home Assistant custom integration for **Teknix ESPRO** (and compatible LEMAX / TRIANCO) electric heating boilers — 100% local control via the built-in Tasmota Wi-Fi module. No Teknix cloud account required.

Based on reverse-engineered serial protocol between the boiler's Wi-Fi module and its MCU.

## What you get

- Native **climate entity** for thermostat-style control
- Live sensors: room temperature, coolant temperature, DHW tank temperature, current power consumption, error code
- Number controls: heating setpoint, room setpoint, DHW tank setpoint, max power, hysteresis, DHW safety limits
- Switches: heating on/off, DHW on/off
- Select: heating mode (by coolant / by air)
- Binary sensors: legionella cycle, priority consumer input, programmer status
- Services: `set_field` (write any INFO field) and `send_raw` (advanced debugging)
- English and Ukrainian translations

All entities grouped under one HA device. Writes use Tasmota `Backlog` for immediate state refresh (~1 second).

**What's intentionally NOT exposed**: phase mode, 3-way valve, force pump, and external thermostat control — see the "Intentionally NOT exposed" section below for why, and how to reach these fields via a service call if you really need them.

## Prerequisite: boiler on local MQTT

> ⚠️ **This integration does NOT pair with the Teknix cloud.** Before installing the plugin, your boiler's Wi-Fi module must already be connected to **your own MQTT broker** (usually the same Mosquitto that Home Assistant uses).
>
> By default, the stock Teknix Wi-Fi module talks to `api.teknix.pro:1883`. You'll need to one-time reconfigure it to point at your local broker instead. **This is a one-way trade-off** — once you switch to local MQTT, the Teknix Android/iOS app stops working (Tasmota can only connect to one broker at a time).

### How to switch your boiler to a local MQTT broker

There are two realistic paths — pick whichever is easier for you:

#### Option A — via Tasmota captive portal (clean but requires Wi-Fi reset)

1. On the boiler's physical panel, enter the service menu and set **P11 = 1** (Wi-Fi module factory reset). This wipes both Wi-Fi and MQTT settings.
2. The Wi-Fi module boots into AP mode and creates an open network called `Tasmota_XXXXX`.
3. Connect a phone/laptop to that network. A captive portal opens automatically.
4. Enter your home Wi-Fi SSID and password, then save. The module reboots and joins your home network.
5. Once it's on your LAN, find its IP (check your router's DHCP leases; the hostname will start with `tasmota-`).
6. Open `http://<boiler-ip>/` in a browser — this is the Tasmota web UI.
7. Go to **Configuration → Configure MQTT**:
   - **Host**: your Mosquitto IP (e.g. `192.168.1.50`)
   - **Port**: `1883`
   - **User** / **Password**: whatever your broker requires
   - **Topic**: leave as the auto-generated one or set something memorable like `boiler_kotel`
8. Save. The boiler will reboot and connect to your broker. You can verify in `mosquitto_sub -t 'tele/<topic>/LWT' -v` — it should publish `Online`.

#### Option B — via the Tasmota web UI directly (no reset needed)

If you can already reach the boiler's web UI on your LAN (for example because you configured it once before), skip Option A and go straight to the Tasmota Configuration → MQTT page to repoint the broker.

### After the switch

- The Teknix app will show "disconnected" / no longer work — expected.
- Do NOT run `Reset 5` on the Tasmota console. It wipes MQTT config (Tasmota stores Wi-Fi and MQTT in the same settings block).
- Make a note of your Tasmota topic — you'll need it when setting up this integration.

## Requirements

- A **Teknix ESPRO / LEMAX ProPLUS / TRIANCO AZTEC** boiler with the stock Wi-Fi module (runs Tasmota 8.5.1 internally)
- Home Assistant **2024.4.0** or later
- The **MQTT integration** configured in HA, connected to the same broker as the boiler
- **The boiler itself already connected to your local MQTT broker** — see the prerequisite section above

## Installation

### Via HACS (custom repository)

1. Open HACS in Home Assistant.
2. Click the 3-dot menu in the top-right → **Custom repositories**.
3. Repository: `https://github.com/vitaliy-kovalenko/teknix-espro-local`, Type: **Integration**, click Add.
4. Find "Teknix ESPRO Boiler Local" in the HACS integration list and click Download.
5. Restart Home Assistant.
6. Settings → **Devices & Services** → **Add Integration** → search for "Teknix ESPRO Boiler Local".
7. Enter your Tasmota topic (see next section).

### Manual

1. Copy `custom_components/teknix_espro_local/` into your HA `config/custom_components/` directory.
2. Restart Home Assistant.
3. Settings → **Devices & Services** → **Add Integration** → "Teknix ESPRO Boiler Local".

### ⚠️ Finding your Tasmota topic

> **This is the #1 cause of setup failures.** The "Tasmota topic" field during integration setup must **EXACTLY** match the topic configured on your boiler's Wi-Fi module. It is NOT the device IP, hostname, MQTT client ID, or auto-discovery prefix.

To find it:

1. Open the Tasmota web UI of your boiler — e.g. `http://<boiler-ip>/` in a browser.
2. Go to **Configuration → Configure MQTT**.
3. Look at the **Topic** field. That is the value you enter in the HA integration.
4. Alternatively, open the Tasmota console and type `Topic` — it prints the current value.

**Enter only the plain topic name** (e.g. `boiler_kotel`, `tasmota_A1B2C3`). Do NOT include:
- ❌ `stat/boiler_kotel/serial` — this is a full topic path, wrong
- ❌ `cmnd/boiler_kotel` — also a full topic path, wrong
- ❌ `192.168.42.101` — this is the IP address, wrong
- ❌ `homeassistant/...` — this is the auto-discovery prefix, wrong

The plugin builds `stat/<topic>/serial` and `cmnd/<topic>/...` internally. If you enter a wrong topic, the integration will load but no state updates will arrive and commands will be silently ignored.

## Setup

During setup the integration will auto-configure the Tasmota rules on your boiler via MQTT:

- `SerialDelimiter 82` (needed for INFO frame parsing)
- `SerialLog 0` (prevents debug output polluting the MCU)
- `Rule1` — forwards serial data to `stat/<topic>/serial`
- `Rule2` + `RuleTimer1 30` — polls the MCU for INFO every 30 seconds

No manual Tasmota console work needed.

## Services

### `teknix_espro_local.set_field`

Write any INFO field by name. Useful for fields not exposed as entities.

```yaml
service: teknix_espro_local.set_field
target:
  device_id: <your boiler device id>
data:
  field: TEMPER_BOILER_OUT
  value: 65
```

### `teknix_espro_local.send_raw`

Send a pre-built T-command or raw string. For debugging only.

```yaml
service: teknix_espro_local.send_raw
target:
  device_id: <your boiler device id>
data:
  command: "INFO"
```

## Protocol Notes

- **INFO format**: `I1&<45 comma-separated fields>&<checksum>Z`. Checksum = `sum(fields) + 1`.
- **T-command format**: `T<index 2d><value 2d><00 pad><digit-sum checksum 2d>Z`. Index = INFO field + 2. Checksum = sum of individual digits.
- **Field naming** comes from the public Teknix Swagger at `https://api.teknix.pro/v3/api-docs` (the `Param` enum).

See the project's `teknix-espro-ha-integration.md` for the full reverse-engineering write-up.

## Entities and what they do

Every entity is documented below with a short description. Entities marked ⚠️ have caveats — read them before using. Each entity also exposes its description (and any warning) as HA extra state attributes, so you can see them in the entity's "More info" dialog.

### Climate

| Entity | Description |
|--------|-------------|
| `climate.teknix_espro_boiler` ⚠️ | Native HA thermostat. HEAT/OFF ↔ `HEATING_MODE`, target temperature ↔ `TEMPER_ROOM_WHOLE`, current temperature ↔ `SENSOR_ROOM`, HVAC action ↔ current `POWER`. **Set "Heating mode" to "by air" for this to work intuitively**, otherwise the boiler regulates by coolant temp and ignores the room setpoint. |

### Main sensors

| Entity | INFO field | Description |
|--------|-----------|-------------|
| Air temperature | 39 `SENSOR_ROOM` | Room temperature from the boiler's external NTC sensor (must be ≥50 cm from the boiler per the manual). |
| Coolant temperature | 37 `SENSOR_BOILER_OUT` | Water temperature at the boiler outlet — the main "system temperature" reading. |
| DHW tank temperature | 38 `SENSOR_TANK_GVS` | DHW tank temperature sensor. ⚠️ If no DHW tank is connected, reads the ambient NTC input, not actual water. |
| Current power ⚠️ | 29+30 `POWER`+`POWER_FRACT` | Power draw reported by the MCU. **Formula is unverified against a real kWh meter — treat as approximate.** |
| Error code | 5 `CODE_ERROR` | Boiler error code (E1-E7). E1 = current leak, E2 = water flow fault, E3 = coolant sensor fault, E4 = air sensor fault, E5 = DHW sensor fault, E6 = overheat, E7 = no remote connection. **E1 and E3 are dangerous.** |

### Main controls

| Entity | INFO field | Description |
|--------|-----------|-------------|
| Heating setpoint | 0 `TEMPER_BOILER_OUT` | Target outlet water temperature (30-80 °C). Primary setpoint in "by coolant" mode. |
| Room setpoint | 1 `TEMPER_ROOM_WHOLE` | Target room temperature (10-26 °C). Primary setpoint in "by air" mode. Also bound to climate entity target. |
| Power | 17 `P4_MAX_POWER_HEAT` | Max heating power in kW. Stored as relay count × 2 kW. ⚠️ Don't exceed your boiler's nameplate rating. |
| Hysteresis | 4 `TEMPER_DIFF` | Temperature differential for heating cycles (0.1-2.0 °C). Smaller = tighter control but more cycling. |
| DHW tank setpoint | 7 `TEMPER_TANK` | Target DHW tank temperature (30-60 °C). Only meaningful with DHW connected. |
| Heating mode ⚠️ | 9 `STEP_LAST_HEATING` | `by_coolant` (1) regulates outlet water; `by_air` (2) regulates room temperature. Setting to `by_coolant` makes the boiler heat hard regardless of room temperature. |
| Heating | 10 `HEATING_MODE` | Main heating on/off. Bound to climate HVAC mode. |
| DHW | 11 `GVS_MODE` | DHW (tap water heating) on/off. |

### Safety limits and configuration

These live under the "Configuration" section of the device page.

| Entity | INFO field | Description |
|--------|-----------|-------------|
| P7 max heating temperature ⚠️ | 20 `P7_LIMIT_MAX_TEMPER_HEAT` | Safety cap for heating outlet water (factory 80 °C). **Don't lower below your heating setpoint** or heating will be capped. |
| DHW outlet setpoint | 6 `TEMPER_BOILER_OUT_GVS` | Target outlet water temperature while heating the DHW tank. |
| P5 max DHW power | 18 `P5_MAX_POWER_GVS` | Max heating power while in DHW mode (kW). |
| P8 max DHW tank | 21 `P8_LIMIT_MAX_TEMPER_TANK_GVS` | Safety limit for DHW tank temperature (factory 60 °C). |
| P9 max boiler in DHW | 22 `P9_LIMIT_MAX_TEMPER_BOILER_GVS` | Safety limit for outlet water during DHW cycle (factory 80 °C). |

### Intentionally NOT exposed as entities

The following parameters are readable in the INFO frame and could be settable via the serial T-command, but they are **not exposed** as HA entities in this plugin because writing wrong values can damage the boiler or cause unsafe operation, and the exact write semantics have not been verified on real hardware:

| Parameter | INFO field | Why it's hidden |
|-----------|-----------|-----------------|
| **Phase mode** | 13 `P0_PHASE_MODE` | Single-phase / three-phase configuration. A wrong value can **destroy heating elements, trip breakers, or cause a fire**. Only a certified electrician should touch this, and only via the service menu on the physical panel. |
| **3-way valve** | 15 `P2_THREE_STROKE_VALVE` | Service parameter that can misroute water between heating and DHW circuits. Not safe to change from software without verifying plumbing. |
| **Force pump** | 14 `P1_SWITCH_PUMP` | Forcing the circulation pump on outside of a heating cycle can run it dry and damage it. Normally managed automatically by the boiler firmware. |
| **Thermostat control** | 3 `CTRL_ROOM` | Enables/disables the external dry-contact room thermostat input. Uses values 11/12 per the Teknix API enum — unverified on real hardware, many boilers return `0` when unused. |

If you really need to change one of these, use the `teknix_espro_local.set_field` service (see below) with full awareness of the risk. The plugin deliberately does not put a slider or toggle in the UI where an accidental click could cause damage.

### Diagnostic sensors

Hidden under the "Diagnostic" section; normally not needed.

| Entity | INFO field | Description |
|--------|-----------|-------------|
| Manufacturing date | 24-26 `ISSUE_YEAR/MONTH/DAY` | Boiler manufacturing date (YYYY-MM-DD). |
| Last heating step | 9 `STEP_LAST_HEATING` | Raw value of the heating control step (same field as the "Heating mode" select). |
| Last DHW step | 12 `STEP_LAST_GVS` | Raw value of the DHW control step. |
| P6 priority consumer | 19 `P6_CONSUMER_PRIORITY` | Power limit (kW) applied when the priority consumer input is active. |
| Legionella mode | 8 `LEGIONELLA_MODE` | Anti-legionella cycle configuration value. |

### Diagnostic binary sensors

| Entity | INFO field | Description |
|--------|-----------|-------------|
| Legionella cycle active | 23 `LEGIONELLA_CYCLE` | ON while the anti-legionella sanitation cycle is running. |
| Priority consumer input ⚠️ | 40 `SENSOR_PP` | External high-load device is drawing current. **Hardware signal is inverted — the entity already flips it, so ON/OFF match intuition.** |
| Room thermostat input ⚠️ | 41 `SENSOR_R` | External dry-contact room thermostat is calling for heat. **Inverted at hardware level — entity flips it.** |
| Heating programmer active | 42 `STAT_PROG_OUT` | Built-in weekly programmer for heating is running. |
| Room programmer active | 43 `STAT_PROG_ROOM` | Built-in weekly programmer for room temperature is running. |
| DHW programmer active | 44 `STAT_PROG_GVS` | Built-in weekly programmer for DHW is running. |

### Not exposed as entities

These INFO fields can still be read/written via the `set_field` service if you need them:

- `TEMPER_FRACT` (2) — room setpoint fractional part
- `STEND_NUMBER*` (31-36) — factory test stand numbers
- `SERIES` / `BRAND` (27-28) — manufacturer metadata

## Known Limitations

- **Only tested on one ESPRO-12**. Other hardware revisions may have protocol differences. Please file issues with your boiler model and sample INFO frames.
- **Multi-field T-commands are not supported** — each write is one field at a time. The boiler's backend-composed multi-field atomic writes (seen in Teknix cloud traffic as longer T-commands like `T12011102032404000021Z`) are not yet decoded.
- **Weekly programmer is read-only** — you can see if it's active (STAT_PROG_* binary sensors) but not edit schedules. Use HA's native scheduler instead.
- **Dangerous fields** like phase mode and 3-way valve are exposed but should NOT be changed unless you know what you're doing. Wrong values can damage the boiler.

## Translations

English and Ukrainian (`uk`) are bundled. PRs welcome for more languages.

## License

MIT. Use at your own risk — this is unofficial and Teknix does not support it.
