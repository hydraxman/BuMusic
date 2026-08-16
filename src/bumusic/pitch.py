"""Pitch transposition and key-targeting helpers."""

from __future__ import annotations

from dataclasses import replace

from .models import NoteEvent
from .transcription import midi_name

_KEY_ALIASES = {
    "C": 0,
    "B#": 0,
    "C#": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "EB": 3,
    "E": 4,
    "FB": 4,
    "E#": 5,
    "F": 5,
    "F#": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "BB": 10,
    "B": 11,
    "CB": 11,
}


def parse_pitch_class(key: str) -> int:
    """Parse a major-key tonic name into a pitch class."""
    if not isinstance(key, str) or not key.strip():
        raise ValueError("key must be a non-empty note name")
    normalized = key.strip().replace("♯", "#").replace("♭", "b").upper()
    try:
        return _KEY_ALIASES[normalized]
    except KeyError as error:
        raise ValueError(f"unsupported key: {key}") from error


def _equal_tempered_hz(midi: int) -> float:
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def transpose_events(
    events: list[NoteEvent],
    semitones: int,
    *,
    snap_to_equal_temperament: bool = False,
) -> list[NoteEvent]:
    """Transpose a melody while preserving original timing and confidence."""
    if not events:
        raise ValueError("events must not be empty")
    if isinstance(semitones, bool) or not isinstance(semitones, int):
        raise TypeError("semitones must be an integer")

    target_midis = [event.midi + semitones for event in events]
    if any(not 0 <= target_midi <= 127 for target_midi in target_midis):
        raise ValueError("transposition exceeds the MIDI range")

    result: list[NoteEvent] = []
    frequency_ratio = 2.0 ** (semitones / 12.0)
    for event, target_midi in zip(events, target_midis, strict=True):
        result.append(
            replace(
                event,
                midi=target_midi,
                name=midi_name(target_midi),
                pitch_hz=(
                    _equal_tempered_hz(target_midi)
                    if snap_to_equal_temperament
                    else event.pitch_hz * frequency_ratio
                ),
                cents_offset=0.0 if snap_to_equal_temperament else event.cents_offset,
            )
        )
    return result


def align_first_note_to_middle_c(
    events: list[NoteEvent],
    *,
    snap_to_equal_temperament: bool = False,
) -> tuple[list[NoteEvent], int]:
    """Move the first detected note to middle C (C4/MIDI 60)."""
    if not events:
        raise ValueError("events must not be empty")
    semitones = 60 - events[0].midi
    return (
        transpose_events(
            events,
            semitones,
            snap_to_equal_temperament=snap_to_equal_temperament,
        ),
        semitones,
    )


def transpose_to_key(
    events: list[NoteEvent],
    *,
    source_key: str,
    target_key: str,
    target_octave: int = 4,
    snap_to_equal_temperament: bool = False,
) -> tuple[list[NoteEvent], int]:
    """Map the first source tonic to a target major-key tonic and octave."""
    if not events:
        raise ValueError("events must not be empty")
    if isinstance(target_octave, bool) or not isinstance(target_octave, int):
        raise TypeError("target_octave must be an integer")

    source_pitch_class = parse_pitch_class(source_key)
    target_pitch_class = parse_pitch_class(target_key)
    source_tonic = next(
        (event for event in events if event.midi % 12 == source_pitch_class),
        None,
    )
    if source_tonic is None:
        raise ValueError(f"source tonic {source_key} is not present in the events")

    target_midi = (target_octave + 1) * 12 + target_pitch_class
    if not 0 <= target_midi <= 127:
        raise ValueError("target key octave exceeds the MIDI range")
    semitones = target_midi - source_tonic.midi
    return (
        transpose_events(
            events,
            semitones,
            snap_to_equal_temperament=snap_to_equal_temperament,
        ),
        semitones,
    )
