.PHONY: setup test lint build demo clean

setup:
	./scripts/setup.sh

test:
	.venv/bin/python -m pytest

lint:
	.venv/bin/ruff check src tests scripts

build:
	./scripts/build.sh

demo:
	./scripts/demo.sh

clean:
	.venv/bin/python -c "from pathlib import Path; import shutil; [shutil.rmtree(p, ignore_errors=True) for p in (Path('build'), Path('dist'), Path('.demo'))]"
