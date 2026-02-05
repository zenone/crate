#!/usr/bin/env bash
set -euo pipefail

# scripts/doctor.sh
# Quick environment checks for projects created from this template.

ok=0
warn=0
fail=0

pass() { printf "✅ %s\n" "$*"; ok=$((ok+1)); }
info() { printf "ℹ️  %s\n" "$*"; }
W() { printf "⚠️  %s\n" "$*"; warn=$((warn+1)); }
X() { printf "❌ %s\n" "$*"; fail=$((fail+1)); }

need_cmd() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    pass "$name: $(command -v "$name")"
  else
    X "$name: not found"
  fi
}

header() { printf "\n== %s ==\n" "$*"; }

header "Core tools"
need_cmd git
need_cmd make

header "Node / JS"
if command -v node >/dev/null 2>&1; then
  pass "node: $(node -v)"
else
  W "node: not found (needed for node-ts/nextjs variants)"
fi
if command -v npm >/dev/null 2>&1; then
  pass "npm: $(npm -v)"
else
  W "npm: not found"
fi

header "Python"
if command -v python3 >/dev/null 2>&1; then
  pass "python3: $(python3 -V 2>&1)"
else
  W "python3: not found (needed for python-fastapi variant)"
fi

header "Optional but recommended"
if command -v rg >/dev/null 2>&1; then
  pass "rg (ripgrep): $(command -v rg)"
else
  info "rg not found (nice for fast code search)"
fi

if command -v gh >/dev/null 2>&1; then
  pass "gh (GitHub CLI): $(command -v gh)"
else
  info "gh not found (optional)"
fi

if command -v clawdbot >/dev/null 2>&1; then
  pass "clawdbot: $(clawdbot --version 2>/dev/null || echo installed)"
else
  info "clawdbot not found (optional)"
fi

header "Summary"
printf "OK: %d, Warnings: %d, Failures: %d\n" "$ok" "$warn" "$fail"

if [ "$fail" -gt 0 ]; then
  exit 2
fi
