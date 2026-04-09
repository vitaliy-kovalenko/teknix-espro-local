"""Constants for the Teknix ESPRO Boiler Local integration."""

from __future__ import annotations

DOMAIN = "teknix_espro_local"
MANUFACTURER = "Teknix Engineering"
DEFAULT_MODEL = "ESPRO"

# Configuration keys
CONF_TASMOTA_TOPIC = "tasmota_topic"

# INFO field index → field name (from Teknix Swagger API Param enum).
# parts[N+1] in the raw "I1&...Z" frame is INFO field N.
INFO_FIELD_NAMES: dict[int, str] = {
    0: "TEMPER_BOILER_OUT",
    1: "TEMPER_ROOM_WHOLE",
    2: "TEMPER_FRACT",
    3: "CTRL_ROOM",
    4: "TEMPER_DIFF",
    5: "CODE_ERROR",
    6: "TEMPER_BOILER_OUT_GVS",
    7: "TEMPER_TANK",
    8: "LEGIONELLA_MODE",
    9: "STEP_LAST_HEATING",
    10: "HEATING_MODE",
    11: "GVS_MODE",
    12: "STEP_LAST_GVS",
    13: "P0_PHASE_MODE",
    14: "P1_SWITCH_PUMP",
    15: "P2_THREE_STROKE_VALVE",
    16: "STEP_SERVICE_MENU",
    17: "P4_MAX_POWER_HEAT",
    18: "P5_MAX_POWER_GVS",
    19: "P6_CONSUMER_PRIORITY",
    20: "P7_LIMIT_MAX_TEMPER_HEAT",
    21: "P8_LIMIT_MAX_TEMPER_TANK_GVS",
    22: "P9_LIMIT_MAX_TEMPER_BOILER_GVS",
    23: "LEGIONELLA_CYCLE",
    24: "ISSUE_YEAR",
    25: "ISSUE_MONTH",
    26: "ISSUE_DAY",
    27: "SERIES",
    28: "BRAND",
    29: "POWER",
    30: "POWER_FRACT",
    31: "STEND_NUMBER",
    32: "STEND_NUMBER_DIG_1",
    33: "STEND_NUMBER_DIG_2",
    34: "STEND_NUMBER_DIG_3",
    35: "STEND_NUMBER_DIG_4",
    36: "STEND_NUMBER_DIG_5",
    37: "SENSOR_BOILER_OUT",
    38: "SENSOR_TANK_GVS",
    39: "SENSOR_ROOM",
    40: "SENSOR_PP",
    41: "SENSOR_R",
    42: "STAT_PROG_OUT",
    43: "STAT_PROG_ROOM",
    44: "STAT_PROG_GVS",
}

# Reverse lookup: field name → index
INFO_FIELD_INDICES: dict[str, int] = {v: k for k, v in INFO_FIELD_NAMES.items()}

# INFO frame constants
INFO_FRAME_PREFIX = "I1&"
INFO_FRAME_TERMINATOR = "Z"
INFO_FRAME_FIELD_COUNT = 45  # fields 0..44 + checksum
INFO_FRAME_PARTS_COUNT = 47  # "I1" + 45 fields + "checksumZ"

# MCU responses
MCU_RESPONSE_OK = "OK"
MCU_RESPONSE_ER = "ER"
MCU_RESPONSE_GER = "GER"
MCU_RESPONSE_OER = "OER"

# Tasmota topic patterns
CMND_TOPIC_TEMPLATE = "cmnd/{topic}"
STAT_TOPIC_TEMPLATE = "stat/{topic}"
STAT_SERIAL_TOPIC_TEMPLATE = "stat/{topic}/serial"

# Tasmota rules we want in place on the boiler
TASMOTA_RULE1 = (
    "ON SerialReceived#Data DO Publish stat/{topic}/serial %value% ENDON"
)
TASMOTA_RULE2 = (
    "ON System#Boot DO RuleTimer1 30 ENDON "
    "ON Rules#Timer=1 DO Backlog SerialSend1 INFO; RuleTimer1 30 ENDON"
)
TASMOTA_POLL_INTERVAL_SECONDS = 30
TASMOTA_SERIAL_DELIMITER = 82  # 'R'

# After a write command, how long to wait before re-requesting INFO
# (in Tasmota Delay units of 100ms)
COMMAND_REFRESH_DELAY_UNITS = 10  # = 1 second
