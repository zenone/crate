.PHONY: setup test lint format verify web

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -U pip && pip install -e '.[dev]'

test:
	. .venv/bin/activate && pytest -q

lint:
	. .venv/bin/activate && ruff check .

format:
	. .venv/bin/activate && ruff format .

verify:
	./scripts/verify.sh

web:
	./start_crate_web.sh
