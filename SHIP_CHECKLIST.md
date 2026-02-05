# Ship Checklist (Crate)

This is the minimum set of checks to confirm Crate is ready to ship.

## 1) Code quality
- [ ] `pytest -q` passes
- [ ] `ruff check crate web tests` passes
- [ ] `mypy crate --config-file pyproject.toml` passes

## 2) CLI smoke test (safe)
Create a test folder with a few MP3s (real files recommended):
- [ ] Dry-run preview:
  - [ ] `crate ~/Music/DJ/Incoming --recursive --dry-run -v`
  - [ ] Output is readable (no stack traces)
- [ ] Apply rename:
  - [ ] `crate ~/Music/DJ/Incoming --recursive`
  - [ ] Renames happen as expected

## 3) Web UI smoke test
- [ ] Start server:
  - [ ] `python3 run_web.py`
- [ ] Open UI:
  - [ ] http://localhost:8000
- [ ] Preview:
  - [ ] Select a folder with MP3s
  - [ ] Preview shows planned renames
- [ ] Execute:
  - [ ] Execute rename completes
  - [ ] Status counts look sane
- [ ] Undo:
  - [ ] Undo restores original filenames

## 4) Safety checks
- [ ] Preview mode does not write tags
- [ ] Invalid paths are rejected (no traversal)
- [ ] Cancellation behaves (best-effort)

## 5) Docs sanity
- [ ] README points new users to `docs/GETTING_STARTED.md`
- [ ] No outdated command names in docs (old `dj_mp3_renamer` references)
