#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p .demo
.venv/bin/python scripts/generate_demo.py .demo/c-major-scale.wav
.venv/bin/bumusic transcribe .demo/c-major-scale.wav --out .demo/result --bpm 120

echo "Demo outputs: $ROOT/.demo/result"
