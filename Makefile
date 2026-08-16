PYTHON ?= python3

.PHONY: setup test lint build demo clean

setup:
	$(PYTHON) scripts/dev.py setup

test:
	$(PYTHON) scripts/dev.py test

lint:
	$(PYTHON) scripts/dev.py lint

build:
	$(PYTHON) scripts/dev.py build

demo:
	$(PYTHON) scripts/dev.py demo

clean:
	$(PYTHON) scripts/dev.py clean
