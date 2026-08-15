"""Shared BuMusic data models."""

import math
from dataclasses import dataclass


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


@dataclass(frozen=True, slots=True)
class NoteEvent:
    midi: int
    name: str
    pitch_hz: float
    cents_offset: float
    start_seconds: float
    end_seconds: float
    duration_beats: float
    confidence: float

    def __post_init__(self) -> None:
        if isinstance(self.midi, bool) or not isinstance(self.midi, int):
            raise TypeError("midi must be an integer")
        if not 0 <= self.midi <= 127:
            raise ValueError("midi must be between 0 and 127")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")

        pitch_hz = _finite_number(self.pitch_hz, "pitch_hz")
        cents_offset = _finite_number(self.cents_offset, "cents_offset")
        start_seconds = _finite_number(self.start_seconds, "start_seconds")
        end_seconds = _finite_number(self.end_seconds, "end_seconds")
        duration_beats = _finite_number(self.duration_beats, "duration_beats")
        confidence = _finite_number(self.confidence, "confidence")

        if pitch_hz <= 0:
            raise ValueError("pitch_hz must be greater than zero")
        if not -50.0 <= cents_offset <= 50.0:
            raise ValueError("cents_offset must be between -50 and 50")
        expected_hz = 440.0 * 2.0 ** ((self.midi - 69 + cents_offset / 100.0) / 12.0)
        pitch_error_cents = abs(1200.0 * math.log2(pitch_hz / expected_hz))
        if pitch_error_cents > 0.5:
            raise ValueError("pitch_hz must match midi plus cents_offset within 0.5 cents")
        if start_seconds < 0:
            raise ValueError("start_seconds must not be negative")
        if end_seconds <= start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        if duration_beats <= 0:
            raise ValueError("duration_beats must be greater than zero")
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
