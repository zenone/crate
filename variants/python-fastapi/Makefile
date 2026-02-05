.PHONY: setup test lint format run

VENV?=.venv
PY?=$(VENV)/bin/python
PIP?=$(VENV)/bin/pip

setup:
	python3 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -e .
	$(PIP) install -r requirements-dev.txt

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check .

format:
	$(PY) -m ruff format .

run:
	$(VENV)/bin/uvicorn app.main:app --reload
