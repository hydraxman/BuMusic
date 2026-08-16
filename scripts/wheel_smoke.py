#!/usr/bin/env python3
"""Install a built wheel into a clean venv and run a real transcription smoke test."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

EXPECTED_OUTPUTS = {
    "notes.json",
    "score.musicxml",
    "original-timing.mid",
    "score.svg",
    "reconstructed-original-timing.wav",
}


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


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    wheels = [args.wheel] if args.wheel else list((root / "dist").glob("bumusic-*.whl"))
    if len(wheels) != 1 or wheels[0] is None or not wheels[0].is_file():
        raise SystemExit(f"Expected exactly one wheel, found: {wheels}")
    wheel = wheels[0].resolve()

    with tempfile.TemporaryDirectory(prefix="bumusic-wheel-test-") as temporary:
        workspace = Path(temporary)
        environment = workspace / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment_python(environment)
        cli = environment_cli(environment)
        subprocess.run([python, "-m", "pip", "install", str(wheel)], check=True)

        audio = workspace / "c-major.wav"
        output = workspace / "result"
        subprocess.run([sys.executable, root / "scripts/generate_demo.py", audio], check=True)
        subprocess.run(
            [
                cli,
                "transcribe",
                audio,
                "--out",
                output,
                "--bpm",
                "120",
            ],
            check=True,
        )
        produced = {path.name for path in output.iterdir()}
        missing = EXPECTED_OUTPUTS - produced
        if missing:
            raise SystemExit(f"Wheel smoke test is missing outputs: {sorted(missing)}")
        print(f"Wheel smoke test passed: {wheel.name}")


if __name__ == "__main__":
    main()
