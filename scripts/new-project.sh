#!/usr/bin/env bash
set -euo pipefail

# Create a new project from this template.
# Usage:
#   ./scripts/new-project.sh /path/to/new-project "Project Name" [variant]
#
# Variants live in ./variants (e.g. python-fastapi | node-ts | nextjs)

TEMPLATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="${1:-}"
PROJECT_NAME="${2:-}"
VARIANT="${3:-}"

if [[ -z "$DEST_DIR" || -z "$PROJECT_NAME" ]]; then
  echo "Usage: $0 /path/to/new-project \"Project Name\" [variant]" >&2
  exit 1
fi

if [[ -e "$DEST_DIR" ]]; then
  echo "Destination already exists: $DEST_DIR" >&2
  exit 1
fi

mkdir -p "$DEST_DIR"

# Copy everything except .git and obvious local files
rsync -a --delete \
  --exclude '.git/' \
  --exclude '.DS_Store' \
  --exclude '.claude/settings.local.json' \
  "$TEMPLATE_DIR/" "$DEST_DIR/"

# Initialize project docs
if [[ ! -f "$DEST_DIR/PROJECT.md" ]]; then
  cp "$DEST_DIR/docs/PROJECT.md.template" "$DEST_DIR/PROJECT.md"
fi
if [[ -f "$DEST_DIR/docs/STACK_DECISION.md.template" && ! -f "$DEST_DIR/docs/STACK_DECISION.md" ]]; then
  cp "$DEST_DIR/docs/STACK_DECISION.md.template" "$DEST_DIR/docs/STACK_DECISION.md"
fi
if [[ -f "$DEST_DIR/docs/LOCAL_DEV.md.template" && ! -f "$DEST_DIR/docs/LOCAL_DEV.md" ]]; then
  cp "$DEST_DIR/docs/LOCAL_DEV.md.template" "$DEST_DIR/docs/LOCAL_DEV.md"
fi

# Optionally apply variant
if [[ -n "$VARIANT" ]]; then
  if [[ ! -d "$TEMPLATE_DIR/variants/$VARIANT" ]]; then
    echo "Unknown variant: $VARIANT" >&2
    echo "Available variants:" >&2
    ls -1 "$TEMPLATE_DIR/variants" | sed 's#/$##' >&2
    exit 1
  fi
  rsync -a "$TEMPLATE_DIR/variants/$VARIANT/" "$DEST_DIR/"
  # If the variant ships its own Makefile, prefer it.
  if [[ -f "$DEST_DIR/variants/$VARIANT/Makefile" && -f "$DEST_DIR/Makefile" ]]; then
    cp "$DEST_DIR/variants/$VARIANT/Makefile" "$DEST_DIR/Makefile"
  elif [[ -f "$TEMPLATE_DIR/variants/$VARIANT/Makefile" ]]; then
    cp "$TEMPLATE_DIR/variants/$VARIANT/Makefile" "$DEST_DIR/Makefile"
  fi

fi

# Seed state
STATE="$DEST_DIR/.claude/state/current-state.md"
cat > "$STATE" <<EOF
# Current State

Project: $PROJECT_NAME
Phase: initialization

## Next steps
- Fill PROJECT.md
- Copy docs/STACK_DECISION.md.template → docs/STACK_DECISION.md and decide stack (timeboxed)
- Wire Makefile targets (setup/test/lint/format)
- Create first thin vertical slice (one feature end-to-end)
EOF

echo "Created new project at: $DEST_DIR"
echo "Next: cd \"$DEST_DIR\" && git init && git add . && git commit -m 'Initial commit from template'"
