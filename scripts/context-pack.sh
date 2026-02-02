#!/usr/bin/env bash
set -euo pipefail

# Create a lightweight context bundle for AI sessions.
# Output: tmp/context.txt

OUT="tmp/context.txt"
mkdir -p tmp

{
  echo "# Context Pack"
  echo "Generated: $(date -Is)"
  echo
  echo "## Repo tree (depth 3)"
  find . -maxdepth 3 -type f \
    -not -path '*/.git/*' \
    -not -path '*/.venv/*' \
    -not -path '*/node_modules/*' \
    -not -path '*/__pycache__/*' \
    | sed 's#^\./##' | sort
  echo
  echo "## Key docs"
  for f in README.md CLAUDE.md docs/STACK_DECISION.md docs/LOCAL_DEV.md; do
    if [ -f "$f" ]; then
      echo "\n---\n### $f\n"
      sed -n '1,200p' "$f"
    fi
  done
} > "$OUT"

echo "Wrote: $OUT"
