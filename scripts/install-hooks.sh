#!/usr/bin/env bash
set -euo pipefail

# Opt-in git hooks (pre-push runs make verify)
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "ERROR: run inside a git repo" >&2
  exit 1
fi

chmod +x .githooks/*
git config core.hooksPath .githooks

echo "Installed hooksPath: $(git config --get core.hooksPath)"
