# Project Template (2026) — What this is

A reusable skeleton for starting new projects with dev coding tools:
- Claude Code / Claude CLI
- Cursor
- OpenClaw (tool-using agent)

Design goals:
- **Low-friction startup** (fast to begin shipping)
- **Persistent memory** (`.claude/`) so sessions don’t reset to zero
- **Small, verifiable loops** (plan → implement → test)
- **Minimal context bloat** (short root guidance, deeper docs elsewhere)

Key files:
- `CLAUDE.md` – short working contract for Claude/Cursor
- `OPENCLAW.md` – how to use OpenClaw effectively in repos from this template
- `.claude/state/current-state.md` – what’s happening now
- `.claude/knowledge-base/*` – decisions + lessons that persist

Quickstart:
- Copy this template into a new repo directory (without `.git/`), then `git init`.
- Fill `PROJECT.md` (see `docs/PROJECT.md.template`)
- Start an dev session and tell it to read `CLAUDE.md` + `.claude/state/current-state.md`.
