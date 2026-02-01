# Crate Rebrand: File Naming Strategy

## Executive Summary

This document defines the comprehensive file naming strategy for rebranding "DJ MP3 Renamer" → "Crate". All changes will preserve git history using `git mv` commands.

**Status**: Approved by user ("And Crate seems great")
**Execution**: Task #38

---

## 1. Python Package Naming

### Primary Package Name

**Old**: `dj_mp3_renamer`
**New**: `crate`

**Rationale**:
- Short, memorable, Pythonic (single word, all lowercase)
- Follows PEP-8 conventions
- Matches branding (Crate)
- No underscores needed (single word)

### PyPI Package Name

**Check Required**: `crate` availability on PyPI
**Primary**: `crate` (if available)
**Fallback**: `cratepy` (Python-specific, still searchable)

**Command to check**:
```bash
pip search crate  # or visit https://pypi.org/project/crate/
```

### Import Statement

**Old**:
```python
from dj_mp3_renamer.api import RenamerAPI
from dj_mp3_renamer.core.template import build_filename_from_template
```

**New**:
```python
from crate.api import CrateAPI  # RenamerAPI renamed to CrateAPI
from crate.core.template import build_filename_from_template
```

---

## 2. Repository Structure

### Directory Renaming

| Old Path | New Path | Command |
|----------|----------|---------|
| `batch_rename/` | `crate/` | Project root rename (optional) |
| `dj_mp3_renamer/` | `crate/` | **CRITICAL** - main package |
| `dj_mp3_renamer/api/` | `crate/api/` | Via parent rename |
| `dj_mp3_renamer/core/` | `crate/core/` | Via parent rename |
| `dj_mp3_renamer/tui/` | `crate/tui/` | Via parent rename |
| `dj_mp3_renamer/cli/` | `crate/cli/` | Via parent rename |

**Git Commands**:
```bash
# Main package rename (preserves git history)
git mv dj_mp3_renamer crate

# Optional: Rename project root directory
cd ..
mv batch_rename crate
cd crate
```

### Files to Rename

| Old Filename | New Filename | Location |
|--------------|--------------|----------|
| `start_web_ui.sh` | `start_crate_web.sh` | Root |
| `stop_web_ui.sh` | `stop_crate_web.sh` | Root |
| `.dj_renamer_web.pid` | `.crate_web.pid` | Root |

**Git Commands**:
```bash
git mv start_web_ui.sh start_crate_web.sh
git mv stop_web_ui.sh stop_crate_web.sh
# .pid file will be regenerated with new name
```

### Files to Preserve (Content Updates Only)

- `README.md` - Update content, not filename
- `setup.py` / `pyproject.toml` - Update package metadata
- `tests/` - Keep structure, update imports only
- `.gitignore` - Update patterns if needed
- `web/` - Keep structure, update branding in content

---

## 3. CLI Command Naming

### Entry Point

**Old**: `dj-rename` (or `dj-mp3-renamer`)
**New**: `crate`

**Rationale**:
- Simple, memorable, matches app name
- Easy to type, professional
- Follows modern CLI conventions (short commands)

**Usage Examples**:
```bash
# Old
dj-rename ~/Music --preview
dj-rename ~/Music --template "{artist} - {title} [{camelot} {bpm}]"

# New
crate ~/Music --preview
crate ~/Music --template "{artist} - {title} [{camelot} {bpm}]"
```

### Alternative Commands (Future Expansion)

```bash
crate rename ~/Music              # Explicit subcommand
crate preview ~/Music             # Preview changes
crate analyze ~/Music/track.mp3   # Analyze single file
crate sync                        # Cloud sync (future)
crate config                      # Show/edit config
```

### Entry Point Configuration

**File**: `setup.py` or `pyproject.toml`

**Old** (`setup.py`):
```python
entry_points={
    'console_scripts': [
        'dj-rename=dj_mp3_renamer.cli.main:main',
    ],
}
```

**New** (`setup.py`):
```python
entry_points={
    'console_scripts': [
        'crate=crate.cli.main:main',
    ],
}
```

**Alternative** (`pyproject.toml`):
```toml
[project.scripts]
crate = "crate.cli.main:main"
```

---

## 4. Configuration File Paths

### Config Directory

**Old**: `~/.config/dj-mp3-renamer/`
**New**: `~/.config/crate/`

