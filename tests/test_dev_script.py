import os
import subprocess
import sys
import wave
from pathlib import Path

import pytest

from scripts import dev, index_smoke, release_version, wheel_smoke


def test_venv_python_uses_windows_scripts_directory() -> None:
    assert dev.venv_python(Path("repo"), platform="nt") == Path(
        "repo/.venv/Scripts/python.exe"
    )


def test_venv_python_uses_posix_bin_directory() -> None:
    assert dev.venv_python(Path("repo"), platform="posix") == Path("repo/.venv/bin/python")


def test_wheel_smoke_uses_windows_scripts_directory() -> None:
    assert wheel_smoke.environment_python(Path("venv"), platform="nt") == Path(
        "venv/Scripts/python.exe"
    )


def test_wheel_smoke_uses_posix_bin_directory() -> None:
    assert wheel_smoke.environment_python(Path("venv"), platform="posix") == Path(
        "venv/bin/python"
    )


def test_wheel_smoke_uses_windows_cli_entrypoint() -> None:
    assert wheel_smoke.environment_cli(Path("venv"), platform="nt") == Path(
        "venv/Scripts/bumusic.exe"
    )


def test_wheel_smoke_uses_posix_cli_entrypoint() -> None:
    assert wheel_smoke.environment_cli(Path("venv"), platform="posix") == Path(
        "venv/bin/bumusic"
    )


def test_wheel_smoke_generates_standalone_audio(tmp_path: Path) -> None:
    audio = tmp_path / "scale.wav"

    wheel_smoke.generate_audio(audio)

    with wave.open(str(audio), "rb") as generated:
        assert generated.getnchannels() == 1
        assert generated.getframerate() == 22_050
        assert generated.getnframes() > 0


def test_wheel_smoke_removes_pythonpath(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTHONPATH", "source-checkout")

    environment = wheel_smoke.isolated_environment()

    assert "PYTHONPATH" not in environment
    assert environment["PYTHONNOUSERSITE"] == "1"


def test_release_tag_must_match_project_version(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "bumusic"\nversion = "1.2.3"\n',
        encoding="utf-8",
    )

    assert release_version.validate_release_tag("v1.2.3", root=tmp_path) == "1.2.3"
    with pytest.raises(ValueError, match="does not match"):
        release_version.validate_release_tag("v1.2.4", root=tmp_path)


def test_index_smoke_retries_and_returns_downloaded_wheel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    attempts = 0
    delays: list[float] = []

    def fake_run(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            (tmp_path / "bumusic-1.2.3-py3-none-any.whl").touch()
        return subprocess.CompletedProcess(command, 0 if attempts == 2 else 1)

    monkeypatch.setattr(index_smoke.subprocess, "run", fake_run)
    monkeypatch.setattr(index_smoke.time, "sleep", delays.append)

    wheel = index_smoke.download_wheel(
        "bumusic==1.2.3",
        index_url="https://packages.example/simple/",
        destination=tmp_path,
        attempts=2,
        delay_seconds=0.25,
    )

    assert wheel.name == "bumusic-1.2.3-py3-none-any.whl"
    assert attempts == 2
    assert delays == [0.25]


def test_index_smoke_rejects_a_different_published_wheel(tmp_path: Path) -> None:
    downloaded = tmp_path / "downloaded.whl"
    expected = tmp_path / "expected.whl"
    downloaded.write_bytes(b"published")
    expected.write_bytes(b"built")

    with pytest.raises(SystemExit, match="does not match"):
        index_smoke.require_matching_wheel(downloaded, expected)


def test_dev_help_runs_with_the_current_python() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/dev.py", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "setup" in completed.stdout
    assert "demo" in completed.stdout


def test_runtime_platform_is_supported() -> None:
    assert os.name in {"nt", "posix"}
