#!/usr/bin/env python3
"""Validate that a release tag matches the project version."""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def project_version(root: Path = ROOT) -> str:
    with (root / "pyproject.toml").open("rb") as project_file:
        project = tomllib.load(project_file)
    version = project["project"]["version"]
    if not isinstance(version, str) or not version:
        raise ValueError("project.version must be a non-empty string")
    return version


def validate_release_tag(tag: str, *, root: Path = ROOT) -> str:
    version = project_version(root)
    expected = f"v{version}"
    if tag != expected:
        raise ValueError(f"release tag {tag!r} does not match project version {expected!r}")
    return version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    args = parser.parse_args()
    try:
        print(validate_release_tag(args.tag))
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