**Migration Strategy**:
```python
# In crate/core/config.py

def get_config_path() -> Path:
    """Get config file path, migrating from old location if needed."""
    new_path = Path.home() / ".config" / "crate" / "config.json"
    old_path = Path.home() / ".config" / "dj-mp3-renamer" / "config.json"

    # Auto-migrate old config to new location
    if not new_path.exists() and old_path.exists():
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(old_path, new_path)
        logger.info(f"Migrated config from {old_path} to {new_path}")

    return new_path
```

**Benefits**:
- Seamless upgrade experience
- No data loss for existing users
- Old config preserved (not deleted) for safety

### Config File Structure (No Changes)

```json
{
  "acoustid_api_key": "...",
  "enable_musicbrainz": false,
  "default_template": "{artist} - {title}{mix_paren}{kb}",
  "first_run_complete": true
}
```

---

## 5. Web UI Branding

### HTML/CSS/JS Updates

**Files to Update** (content only, not filenames):

1. **web/static/index.html**:
   - `<title>DJ MP3 Renamer</title>` → `<title>Crate</title>`
   - `<h1>🎵 DJ MP3 Renamer</h1>` → `<h1>🎵 Crate</h1>`
   - Meta tags, descriptions

2. **web/static/css/styles.css**:
   - No changes needed (no branding in CSS)

3. **web/static/js/app.js**:
   - Console logs: "DJ MP3 Renamer - Initializing..." → "Crate - Initializing..."
   - Comments/docstrings with old name

4. **web/main.py**:
   - FastAPI app title: "DJ MP3 Renamer" → "Crate"
   - API descriptions

### Visual Branding (Optional Future Enhancement)

- **Logo/Icon**: Stylized crate icon
- **Color Scheme**: Professional (navy blue + orange or purple + gold)
- **Tagline**: "Your music library, organized."

---

## 6. Import Path Updates

### Comprehensive Search & Replace

**Pattern**: `dj_mp3_renamer` → `crate`

**Files Affected** (all .py files):
```
crate/              # Main package (renamed)
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── models.py
│   └── renamer.py  # imports from crate.core.*
├── core/
│   └── *.py        # all core modules
├── tui/
│   └── *.py        # imports from crate.api, crate.core
├── cli/
│   └── *.py        # imports from crate.api
web/
└── main.py         # imports from crate.api, crate.core
tests/
└── test_*.py       # all test files import from crate.*
```

**Automated Command**:
```bash
# Find all Python files with old import
grep -r "from dj_mp3_renamer" --include="*.py" .

# Replace in all files (macOS)
find . -name "*.py" -type f -exec sed -i '' 's/from dj_mp3_renamer/from crate/g' {} +
find . -name "*.py" -type f -exec sed -i '' 's/import dj_mp3_renamer/import crate/g' {} +

# Replace in all files (Linux)
find . -name "*.py" -type f -exec sed -i 's/from dj_mp3_renamer/from crate/g' {} +
find . -name "*.py" -type f -exec sed -i 's/import dj_mp3_renamer/import crate/g' {} +
```

### Class Renames

**Optional but Recommended**:

| Old Class Name | New Class Name | File |
|----------------|----------------|------|
| `RenamerAPI` | `CrateAPI` | `crate/api/renamer.py` |
| `RenameRequest` | `CrateRequest` | `crate/api/models.py` |
| `RenameResult` | `CrateResult` | `crate/api/models.py` |
| `RenameStatus` | `CrateStatus` | `crate/api/models.py` |

**Rationale**:
- More generic naming (Crate can grow beyond renaming)
- Cleaner API: `from crate.api import CrateAPI`
- Consistency with new branding

**Alternative** (Keep Current Names):
- Less disruptive for existing users
- `RenamerAPI` still makes sense (describes what it does)
- Can do this later in v3.0.0

**Recommendation**: Keep `RenamerAPI` for now (v2.0.0 rebrand), rename in v3.0.0 if Crate expands features.

---

## 7. Documentation Updates

### README.md

**Changes**:
1. Title: "# DJ MP3 Renamer 🎶" → "# Crate 🎵"
2. Tagline: "A modular, API-first Python tool that renames MP3 files..." → "Your music library, organized."
3. Installation:
   ```bash
   # Old
   pip install dj-mp3-renamer

   # New
   pip install crate  # or cratepy if crate taken
   ```
4. CLI examples:
   ```bash
   # Old
   dj-rename ~/Music --preview

   # New
   crate ~/Music --preview
   ```
5. Python API:
   ```python
   # Old
   from dj_mp3_renamer.api import RenamerAPI

   # New
   from crate.api import RenamerAPI  # or CrateAPI if renamed
   ```

