#!/usr/bin/env bash
set -euo pipefail

echo "==> verify (batch_rename)"

if [ -f Makefile ]; then
  echo "==> make lint"
  make lint
  echo "==> make test"
  make test
  echo "==> make format (check only)"
  . .venv/bin/activate && ruff format --check .
  exit 0
fi

echo "No Makefile found; falling back to pytest/ruff if available"
command -v ruff >/dev/null 2>&1 && ruff check .
command -v pytest >/dev/null 2>&1 && pytest -q
