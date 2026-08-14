import math
import struct
import subprocess
import sys
import wave
from pathlib import Path


def write_tone(path: Path, frequency: float = 440.0) -> None:
    sample_rate = 22_050
    with wave.open(str(path), "w") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        for index in range(int(sample_rate * 0.6)):
            value = int(0.3 * 32_767 * math.sin(2 * math.pi * frequency * index / sample_rate))
            audio.writeframesraw(struct.pack("<h", value))


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


def test_cli_reports_version() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "bumusic.cli", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout.strip() == "bumusic 0.1.1"


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