### ./claude/ Documentation

**Files to Update**:
- `lessons-learned.md` - Add rebrand documentation
- `metadata-lookup-logic.md` - Update code references (dj_mp3_renamer → crate)
- `market-research-2025-2026.md` - Add note about final name selection
- `app-naming-research-2025-2026.md` - Mark as "APPROVED: Crate"

### Docstrings & Comments

**Pattern**: Search for "DJ MP3 Renamer" in comments and update to "Crate"

```bash
# Find all occurrences
grep -r "DJ MP3 Renamer" --include="*.py" --include="*.md" .

# Review and update manually (context-dependent)
```

---

## 8. Testing Strategy

### Test File Updates

**No Renames Needed** - tests/ directory structure stays the same:
```
tests/
├── test_api_*.py
├── test_core_*.py
├── test_template.py
└── ...
```

**Import Updates Required**:
```python
# Old
from dj_mp3_renamer.core.template import build_filename_from_template
from dj_mp3_renamer.api import RenamerAPI

# New
from crate.core.template import build_filename_from_template
from crate.api import RenamerAPI
```

### Verification Checklist

After rebrand, run:
```bash
# 1. Install package in editable mode
pip install -e .

# 2. Verify CLI works
crate --help

# 3. Run full test suite
pytest tests/ -v

# 4. Verify imports work
python -c "from crate.api import RenamerAPI; print('OK')"

# 5. Test web UI
./start_crate_web.sh

# 6. Check config migration
rm -rf ~/.config/crate  # Clear new config
# Old config at ~/.config/dj-mp3-renamer/ should auto-migrate
crate --help  # Triggers config load and migration
ls ~/.config/crate/config.json  # Should exist

# 7. Verify git history preserved
git log --follow crate/api/renamer.py  # Should show full history
```

---

## 9. Breaking Changes & Migration Guide

### For End Users

**Breaking Changes**:
- ❌ Old CLI command `dj-rename` will not work (uninstall old version first)
- ❌ Old import paths `from dj_mp3_renamer...` will fail
- ✅ Config auto-migrates from `~/.config/dj-mp3-renamer/` to `~/.config/crate/`

**Migration Steps**:
```bash
# 1. Uninstall old version
pip uninstall dj-mp3-renamer

# 2. Install new version
pip install crate  # or cratepy

# 3. Update scripts with new CLI command
# Old: dj-rename ~/Music
# New: crate ~/Music

# 4. Config migrates automatically on first run
```

### For Developers

**Breaking Changes**:
- ❌ Package name changed: `dj_mp3_renamer` → `crate`
- ❌ Import paths must be updated
- ✅ API signatures unchanged (RenamerAPI class still works the same)

**Migration Steps**:
```bash
# Update imports in your code
sed -i 's/from dj_mp3_renamer/from crate/g' *.py
sed -i 's/import dj_mp3_renamer/import crate/g' *.py

# Update requirements.txt
sed -i 's/dj-mp3-renamer/crate/g' requirements.txt

# Test
python -m pytest
```

---

## 10. Rollout Plan

### Phase 1: Pre-Rebrand Validation ✅
- [x] User approval on "Crate" name
- [ ] Check PyPI availability (`crate` or `cratepy`)
- [ ] Check domain availability (`crate.io`, `cratehq.com`)
- [ ] Verify trademark clearance

### Phase 2: Code Changes (Task #38)
- [ ] Rename main package: `git mv dj_mp3_renamer crate`
- [ ] Update all imports: automated sed/find commands
- [ ] Update CLI entry point in setup.py/pyproject.toml
- [ ] Update web UI branding (HTML titles, headers)
- [ ] Update README.md and documentation
- [ ] Add config migration logic
- [ ] Update start/stop scripts

### Phase 3: Testing
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Test CLI: `crate --help`, `crate ~/Music --preview`
- [ ] Test web UI: `./start_crate_web.sh`
- [ ] Test config migration
- [ ] Test package installation: `pip install -e .`
- [ ] Verify git history: `git log --follow crate/api/renamer.py`

### Phase 4: Release
- [ ] Commit all changes: `git add -A && git commit -m "feat: Rebrand to Crate"`
- [ ] Tag release: `git tag v2.0.0-crate`
- [ ] Update GitHub repo name and description
- [ ] Publish to PyPI: `python -m build && twine upload dist/*`
- [ ] Create announcement (README, social media)
- [ ] Archive old `dj-mp3-renamer` PyPI package (deprecation notice)

