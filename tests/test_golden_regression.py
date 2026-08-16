from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from bumusic.transcription import transcribe_audio

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "golden"
GOLDEN_FIXTURES = ("voice-balanced-001", "voice-balanced-002")


@pytest.mark.golden
@pytest.mark.parametrize("fixture_id", GOLDEN_FIXTURES)
def test_selected_voice_transcription_matches_golden_baseline(fixture_id: str) -> None:
    fixture = FIXTURE_ROOT / fixture_id
    metadata = json.loads((fixture / "metadata.json").read_text(encoding="utf-8"))
    audio = fixture / "input.ogg"
    expected = json.loads((fixture / "expected-notes.json").read_text(encoding="utf-8"))

    assert hashlib.sha256(audio.read_bytes()).hexdigest() == metadata["audio_sha256"]
    expected_canonical = json.dumps(expected, indent=2).encode("utf-8")
    assert hashlib.sha256(expected_canonical).hexdigest() == metadata["expected_notes_sha256"]
    assert len(expected) == metadata["expected_note_count"]
    actual = [asdict(event) for event in transcribe_audio(audio, bpm=metadata["bpm"])]

    assert [event["midi"] for event in actual] == [event["midi"] for event in expected]
    assert [event["name"] for event in actual] == [event["name"] for event in expected]
    assert [event["duration_beats"] for event in actual] == [
        event["duration_beats"] for event in expected
    ]

    actual_anchor = actual[0]["start_seconds"]
    expected_anchor = expected[0]["start_seconds"]
    timing_tolerance = metadata["relative_timing_tolerance_seconds"]
    for observed, golden in zip(actual, expected, strict=True):
        assert observed["pitch_hz"] == pytest.approx(
            golden["pitch_hz"], abs=metadata["pitch_tolerance_hz"]
        )
        assert observed["cents_offset"] == pytest.approx(
            golden["cents_offset"], abs=metadata["cents_tolerance"]
        )
        assert observed["confidence"] == pytest.approx(
            golden["confidence"], abs=metadata["confidence_tolerance"]
        )
        assert observed["start_seconds"] - actual_anchor == pytest.approx(
            golden["start_seconds"] - expected_anchor,
            abs=timing_tolerance,
        )
        assert observed["end_seconds"] - observed["start_seconds"] == pytest.approx(
            golden["end_seconds"] - golden["start_seconds"],
            abs=timing_tolerance,
        )
