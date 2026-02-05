# Current State

**Last Updated**: 2026-02-05

**Purpose**: This file tells Claude/OpenClaw (and you) exactly where the project is RIGHT NOW. Update this after every significant work session.

---

## Project Overview

**Project Name**: Crate

**What it is**: DJ-focused MP3 renamer (CLI + Web UI) driven by tags/metadata, with safety-first rename preview/execute and undo.

**Canonical Repo Path (MBP)**: `/Users/szenone/Code/labs/python/DJ/crate`

**GitHub**: `git@github.com:zenone/crate.git` (https://github.com/zenone/crate)

**Current Goal**: Ship by EOD today.

---

## Current Status (as of 2026-02-05)

### ✅ Green gates
- `ruff check crate web tests` ✅
- `mypy crate --config-file pyproject.toml` ✅
- `pytest -q` ✅ (384 passed, 1 skipped)

### ✅ Publishing
- `main` pushed successfully to GitHub from MBP.
- SSH auth + SSH signing configured; commit verifies locally.

### ✅ Repo structure fixes completed today
- `ai-dev-kit` guidance synced into repo (CLAUDE/OPENCLAW/.claude rules + templates refreshed).
- Removed accidental copy artifacts from the working tree:
  - `.venv.nosync/`
  - `web/uploads/` MP3 uploads
  - `* 2.py` / `* 2.sh` duplicates
  - `.venv 2` symlink
- Added missing dev dependency: `httpx` (required by FastAPI/Starlette TestClient during pytest collection).

---

## Current Sprint / Focus

### EOD Ship Checklist (remaining)
1) Run **manual smoke test** on real MP3 fixture:
   - CLI: preview + execute + undo
   - Web: preview + execute + undo
2) Sanity-check README + docs render correctly on GitHub.
3) Create release/tag (decide version).

---

## Known Constraints / Gotchas
- Python: prefer **Python 3.12** for local venv (some pinned deps (e.g., essentia) may not be available on newest Python).
- Dropbox/File Provider can intermittently error (unrelated to Crate itself); avoid using it for repo canonical storage.

---

## Next Steps (immediate)
- Decide ship version: recommend `v0.1.0` unless you want to commit to a stable API/UX promise.
- Run smoke tests on the fixture folder.
- Tag + release + final verification.
