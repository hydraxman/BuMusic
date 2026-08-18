#!/usr/bin/env python3
"""Download a BuMusic wheel from an index and run the clean-wheel smoke test."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def download_wheel(
    package: str,
    *,
    index_url: str,
    destination: Path,
    attempts: int,
    delay_seconds: float,
) -> Path:
    command = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--only-binary=:all:",
        "--no-deps",
        "--dest",
        str(destination),
        "--index-url",
        index_url,
        package,
    ]
    for attempt in range(1, attempts + 1):
        result = subprocess.run(command, check=False)
        if result.returncode == 0:
            break
        if attempt == attempts:
            raise SystemExit(f"Could not download {package!r} after {attempts} attempts")
        time.sleep(delay_seconds)

    wheels = list(destination.glob("bumusic-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"Expected one downloaded BuMusic wheel, found: {wheels}")
    return wheels[0]


def require_matching_wheel(downloaded: Path, expected: Path) -> None:
    if not expected.is_file():
        raise SystemExit(f"Expected wheel was not found: {expected}")
    with downloaded.open("rb") as downloaded_file:
        downloaded_digest = hashlib.file_digest(downloaded_file, "sha256").hexdigest()
    with expected.open("rb") as expected_file:
        expected_digest = hashlib.file_digest(expected_file, "sha256").hexdigest()
    if downloaded_digest != expected_digest:
        raise SystemExit(
            f"Published wheel does not match the built artifact: "
            f"{downloaded_digest} != {expected_digest}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", help="exact package requirement, for example bumusic==0.2.1")
    parser.add_argument("--index-url", required=True)
    parser.add_argument("--attempts", type=int, default=6)
    parser.add_argument("--delay-seconds", type=float, default=10.0)
    parser.add_argument("--expected-wheel", type=Path)
    args = parser.parse_args()
    if args.attempts < 1:
        parser.error("--attempts must be at least 1")
    if args.delay_seconds < 0:
        parser.error("--delay-seconds must not be negative")
    return args


def main() -> None:
    args = parse_args()
    with tempfile.TemporaryDirectory(prefix="bumusic-index-test-") as temporary:
        workspace = Path(temporary)
        wheel = download_wheel(
            args.package,
            index_url=args.index_url,
            destination=workspace,
            attempts=args.attempts,
            delay_seconds=args.delay_seconds,
        )
        if args.expected_wheel is not None:
            require_matching_wheel(wheel, args.expected_wheel.resolve())
        subprocess.run(
            [sys.executable, ROOT / "scripts" / "wheel_smoke.py", wheel],
            cwd=workspace,
            check=True,
        )


if __name__ == "__main__":
    main()
