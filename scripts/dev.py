#!/usr/bin/env python3
"""Cross-platform development tasks for BuMusic.

Run with Python 3.12+ from PowerShell, cmd.exe, Bash, or zsh:
    python scripts/dev.py setup
    python scripts/dev.py test
    python scripts/dev.py build
    python scripts/dev.py demo
    python scripts/dev.py clean
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def venv_python(root: Path = ROOT, *, platform: str = os.name) -> Path:
    """Return the virtual-environment Python path for Windows or POSIX."""
    if platform == "nt":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def run(*command: str | Path, python: Path | None = None) -> None:
    """Run a command from the repository root and fail on non-zero exit."""
    executable = [str(part) for part in command]
    if python is not None:
        executable = [str(python), *executable]
    print(f"+ {subprocess.list2cmdline(executable)}", flush=True)
    subprocess.run(executable, cwd=ROOT, check=True)


def require_venv() -> Path:
    python = venv_python()
    if not python.is_file():
        raise SystemExit(
            "BuMusic virtual environment was not found. "
            "Run 'python scripts/dev.py setup' first."
        )
    return python


def clean_directories(*names: str) -> None:
    for name in names:
        shutil.rmtree(ROOT / name, ignore_errors=True)


def setup() -> None:
    # This standalone script can be launched before package metadata enforces Python 3.12.
    if sys.version_info < (3, 12):  # noqa: UP036
        raise SystemExit("BuMusic requires Python 3.12 or newer to create its environment.")
    run("-m", "venv", ROOT / ".venv", python=Path(sys.executable))
    python = require_venv()
    run("-m", "pip", "install", "--upgrade", "pip", python=python)
    run("-m", "pip", "install", "-e", ".[dev]", python=python)
    print(f"BuMusic development environment is ready: {ROOT / '.venv'}")


def lint() -> None:
    run("-m", "ruff", "check", "src", "tests", "scripts", python=require_venv())


def test() -> None:
    python = require_venv()
    run("-m", "ruff", "check", "src", "tests", "scripts", python=python)
    run("-m", "pytest", python=python)


def build() -> None:
    python = require_venv()
    clean_directories("build", "dist")
    run("-m", "build", python=python)
    distributions = list((ROOT / "dist").iterdir())
    run("-m", "twine", "check", "--strict", *distributions, python=python)
    wheels = list((ROOT / "dist").glob("bumusic-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"Expected exactly one wheel, found: {wheels}")
    run("-m", "pip", "install", "--force-reinstall", "--no-deps", wheels[0], python=python)
    run("-m", "bumusic.cli", "--version", python=python)
    print(f"Build artifacts: {ROOT / 'dist'}")


def demo() -> None:
    python = require_venv()
    audio = ROOT / ".demo" / "c-major-scale.wav"
    output = ROOT / ".demo" / "result"
    audio.parent.mkdir(parents=True, exist_ok=True)
    run("scripts/generate_demo.py", audio, python=python)
    run(
        "-m",
        "bumusic.cli",
        "transcribe",
        audio,
        "--out",
        output,
        "--bpm",
        "120",
        python=python,
    )
    print(f"Demo outputs: {output}")


def clean() -> None:
    clean_directories("build", "dist", ".demo")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=("setup", "lint", "test", "build", "demo", "clean"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tasks = {
        "setup": setup,
        "lint": lint,
        "test": test,
        "build": build,
        "demo": demo,
        "clean": clean,
    }
    tasks[args.task]()


if __name__ == "__main__":
    main()
