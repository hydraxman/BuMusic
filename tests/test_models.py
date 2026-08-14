import math

import pytest

from bumusic.models import NoteEvent


def valid_event(**overrides: object) -> NoteEvent:
    values: dict[str, object] = {
        "midi": 60,
        "name": "C4",
        "pitch_hz": 261.6256,
        "cents_offset": 0.0,
        "start_seconds": 0.0,
        "end_seconds": 0.5,
        "duration_beats": 1.0,
        "confidence": 0.9,
    }
    values.update(overrides)
    return NoteEvent(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("midi", -1),
        ("midi", 128),
        ("pitch_hz", 0.0),
        ("pitch_hz", math.nan),
        ("start_seconds", -0.1),
        ("end_seconds", math.inf),
        ("end_seconds", 0.0),
        ("duration_beats", 0.0),
        ("confidence", 1.1),
    ],
)
def test_note_event_rejects_invalid_values(field: str, value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        valid_event(**{field: value})
