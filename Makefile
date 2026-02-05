.PHONY: help setup test lint format verify

help:
	@echo "Common targets:"
	@echo "  make setup   - install deps / bootstrap (project-specific)"
	@echo "  make test    - run tests"
	@echo "  make lint    - run lint/static checks"
	@echo "  make format  - auto-format"
	@echo "  make verify  - best-effort quality gate (runs test/lint/format if wired)"
	@echo ""
	@echo "This template does not assume a stack."
	@echo "After choosing a stack, update this Makefile (or replace it)."

setup:
	@echo "No-op. Choose a stack, then wire setup commands here."

test:
	@echo "No-op. Choose a stack, then wire test commands here (pytest/npm/etc)."

lint:
	@echo "No-op. Choose a stack, then wire lint commands here (ruff/eslint/etc)."

format:
	@echo "No-op. Choose a stack, then wire formatter commands here (ruff/black/prettier/etc)."

verify:
	@./scripts/verify.sh
