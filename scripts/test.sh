#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

.venv/bin/ruff check src tests scripts
PYTHONPATH=src .venv/bin/python -m pytest
