import os
import subprocess
import sys
from pathlib import Path

from scripts import dev, wheel_smoke


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
