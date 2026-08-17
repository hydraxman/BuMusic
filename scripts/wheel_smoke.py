#!/usr/bin/env python3
"""Install a built wheel into a clean venv and run a real transcription smoke test."""

from __future__ import annotations

import argparse
import json
import math
import os
import struct
import subprocess
import tempfile
import venv
import wave
from pathlib import Path

EXPECTED_OUTPUTS = {
    "notes.json",
    "score.musicxml",
    "original-timing.mid",
    "score.svg",
    "reconstructed-original-timing.wav",
}
EXPECTED_NOTES = ("C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5")
NOTE_FREQUENCIES = (
    261.6256,
    293.6648,
    329.6276,
    349.2282,
    391.9954,
    440.0,
    493.8833,
    523.2511,
)


def environment_python(environment: Path, *, platform: str = os.name) -> Path:
    if platform == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def environment_cli(environment: Path, *, platform: str = os.name) -> Path:
    if platform == "nt":
        return environment / "Scripts" / "bumusic.exe"
    return environment / "bin" / "bumusic"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", nargs="?", type=Path)
    return parser.parse_args()


def generate_audio(path: Path) -> None:
    sample_rate = 22_050
    with wave.open(str(path), "w") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        for frequency in NOTE_FREQUENCIES:
            for index in range(int(sample_rate * 0.45)):
                envelope = min(
                    1.0,
                    index / (sample_rate * 0.02),
                    (sample_rate * 0.45 - index) / (sample_rate * 0.03),
                )
                value = int(
                    0.35
                    * 32_767
                    * envelope
                    * math.sin(2 * math.pi * frequency * index / sample_rate)
                )
                audio.writeframesraw(struct.pack("<h", value))
            audio.writeframesraw(b"\x00\x00" * int(sample_rate * 0.05))


def isolated_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def run_wheel_smoke(wheel: Path) -> None:
    wheel = wheel.resolve()
    if not wheel.is_file():
        raise SystemExit(f"Wheel was not found: {wheel}")

    with tempfile.TemporaryDirectory(prefix="bumusic-wheel-test-") as temporary:
        workspace = Path(temporary)
        environment = workspace / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment_python(environment)
        cli = environment_cli(environment)
        process_environment = isolated_environment()
        subprocess.run(
            [
                python,
                "-m",
                "pip",
                "install",
                "--only-binary=:all:",
                str(wheel),
            ],
            cwd=workspace,
            env=process_environment,
            check=True,
        )

        audio = workspace / "c-major.wav"
        output = workspace / "result"
        generate_audio(audio)
        version_result = subprocess.run(
            [cli, "--version"],
            cwd=workspace,
            env=process_environment,
            check=True,
            capture_output=True,
            text=True,
        )
        if not version_result.stdout.startswith("bumusic "):
            raise SystemExit(f"Unexpected CLI version output: {version_result.stdout!r}")
        transcription = subprocess.run(
            [
                cli,
                "transcribe",
                audio,
                "--out",
                output,
                "--bpm",
                "120",
            ],
            cwd=workspace,
            env=process_environment,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(transcription.stdout)
        if tuple(payload["notes"]) != EXPECTED_NOTES:
            raise SystemExit(f"Unexpected transcription: {payload['notes']}")
        produced = {path.name for path in output.iterdir()}
        missing = EXPECTED_OUTPUTS - produced
        if missing:
            raise SystemExit(f"Wheel smoke test is missing outputs: {sorted(missing)}")
        empty = sorted(
            name for name in EXPECTED_OUTPUTS if (output / name).stat().st_size == 0
        )
        if empty:
            raise SystemExit(f"Wheel smoke test produced empty outputs: {empty}")
        print(f"Wheel smoke test passed: {wheel.name}")


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    wheels = [args.wheel] if args.wheel else list((root / "dist").glob("bumusic-*.whl"))
    if len(wheels) != 1 or wheels[0] is None:
        raise SystemExit(f"Expected exactly one wheel, found: {wheels}")
    run_wheel_smoke(wheels[0])


if __name__ == "__main__":
    main()