### Phase 5: User Communication
- [ ] Update README with migration guide
- [ ] Create CHANGELOG entry for v2.0.0
- [ ] Add deprecation notice to old package
- [ ] Update any external links/references

---

## 11. Backward Compatibility Strategy

### Option 1: Hard Break (Recommended)

**Approach**: Version 2.0.0 = clean break, no backward compatibility

**Pros**:
- Clean codebase, no legacy baggage
- Simpler to maintain
- Forces users to migrate (ensures everyone on new branding)

**Cons**:
- Breaks existing scripts/code
- Requires user action

**Mitigation**:
- Clear migration guide
- Deprecation notice on old PyPI package: "This package has been renamed to 'crate'. Please update your dependencies."

### Option 2: Transition Package (Overkill for This Project)

**Approach**: Keep `dj-mp3-renamer` as thin wrapper that imports from `crate`

**Not Recommended**: Adds complexity for minimal benefit (small user base, early stage)

---

## 12. Quick Reference: Command Checklist

### Execution Commands (Task #38)

```bash
# 1. Rename main package
git mv dj_mp3_renamer crate

# 2. Rename scripts
git mv start_web_ui.sh start_crate_web.sh
git mv stop_web_ui.sh stop_crate_web.sh

# 3. Update imports (macOS)
find . -name "*.py" -type f -exec sed -i '' 's/from dj_mp3_renamer/from crate/g' {} +
find . -name "*.py" -type f -exec sed -i '' 's/import dj_mp3_renamer/import crate/g' {} +

# 4. Update references in Python files
find . -name "*.py" -type f -exec sed -i '' 's/dj_mp3_renamer/crate/g' {} +

# 5. Update HTML branding
sed -i '' 's/DJ MP3 Renamer/Crate/g' web/static/index.html
sed -i '' 's/🎵 DJ MP3 Renamer/🎵 Crate/g' web/static/index.html

# 6. Update web/main.py FastAPI title
sed -i '' 's/"DJ MP3 Renamer"/"Crate"/g' web/main.py

# 7. Update README (manual - preserve structure)
# Replace "DJ MP3 Renamer" with "Crate"
# Update CLI examples: dj-rename → crate
# Update installation: dj-mp3-renamer → crate

# 8. Update setup.py/pyproject.toml
# Change package name, entry point, metadata

# 9. Run tests
pytest tests/ -v

# 10. Test CLI
pip install -e .
crate --help

# 11. Commit
git add -A
git commit -m "feat: Rebrand to Crate

- Rename dj_mp3_renamer → crate
- Update CLI command: dj-rename → crate
- Update web UI branding
- Add config migration from ~/.config/dj-mp3-renamer
- Update all documentation

BREAKING CHANGE: Package renamed to 'crate'. Update imports and CLI commands.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## 13. Success Criteria

Task #38 is complete when:

- [ ] ✅ Package renamed: `crate/` exists, `dj_mp3_renamer/` gone
- [ ] ✅ All tests passing: `pytest tests/ -v` shows 100% pass rate
- [ ] ✅ CLI works: `crate --help` and `crate ~/Music --preview` functional
- [ ] ✅ Web UI works: `./start_crate_web.sh` launches correctly
- [ ] ✅ Web UI branding updated: "Crate" visible in browser title and header
- [ ] ✅ Config migration works: Old config auto-migrates to new location
- [ ] ✅ Documentation updated: README reflects new name and commands
- [ ] ✅ Git history preserved: `git log --follow` shows full history
- [ ] ✅ No broken imports: All files reference `crate`, not `dj_mp3_renamer`
- [ ] ✅ Package installable: `pip install -e .` succeeds

---

## 14. Risk Assessment

### Low Risk
- [x] File renames (git mv preserves history)
- [x] Import updates (automated, testable)
- [x] Documentation updates (non-functional)

### Medium Risk
- [ ] Config migration (test thoroughly with old configs)
- [ ] CLI entry point (ensure pip installs correctly)
- [ ] Web UI (verify no hardcoded paths)

### High Risk
- None identified

### Mitigation
- Full test suite must pass before commit
- Manual testing of all features before release
- Git history preserved for rollback if needed
- Can revert entire commit if critical issues found

---

**Document Status**: Ready for Execution (Task #38)
**Approved By**: User (confirmed "Crate seems great")
**Next Step**: Execute rebrand per this strategy
