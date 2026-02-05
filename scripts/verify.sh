#!/usr/bin/env bash
set -euo pipefail

# scripts/verify.sh
# A friendly “quality gate” you can run anytime.
# Tries to run the best available checks without being stack-specific.

say() { printf "\n==> %s\n" "$*"; }

ROOT="${1:-.}"
cd "$ROOT"

say "Git status"
git status --porcelain || true

# Prefer Makefile targets if present
if [ -f Makefile ]; then
  if make -n test >/dev/null 2>&1; then
    say "make test"
    make test || true
  fi
  if make -n lint >/dev/null 2>&1; then
    say "make lint"
    make lint || true
  fi
  if make -n format >/dev/null 2>&1; then
    say "make format"
    make format || true
  fi
  exit 0
fi

# Fallbacks (best-effort)
if [ -f package.json ]; then
  say "npm test"
  npm test --if-present || true
  say "npm run lint"
  npm run lint --if-present || true
  say "npm run format"
  npm run format --if-present || true
  exit 0
fi

if [ -f pyproject.toml ] || [ -f requirements.txt ]; then
  if command -v pytest >/dev/null 2>&1; then
    say "pytest"
    pytest -q || true
  fi
  if command -v ruff >/dev/null 2>&1; then
    say "ruff check"
    ruff check . || true
    say "ruff format --check"
    ruff format --check . || true
  fi
  exit 0
fi

say "No recognized stack. Wire Makefile targets for your project."
