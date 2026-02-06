#!/usr/bin/env bash
set -euo pipefail

# Create a lightweight context bundle of key project files.
# Useful for code reviews, onboarding, or documentation.
# Output: tmp/context.txt

ROOT="${1:-.}"
OUT="tmp/context.txt"

mkdir -p tmp

{
  echo "# Project Context"
  echo "Generated: $(date -Is)"
  echo
  echo "## Repository Structure (depth 3)"
  find "$ROOT" -maxdepth 3 -type f \
    -not -path '*/.git/*' \
    -not -path '*/node_modules/*' \
    -not -path '*/.venv/*' \
    -not -path '*/dist/*' \
    -not -path '*/build/*' \
    -not -path '*/.local/*' \
    | sed 's#^\./##' \
    | sort
  echo
  echo "## Key Documentation"
  for f in README.md PROJECT.md docs/STACK_DECISION.md docs/LOCAL_DEV.md; do
    if [ -f "$f" ]; then
      echo ""
      echo "---"
      echo "### $f"
      echo ""
      sed -n '1,200p' "$f"
    fi
  done
} > "$OUT"

echo "Wrote context to: $OUT"
