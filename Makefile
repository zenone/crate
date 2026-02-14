.PHONY: help setup test lint format verify clean web

help:
	@echo "Crate - DJ MP3 Renaming Tool"
	@echo ""
	@echo "Common targets:"
	@echo "  make setup   - create venv and install deps"
	@echo "  make test    - run pytest"
	@echo "  make lint    - run ruff + mypy"
	@echo "  make format  - auto-format with ruff"
	@echo "  make verify  - full quality gate (lint + test)"
	@echo "  make web     - start web UI"
	@echo "  make clean   - remove build artifacts"

setup:
	python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"
	@echo "✅ Setup complete. Activate with: source .venv/bin/activate"

test:
	.venv/bin/pytest tests/ -q

lint:
	.venv/bin/ruff check crate web tests
	.venv/bin/mypy crate web --config-file pyproject.toml

format:
	.venv/bin/ruff check --fix crate web tests
	.venv/bin/ruff format crate web tests

verify: lint test
	@echo "✅ All checks passed"

web:
	./crate-web.sh

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned build artifacts"
