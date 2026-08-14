"""Export BuMusic note events to JSON, MusicXML, MIDI and SVG."""

import json
import math
import struct
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path

import verovio

from .models import NoteEvent
from .transcription import PITCH_CLASSES

DIVISIONS = 4
MIDI_PPQ = 480
MAX_MIDI_TEMPO_MICROSECONDS = 0xFFFFFF


def _midi_tempo_microseconds(bpm: float) -> int:
    if isinstance(bpm, bool) or not isinstance(bpm, (int, float)):
        raise TypeError("bpm must be a number")
    if not math.isfinite(float(bpm)) or bpm <= 0:
        raise ValueError("bpm must be a finite number greater than zero")
    microseconds = int(round(60_000_000 / bpm))
    if not 1 <= microseconds <= MAX_MIDI_TEMPO_MICROSECONDS:
        raise ValueError("bpm cannot be encoded as a three-byte MIDI tempo")
    return microseconds


def _pitch_xml(parent: ET.Element, midi: int) -> None:
    pitch = ET.SubElement(parent, "pitch")
    step, alter = PITCH_CLASSES[midi % 12]
    ET.SubElement(pitch, "step").text = step
    if alter:
        ET.SubElement(pitch, "alter").text = str(alter)
    ET.SubElement(pitch, "octave").text = str(midi // 12 - 1)


def _largest_notation(beats: float) -> tuple[float, str, int]:
    values = (
        (4.0, "whole", 0),
        (3.0, "half", 1),
        (2.0, "half", 0),
        (1.5, "quarter", 1),
        (1.0, "quarter", 0),
        (0.75, "eighth", 1),
        (0.5, "eighth", 0),
        (0.25, "16th", 0),
    )
    for value in values:
        if value[0] <= beats + 1e-9:
            return value
    raise ValueError("MusicXML duration must be at least a sixteenth note")


def write_musicxml(events: list[NoteEvent], path: Path, *, bpm: float) -> None:
    root = ET.Element("score-partwise", version="4.0")
    work = ET.SubElement(root, "work")
    ET.SubElement(work, "work-title").text = "BuMusic Transcription"
    part_list = ET.SubElement(root, "part-list")
    score_part = ET.SubElement(part_list, "score-part", id="P1")
    ET.SubElement(score_part, "part-name").text = "Voice"
    part = ET.SubElement(root, "part", id="P1")

    measure_number = 1
    beat_in_measure = 0.0
    measure = ET.SubElement(part, "measure", number=str(measure_number))
    attributes = ET.SubElement(measure, "attributes")
    ET.SubElement(attributes, "divisions").text = str(DIVISIONS)
    key = ET.SubElement(attributes, "key")
    ET.SubElement(key, "fifths").text = "0"
    time = ET.SubElement(attributes, "time")
    ET.SubElement(time, "beats").text = "4"
    ET.SubElement(time, "beat-type").text = "4"
    clef = ET.SubElement(attributes, "clef")
    ET.SubElement(clef, "sign").text = "G"
    ET.SubElement(clef, "line").text = "2"
    direction = ET.SubElement(measure, "direction", placement="above")
    direction_type = ET.SubElement(direction, "direction-type")
    metronome = ET.SubElement(direction_type, "metronome")
    ET.SubElement(metronome, "beat-unit").text = "quarter"
    ET.SubElement(metronome, "per-minute").text = f"{bpm:g}"
    ET.SubElement(direction, "sound", tempo=f"{bpm:g}")

    def render_duration(midi: int | None, total_beats: float) -> None:
        nonlocal beat_in_measure, measure, measure_number
        remaining = total_beats
        rendered = 0.0
        while remaining > 1e-9:
            if beat_in_measure >= 4.0 - 1e-9:
                measure_number += 1
                measure = ET.SubElement(part, "measure", number=str(measure_number))
                beat_in_measure = 0.0

            capacity = 4.0 - beat_in_measure
            notation_beats, note_type, dot_count = _largest_notation(
                min(remaining, capacity)
            )
            has_previous_fragment = rendered > 1e-9
            has_next_fragment = remaining - notation_beats > 1e-9

            note = ET.SubElement(measure, "note")
            if midi is None:
                ET.SubElement(note, "rest")
            else:
                _pitch_xml(note, midi)
            ET.SubElement(note, "duration").text = str(
                int(round(notation_beats * DIVISIONS))
            )
            if midi is not None and has_previous_fragment:
                ET.SubElement(note, "tie", type="stop")
            if midi is not None and has_next_fragment:
                ET.SubElement(note, "tie", type="start")
            ET.SubElement(note, "type").text = note_type
            for _ in range(dot_count):
                ET.SubElement(note, "dot")
            if midi is not None and (has_previous_fragment or has_next_fragment):
                notations = ET.SubElement(note, "notations")
                if has_previous_fragment:
                    ET.SubElement(notations, "tied", type="stop")
                if has_next_fragment:
                    ET.SubElement(notations, "tied", type="start")

            beat_in_measure += notation_beats
            rendered += notation_beats
            remaining -= notation_beats

    timeline_cursor = 0.0
    for event in sorted(events, key=lambda item: item.start_seconds):
        onset_beats = max(0.0, round(event.start_seconds * bpm / 60.0 * 4) / 4)
        if onset_beats > timeline_cursor + 1e-9:
            render_duration(None, onset_beats - timeline_cursor)
            timeline_cursor = onset_beats
        total_beats = max(0.25, round(event.duration_beats * 4) / 4)
        render_duration(event.midi, total_beats)
        timeline_cursor += total_beats

    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def _variable_length(value: int) -> bytes:
    buffer = value & 0x7F
    result = bytearray([buffer])
    while value >> 7:
        value >>= 7
        result.insert(0, (value & 0x7F) | 0x80)
    return bytes(result)


def write_original_timing_midi(
    events: list[NoteEvent],
    path: Path,
    *,
    bpm: float,
) -> None:
    microseconds = _midi_tempo_microseconds(bpm)
    messages: list[tuple[int, int, int]] = []
    ticks_per_second = MIDI_PPQ * bpm / 60.0
    for event in events:
        start_tick = max(0, int(round(event.start_seconds * ticks_per_second)))
        end_tick = max(start_tick + 1, int(round(event.end_seconds * ticks_per_second)))
        messages.append((start_tick, 0x90, event.midi))
        messages.append((end_tick, 0x80, event.midi))
    messages.sort(key=lambda item: (item[0], item[1] == 0x90))

    track = bytearray(b"\x00\xff\x51\x03" + microseconds.to_bytes(3, "big"))
    previous_tick = 0
    for tick, status, midi in messages:
        track += _variable_length(tick - previous_tick)
        track += bytes((status, midi, 96 if status == 0x90 else 0))
        previous_tick = tick
    track += b"\x00\xff\x2f\x00"
    path.write_bytes(
        b"MThd"
        + struct.pack(">IHHH", 6, 0, 1, MIDI_PPQ)
        + b"MTrk"
        + struct.pack(">I", len(track))
        + track
    )


def render_svg(musicxml_path: Path, svg_path: Path) -> None:
    toolkit = verovio.toolkit()
    toolkit.setOptions(
        {
            "pageWidth": 2100,
            "pageHeight": 900,
            "scale": 55,
            "adjustPageHeight": True,
            "footer": "none",
        }
    )
    if not toolkit.loadFile(str(musicxml_path)):
        raise RuntimeError("Verovio could not load generated MusicXML")
    svg_path.write_text(toolkit.renderToSVG(1), encoding="utf-8")


def export_all(
    events: list[NoteEvent],
    output_dir: str | Path,
    *,
    bpm: float,
) -> dict[str, Path]:
    if not events:
        raise ValueError("events must not be empty")
    _midi_tempo_microseconds(bpm)

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    outputs = {
        "json": destination / "notes.json",
        "musicxml": destination / "score.musicxml",
        "midi": destination / "original-timing.mid",
        "svg": destination / "score.svg",
    }
    outputs["json"].write_text(
        json.dumps([asdict(event) for event in events], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_musicxml(events, outputs["musicxml"], bpm=bpm)
    write_original_timing_midi(events, outputs["midi"], bpm=bpm)
    render_svg(outputs["musicxml"], outputs["svg"])
    return outputs
