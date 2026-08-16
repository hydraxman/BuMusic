from __future__ import annotations

import math

import pytest

from bumusic.models import NoteEvent
from bumusic.pitch import (
    align_first_note_to_middle_c,
    parse_pitch_class,
    transpose_events,
    transpose_to_key,
)


def event(midi: int, name: str, hz: float, *, cents: float = 0.0) -> NoteEvent:
    return NoteEvent(
        midi=midi,
        name=name,
        pitch_hz=hz,
        cents_offset=cents,
        start_seconds=0.25,
        end_seconds=0.75,
        duration_beats=1.0,
        confidence=0.9,
    )


def test_transpose_events_preserves_timing_and_relative_tuning() -> None:
    source = [event(45, "A2", 111.278, cents=20.0)]

    result = transpose_events(source, 12)

    assert result[0].midi == 57
    assert result[0].name == "A3"
    assert result[0].pitch_hz == pytest.approx(222.556, rel=1e-6)
    assert result[0].cents_offset == pytest.approx(20.0)
    assert result[0].start_seconds == source[0].start_seconds
    assert result[0].end_seconds == source[0].end_seconds


def test_transpose_events_can_snap_to_equal_temperament() -> None:
    source = [event(45, "A2", 111.278, cents=20.0)]

    result = transpose_events(source, 12, snap_to_equal_temperament=True)

    assert result[0].midi == 57
    assert result[0].pitch_hz == pytest.approx(220.0)
    assert result[0].cents_offset == 0.0


def test_align_first_note_to_middle_c_lifts_low_voice() -> None:
    source = [event(45, "A2", 110.0), event(52, "E3", 164.813778)]

    result, semitones = align_first_note_to_middle_c(source)

    assert semitones == 15
    assert [item.name for item in result] == ["C4", "G4"]
    assert result[0].midi == 60


def test_transpose_to_key_maps_source_tonic_to_target_octave() -> None:
    source = [event(45, "A2", 110.0), event(52, "E3", 164.813778)]

    result, semitones = transpose_to_key(
        source,
        source_key="A",
        target_key="D",
        target_octave=4,
        snap_to_equal_temperament=True,
    )

    assert semitones == 17
    assert [item.name for item in result] == ["D4", "A4"]
    assert result[0].pitch_hz == pytest.approx(293.664768, rel=1e-6)


def test_parse_pitch_class_accepts_sharps_and_flats() -> None:
    assert parse_pitch_class("C") == 0
    assert parse_pitch_class("C#") == 1
    assert parse_pitch_class("Db") == 1
    assert parse_pitch_class("B♭") == 10


def test_transpose_rejects_midi_overflow() -> None:
    source = [event(120, "C9", 8372.018)]

    with pytest.raises(ValueError, match="MIDI range"):
        transpose_events(source, 12)


def test_transpose_rejects_extreme_shift_without_numeric_overflow() -> None:
    source = [event(60, "C4", 261.625565)]

    with pytest.raises(ValueError, match="MIDI range"):
        transpose_events(source, 10**9)


def test_transpose_to_key_requires_source_tonic_in_events() -> None:
    source = [event(48, "C3", 130.812783)]

    with pytest.raises(ValueError, match="source tonic"):
        transpose_to_key(source, source_key="A", target_key="C", target_octave=4)


def test_parse_pitch_class_rejects_invalid_key() -> None:
    with pytest.raises(ValueError, match="key"):
        parse_pitch_class("H")


def test_frequency_relation_is_one_octave() -> None:
    source = [event(45, "A2", 110.0)]
    result = transpose_events(source, 12)
    assert math.isclose(result[0].pitch_hz / source[0].pitch_hz, 2.0)
