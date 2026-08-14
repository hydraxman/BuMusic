import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from bumusic.export import export_all
from bumusic.models import NoteEvent


def test_export_all_writes_editable_and_rendered_artifacts(tmp_path: Path) -> None:
    events = [
        NoteEvent(60, "C4", 261.6256, 0.0, 0.0, 0.5, 1.0, 0.91),
        NoteEvent(62, "D4", 293.6648, 0.0, 0.5, 1.0, 1.0, 0.88),
    ]

    outputs = export_all(events, tmp_path, bpm=120.0)

    assert set(outputs) == {"json", "musicxml", "midi", "svg"}
    assert all(path.is_file() and path.stat().st_size > 50 for path in outputs.values())
    payload = json.loads(outputs["json"].read_text(encoding="utf-8"))
    assert payload[0]["pitch_hz"] == 261.6256
    root = ET.parse(outputs["musicxml"]).getroot()
    assert len(root.findall(".//note")) == 2
    assert outputs["midi"].read_bytes().startswith(b"MThd")
    assert "<svg" in outputs["svg"].read_text(encoding="utf-8")


def test_musicxml_splits_long_note_at_barline_with_ties(tmp_path: Path) -> None:
    events = [
        NoteEvent(60, "C4", 261.6256, 0.0, 0.0, 2.625, 5.25, 0.91),
    ]

    outputs = export_all(events, tmp_path, bpm=120.0)
    root = ET.parse(outputs["musicxml"]).getroot()
    measures = root.findall(".//measure")
    durations = [
        sum(int(value.text or "0") for value in measure.findall(".//duration"))
        for measure in measures
    ]

    assert durations == [16, 5]
    assert len(root.findall('.//tie[@type="start"]')) == 2
    assert len(root.findall('.//tie[@type="stop"]')) == 2


def test_musicxml_preserves_gaps_as_rests_and_writes_valid_tempo_direction(
    tmp_path: Path,
) -> None:
    events = [
        NoteEvent(60, "C4", 261.6256, 0.0, 0.0, 0.5, 1.0, 0.91),
        NoteEvent(62, "D4", 293.6648, 0.0, 2.0, 2.5, 1.0, 0.88),
    ]

    outputs = export_all(events, tmp_path, bpm=120.0)
    root = ET.parse(outputs["musicxml"]).getroot()
    durations = [
        sum(int(value.text or "0") for value in measure.findall(".//duration"))
        for measure in root.findall(".//measure")
    ]

    assert durations == [16, 4]
    assert len(root.findall(".//note/rest")) == 1
    assert root.find(".//direction/direction-type/metronome") is not None
    assert root.findtext(".//direction/direction-type/metronome/beat-unit") == "quarter"
    assert root.findtext(".//direction/direction-type/metronome/per-minute") == "120"


def test_export_rejects_bpm_that_cannot_be_encoded_in_midi(tmp_path: Path) -> None:
    events = [NoteEvent(60, "C4", 261.6256, 0.0, 0.0, 0.5, 1.0, 0.91)]

    with pytest.raises(ValueError, match="MIDI tempo"):
        export_all(events, tmp_path, bpm=1.0)
