"""Serial protocol for Teknix ESPRO boilers.

The ESP8266 (Tasmota) talks to the boiler MCU over UART at 115200 8N1.

Read side (INFO):
    Send:    INFO
    Receive: I1&<f0>&<f1>&...&<f44>&<chk>Z
    Checksum: sum(f0..f44) + 1

Write side (T-command, single field):
    Send:    T<index><2-digit value><"00" padding><2-digit checksum>Z
    Receive: OK   (or ER on checksum/value error, GER on wrong field count)
    Where index = INFO field index + 2, and checksum = sum of all individual
    digits in the data portion.
"""

from __future__ import annotations

from dataclasses import dataclass

from .const import (
    INFO_FIELD_NAMES,
    INFO_FRAME_FIELD_COUNT,
    INFO_FRAME_PARTS_COUNT,
    INFO_FRAME_PREFIX,
    INFO_FRAME_TERMINATOR,
)


@dataclass(frozen=True)
class BoilerState:
    """Parsed INFO frame.

    `fields` is indexed by INFO field number (0..44).
    `named` exposes the same values by APK-derived field name.
    """

    fields: tuple[int, ...]
    checksum: int
    named: dict[str, int]

    @classmethod
    def from_frame(cls, raw: str) -> BoilerState | None:
        """Parse an `I1&...Z` frame. Returns None on any validation failure."""
        if not raw:
            return None
        if not raw.startswith(INFO_FRAME_PREFIX) or not raw.endswith(INFO_FRAME_TERMINATOR):
            return None

        parts = raw.split("&")
        if len(parts) != INFO_FRAME_PARTS_COUNT:
            return None

        try:
            fields = tuple(int(p) for p in parts[1 : 1 + INFO_FRAME_FIELD_COUNT])
            checksum = int(parts[-1].rstrip(INFO_FRAME_TERMINATOR))
        except ValueError:
            return None

        if sum(fields) + 1 != checksum:
            return None  # corrupt frame

        named = {
            INFO_FIELD_NAMES[i]: fields[i]
            for i in range(INFO_FRAME_FIELD_COUNT)
            if i in INFO_FIELD_NAMES
        }
        return cls(fields=fields, checksum=checksum, named=named)

    def __getitem__(self, key: int | str) -> int:
        if isinstance(key, int):
            return self.fields[key]
        return self.named[key]

    def get(self, key: int | str, default: int | None = None) -> int | None:
        try:
            return self[key]
        except (IndexError, KeyError):
            return default


def _digit_sum(text: str) -> int:
    """Sum of all individual digits in `text` (non-digits are ignored)."""
    return sum(int(c) for c in text if c.isdigit())


def build_t_command(field_index: int, value: int) -> str:
    """Build a T-command that writes `value` to INFO field `field_index`.

    Format: T<idx+2><value 2d><00 pad><digit-sum checksum 2d>Z
    """
    if not 0 <= field_index <= 99:
        raise ValueError(f"Field index {field_index} out of range")
    if not 0 <= value <= 99:
        raise ValueError(f"Value {value} out of T-command 2-digit range")

    data = f"{field_index + 2:02d}{value:02d}00"
    chk = _digit_sum(data)
    return f"T{data}{chk:02d}Z"


def build_backlog_payload(t_command: str, refresh_delay_units: int = 10) -> str:
    """Build a Tasmota Backlog payload: send T-command then request fresh INFO.

    `refresh_delay_units` is in Tasmota Delay units (100ms each). Default 10 = 1s.
    """
    return f"SerialSend {t_command}; Delay {refresh_delay_units}; SerialSend1 INFO"
