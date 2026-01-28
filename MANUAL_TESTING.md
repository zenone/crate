# Manual Testing Guide

## Prerequisites

```bash
cd /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename
pip install -e .  # Ensure package is installed
```

---

## Test 1: API Interface (Programmatic)

### Test 1a: Basic API Import
```bash
python3 -c "
from dj_mp3_renamer.api import RenamerAPI, RenameRequest, RenameStatus
print('✓ API imports successfully')
"
```

### Test 1b: API with Mock Directory
```bash
python3 << 'EOF'
from pathlib import Path
from dj_mp3_renamer.api import RenamerAPI, RenameRequest

# Create test directory
test_dir = Path("/tmp/dj_test_api")
test_dir.mkdir(exist_ok=True)
(test_dir / "test.mp3").touch()

# Use API
api = RenamerAPI(workers=4)
request = RenameRequest(path=test_dir, dry_run=True)
status = api.rename_files(request)

print(f"✓ API executed successfully")
print(f"  Total: {status.total}")
print(f"  Renamed: {status.renamed}")
print(f"  Skipped: {status.skipped}")
print(f"  Errors: {status.errors}")

# Cleanup
import shutil
shutil.rmtree(test_dir)
EOF
```

**Expected Result:** Should execute without errors. File will be "skipped" due to no metadata.

---

## Test 2: CLI Interfaces

### Test 2a: Old Script (Backward Compatibility)
```bash
python3 dj_mp3_renamer.py --help | head -5
```
**Expected:** Show help message

### Test 2b: Module Execution
```bash
python3 -m dj_mp3_renamer --help | head -5
```
**Expected:** Show help message

### Test 2c: Installed Command
```bash
dj-mp3-renamer --help | head -5
```
**Expected:** Show help message

### Test 2d: CLI with Test Directory
```bash
# Create test directory
mkdir -p /tmp/dj_test_cli
touch /tmp/dj_test_cli/test.mp3

# Run CLI
dj-mp3-renamer /tmp/dj_test_cli --dry-run -v

# Cleanup
rm -rf /tmp/dj_test_cli
```
**Expected:** Should show "No .mp3 files found" or skip the file

---

## Test 3: Unit Tests

### Test 3a: Run All Tests
```bash
pytest tests/ -v
```
**Expected:** 129 tests passing

### Test 3b: Check Coverage
```bash
pytest tests/ --cov=dj_mp3_renamer --cov-report=term
```
**Expected:** ~75% coverage

### Test 3c: Run Specific Module Tests
```bash
pytest tests/test_api.py -v
pytest tests/test_key_conversion.py -v
pytest tests/test_sanitization.py -v
```

---

## Test 4: Real MP3 Files (IMPORTANT!)

### Test 4a: Create Test MP3 with Metadata

```bash
# You'll need to copy actual MP3 files from your music library
# Create test directory
mkdir -p ~/Music/TEST_RENAME

# Copy some MP3s there (3-5 files)
# Example:
# cp ~/Music/SomeArtist/*.mp3 ~/Music/TEST_RENAME/
```

### Test 4b: Dry Run Test
```bash
dj-mp3-renamer ~/Music/TEST_RENAME --dry-run -vv
```
**Expected:**
- Should read metadata from MP3s
- Show what renames would happen
- No actual files changed

### Test 4c: Actual Rename (Small Test)
```bash
dj-mp3-renamer ~/Music/TEST_RENAME -v
```
**Expected:**
- Files actually renamed
- Check results match expectations

### Test 4d: Recursive Test
```bash
# Create subdirectories
mkdir -p ~/Music/TEST_RENAME/subdir
# Copy some MP3s to subdir

# Test recursive
dj-mp3-renamer ~/Music/TEST_RENAME --recursive --dry-run -v
```

### Test 4e: Custom Template
```bash
dj-mp3-renamer ~/Music/TEST_RENAME \
  --template "{artist} - {title} [{camelot} {bpm}]" \
  --dry-run -v
```

---

## Test 5: Edge Cases

### Test 5a: Non-existent Directory
```bash
dj-mp3-renamer /path/that/does/not/exist --dry-run
```
**Expected:** Error message about path not existing

### Test 5b: Directory with No MP3s
```bash
mkdir -p /tmp/no_mp3s
dj-mp3-renamer /tmp/no_mp3s --dry-run
rm -rf /tmp/no_mp3s
```
**Expected:** "No .mp3 files found"

