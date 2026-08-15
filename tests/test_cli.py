import json
import math
import struct
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import soundfile as sf


def write_tone(path: Path, frequency: float = 440.0) -> None:
    sample_rate = 22_050
    with wave.open(str(path), "w") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        for index in range(int(sample_rate * 0.6)):
            value = int(0.3 * 32_767 * math.sin(2 * math.pi * frequency * index / sample_rate))
            audio.writeframesraw(struct.pack("<h", value))


def write_notes(path: Path) -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "midi": 45,
                    "name": "A2",
                    "pitch_hz": 110.0,
                    "cents_offset": 0.0,
                    "start_seconds": 0.1,
                    "end_seconds": 0.7,
                    "duration_beats": 1.25,
                    "confidence": 0.9,
                },
                {
                    "midi": 52,
                    "name": "E3",
                    "pitch_hz": 164.813778,
                    "cents_offset": 0.0,
                    "start_seconds": 0.8,
                    "end_seconds": 1.3,
                    "duration_beats": 1.0,
                    "confidence": 0.88,
                },
            ]
        ),
        encoding="utf-8",
    )


def test_cli_transcribe_creates_complete_output_bundle(tmp_path: Path) -> None:
    source = tmp_path / "a4.wav"
    output = tmp_path / "result"
    write_tone(source)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "bumusic.cli",
            "transcribe",
            str(source),
            "--out",
            str(output),
            "--bpm",
            "120",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert '"notes": ["A4"]' in completed.stdout
    for name in (
        "notes.json",
        "score.musicxml",
        "original-timing.mid",
        "score.svg",
        "reconstructed-original-timing.wav",
    ):
        assert (output / name).is_file(), name


def test_cli_transcribe_accepts_instrument_for_reconstructed_audio(tmp_path: Path) -> None:
    source = tmp_path / "a4.wav"
    output = tmp_path / "result"
    write_tone(source)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "bumusic.cli",
            "transcribe",
            str(source),
            "--out",
            str(output),
            "--instrument",
            "electric-guitar",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["instrument"] == "electric-guitar"
    assert (output / "reconstructed-original-timing.wav").is_file()


def test_cli_reports_version() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "bumusic.cli", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout.strip() == "bumusic 0.2.0"


def test_cli_reports_invalid_notes_json_without_traceback(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text('[{"midi": 60}]', encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, "-m", "bumusic.cli", "synthesize", str(invalid)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert completed.stderr.startswith("bumusic:")
    assert "Traceback" not in completed.stderr


def test_cli_rejects_non_finite_bpm_without_traceback(tmp_path: Path) -> None:
    source = tmp_path / "a4.wav"
    write_tone(source)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "bumusic.cli",
            "transcribe",
            str(source),
            "--bpm",
            "inf",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert completed.stderr.startswith("bumusic:")
    assert "Traceback" not in completed.stderr


def test_cli_synthesize_aligns_low_voice_to_middle_c_with_piano(tmp_path: Path) -> None:
    notes = tmp_path / "notes.json"
    output = tmp_path / "middle-c-piano.wav"
    write_notes(notes)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "bumusic.cli",
            "synthesize",
            str(notes),
            "--output",
            str(output),
            "--instrument",
            "piano",
            "--align-middle-c",
            "--snap-to-equal-temperament",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert output.is_file()
    audio, sample_rate = sf.read(output)
    segment = audio[int(0.12 * sample_rate) : int(0.62 * sample_rate)]
    frequencies = np.fft.rfftfreq(len(segment), 1 / sample_rate)
    dominant = frequencies[np.argmax(np.abs(np.fft.rfft(segment)))]
    assert abs(dominant - 261.625565) < 5.0


def test_cli_synthesize_renders_multiple_target_major_keys(tmp_path: Path) -> None:
    notes = tmp_path / "notes.json"
    output = tmp_path / "violin.wav"
    write_notes(notes)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "bumusic.cli",
            "synthesize",
            str(notes),
            "--output",
            str(output),
            "--instrument",
            "violin",
            "--source-key",
            "A",
            "--target-key",
            "C",
            "--target-key",
            "D",
            "--target-octave",
            "4",
            "--snap-to-equal-temperament",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["instrument"] == "violin"
    assert set(payload["renders"]) == {"C major", "D major"}
    assert payload["renders"]["C major"]["semitones"] == 15
    assert payload["renders"]["D major"]["semitones"] == 17
    assert (tmp_path / "violin-c-major.wav").is_file()
    assert (tmp_path / "violin-d-major.wav").is_file()


def test_cli_prevalidates_all_target_keys_before_writing(tmp_path: Path) -> None:
    notes = tmp_path / "notes.json"
    write_notes(notes)
    payload = json.loads(notes.read_text(encoding="utf-8"))
    payload.append(
        {
            "midi": 111,
            "name": "D#8",
            "pitch_hz": 440.0 * 2.0 ** ((111 - 69) / 12.0),
            "cents_offset": 0.0,
            "start_seconds": 1.4,
            "end_seconds": 1.8,
            "duration_beats": 0.75,
            "confidence": 0.8,
        }
    )
    notes.write_text(json.dumps(payload), encoding="utf-8")
    output = tmp_path / "batch.wav"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "bumusic.cli",
            "synthesize",
            str(notes),
            "--output",
            str(output),
            "--source-key",
            "A",
            "--target-key",
            "C",
            "--target-key",
            "D",
            "--target-octave",
            "4",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "MIDI range" in completed.stderr
    assert not (tmp_path / "batch-c-major.wav").exists()
    assert not (tmp_path / "batch-d-major.wav").exists()


def test_cli_synthesize_rejects_target_key_without_source_key(tmp_path: Path) -> None:
    notes = tmp_path / "notes.json"
    write_notes(notes)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "bumusic.cli",
            "synthesize",
            str(notes),
            "--target-key",
            "C",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "--source-key" in completed.stderr
    assert "Traceback" not in completed.stderr
