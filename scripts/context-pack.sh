#!/usr/bin/env bash
set -euo pipefail

# Create a lightweight context bundle for AI sessions.
# Output: tmp/context.txt

ROOT="${1:-.}"
OUT="tmp/context.txt"

mkdir -p tmp

{
  echo "# Context Pack"
  echo "Generated: $(date -Is)"
  echo
  echo "## Repo tree (depth 3)"
  find "$ROOT" -maxdepth 3 -type f \
    -not -path '*/.git/*' \
    -not -path '*/node_modules/*' \
    -not -path '*/.venv/*' \
    -not -path '*/dist/*' \
    -not -path '*/build/*' \
    | sed 's#^\./##' \
    | sort
  echo
  echo "## Key docs"
  for f in README.md CLAUDE.md PROJECT.md docs/STACK_DECISION.md docs/LOCAL_DEV.md; do
    if [ -f "$f" ]; then
      echo "\n---\n### $f\n"
      sed -n '1,200p' "$f"
    fi
  done
} > "$OUT"

echo "Wrote: $OUT"