### Test 5c: Single File
```bash
# Copy one MP3
cp ~/Music/some_song.mp3 /tmp/test_single.mp3
dj-mp3-renamer /tmp/test_single.mp3 --dry-run -v
rm /tmp/test_single.mp3
```

---

## Test 6: API Advanced Usage

### Test 6a: Custom Logger
```bash
python3 << 'EOF'
import logging
from pathlib import Path
from dj_mp3_renamer.api import RenamerAPI, RenameRequest

# Custom logger
logger = logging.getLogger("my_test")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("CUSTOM: %(message)s"))
logger.addHandler(handler)

# Use API with custom logger
api = RenamerAPI(workers=2, logger=logger)
request = RenameRequest(path=Path("/tmp"), dry_run=True)
# status = api.rename_files(request)

print("✓ Custom logger works")
EOF
```

### Test 6b: Threading Test
```bash
python3 << 'EOF'
from pathlib import Path
from dj_mp3_renamer.api import RenamerAPI, RenameRequest

# Test with different worker counts
for workers in [1, 4, 8]:
    api = RenamerAPI(workers=workers)
    print(f"✓ API with {workers} workers initialized")
EOF
```

---

## Test 7: Code Quality

### Test 7a: Import Checks
```bash
# Verify no circular imports
python3 -c "import dj_mp3_renamer"
python3 -c "from dj_mp3_renamer.core import sanitization"
python3 -c "from dj_mp3_renamer.core import key_conversion"
python3 -c "from dj_mp3_renamer.core import metadata_parsing"
python3 -c "from dj_mp3_renamer.core import template"
python3 -c "from dj_mp3_renamer.core import io"
python3 -c "from dj_mp3_renamer.api import models, renamer"
python3 -c "from dj_mp3_renamer.cli import main"
echo "✓ All modules import cleanly"
```

### Test 7b: Type Hints Check (Optional)
```bash
# If mypy is installed
mypy dj_mp3_renamer/ 2>&1 | grep -E "error|success" || echo "mypy not installed"
```

---

## Test 8: Documentation Check

### Test 8a: Verify Help Messages
```bash
dj-mp3-renamer --help | grep -q "template" && echo "✓ Help includes template"
dj-mp3-renamer --help | grep -q "workers" && echo "✓ Help includes workers"
dj-mp3-renamer --help | grep -q "recursive" && echo "✓ Help includes recursive"
```

### Test 8b: Check Docstrings
```bash
python3 -c "
from dj_mp3_renamer.api import RenamerAPI
print(RenamerAPI.__doc__)
print(RenamerAPI.rename_files.__doc__)
" | grep -q "API" && echo "✓ API docstrings present"
```

---

## Checklist Summary

Run through this checklist:

- [ ] API imports successfully (Test 1a)
- [ ] API executes with mock data (Test 1b)
- [ ] Old script works (Test 2a)
- [ ] Module execution works (Test 2b)
- [ ] Installed command works (Test 2c)
- [ ] All 129 tests pass (Test 3a)
- [ ] Coverage is ~75% (Test 3b)
- [ ] **Real MP3 dry-run works** (Test 4b) ⭐ CRITICAL
- [ ] **Real MP3 rename works** (Test 4c) ⭐ CRITICAL
- [ ] Recursive mode works (Test 4d)
- [ ] Custom template works (Test 4e)
- [ ] Edge cases handled (Test 5)
- [ ] All modules import cleanly (Test 7a)

---

## Quick Test Script

Run all quick tests at once:

```bash
#!/bin/bash
echo "=== Quick Manual Test Suite ==="
echo ""

echo "1. API Import:"
python3 -c "from dj_mp3_renamer.api import RenamerAPI; print('✓')"

echo "2. CLI Old Script:"
python3 dj_mp3_renamer.py --help > /dev/null 2>&1 && echo "✓"

echo "3. CLI Module:"
python3 -m dj_mp3_renamer --help > /dev/null 2>&1 && echo "✓"

echo "4. CLI Installed:"
dj-mp3-renamer --help > /dev/null 2>&1 && echo "✓" || echo "⚠ (may need reinstall)"

echo "5. Unit Tests:"
pytest tests/ -q 2>&1 | tail -1

echo ""
echo "=== Next: Test with REAL MP3 files ==="
echo "Run: dj-mp3-renamer ~/Music/TEST_DIR --dry-run -vv"
```

Save as `quick_test.sh` and run: `bash quick_test.sh`
