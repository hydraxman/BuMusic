#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

.venv/bin/python -c "from pathlib import Path; import shutil; [shutil.rmtree(path, ignore_errors=True) for path in (Path('build'), Path('dist'))]"
.venv/bin/python -m build
WHEEL="$(.venv/bin/python -c "from pathlib import Path; wheels=list(Path('dist').glob('bumusic-*.whl')); assert len(wheels) == 1, wheels; print(wheels[0])")"
.venv/bin/python -m pip install --force-reinstall --no-deps "$WHEEL"
.venv/bin/bumusic --version

echo "Build artifacts: $ROOT/dist"
