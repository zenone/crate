# DJ MP3 Renamer - Manual Testing Checklist

**Date:** 2026-01-27
**Tester:** _______________
**Test Environment:** macOS / Linux / Windows

---

## Pre-Test Setup

### 1. Create Test Directory
```bash
mkdir -p ~/Desktop/dj_test_files
cd ~/Desktop/dj_test_files
```

### 2. Prepare Test MP3 Files

You'll need **3 types** of test files:

**Option A: Use Your Bebel Gilberto Files**
```bash
# Copy 3-5 of your existing MP3 files to test directory
cp /path/to/your/music/*.mp3 ~/Desktop/dj_test_files/
```

**Option B: Create Dummy MP3 Files (for structure testing)**
```bash
# Create fake MP3s with different naming patterns
cd ~/Desktop/dj_test_files
touch "01 Artist - Song Title (Original Mix).mp3"
touch "02 Different Artist - Track Name.mp3"
touch "Track without tags.mp3"
touch "file-with-dashes.mp3"
touch "UPPERCASE TRACK.MP3"
```

**Note:** For full testing, real MP3 files with ID3 tags are best, but dummy files work for basic functionality.

### 3. Verify Installation
```bash
cd /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename
python3 -c "from dj_mp3_renamer.api import RenamerAPI; print('✓ API installed')"
python3 -c "from dj_mp3_renamer.tui import run_tui; print('✓ TUI installed')"
```

**Expected:** Both print success messages

---

## Test Suite 1: Terminal UI (TUI) - **RECOMMENDED**

### Test 1.1: Launch TUI
```bash
cd /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename
python run_tui.py
```

**Expected:**
- ✅ TUI launches with header "DJ MP3 Renamer - Terminal UI"
- ✅ Input fields visible (Directory Path, Template)
- ✅ Checkbox: "Recursive (include subfolders)"
- ✅ Three buttons: Preview, Rename Files, Reset
- ✅ Stats panel shows "Ready for new directory"
- ✅ Footer shows keyboard shortcuts (Q, P, R, Ctrl+R, ?)

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 1.2: Path Input - Type Path
**Steps:**
1. Type in Directory Path field: `~/Desktop/dj_test_files`
2. Press `Tab` to move to Template field

**Expected:**
- ✅ Cursor moves to Template field
- ✅ Template shows default: `{artist} - {title}{mix_paren}{kb}`

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 1.3: Path Input - Invalid Path
**Steps:**
1. Clear Directory Path
2. Type: `/nonexistent/fake/path`
3. Press `P` (Preview)

**Expected:**
- ✅ Error notification: "Path does not exist"
- ✅ No crash
- ✅ Stats panel unchanged

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 1.4: Preview (Dry-Run)
**Steps:**
1. Enter valid path: `~/Desktop/dj_test_files`
2. Leave template as default
3. Keep "Recursive" checked
4. Press `P` or click "Preview" button

**Expected:**
- ✅ Notification: "Previewing files in dj_test_files..."
- ✅ Stats panel updates:
  - Total Files: (number of MP3s found)
  - To Rename: (number with tags)
  - Skipped: (number without tags or errors)
  - Errors: 0 or more
- ✅ Results panel shows table with:
  - Status column (→, ⊘, ✗)
  - Original filename
  - Arrow →
  - New filename (or skip reason)
- ✅ Results are color-coded:
  - Green → for files to be renamed
  - Yellow ⊘ for skipped files
  - Red ✗ for errors

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 1.5: Custom Template
**Steps:**
1. Clear Template field
2. Type: `{bpm} - {artist} - {title}`
3. Press `P` (Preview)

**Expected:**
- ✅ Results show new format: "128 - Artist - Song.mp3"
- ✅ BPM appears first
- ✅ Stats update correctly

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 1.6: Empty Template
**Steps:**
1. Clear Template field completely
2. Press `P` (Preview)

**Expected:**
- ✅ Error notification: "Please enter a template"
- ✅ No crash

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 1.7: Rename Files (Actual Execution)
**Steps:**
1. Ensure valid path and template are entered
2. Press `P` to preview first
3. Review results carefully
4. Press `R` or click "Rename Files"
5. Confirm when prompted

**Expected:**
- ✅ Notification: "Renaming files..."
- ✅ Stats update with actual results
- ✅ Results panel shows completed renames
- ✅ Status changes from → to ✓
- ✅ Success notification: "✓ Successfully renamed X files!"

**Verification:**
```bash
ls -la ~/Desktop/dj_test_files/
# Check that files have new names
```

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 1.8: Recursive Checkbox
**Steps:**
1. Create subdirectory:
   ```bash
   mkdir ~/Desktop/dj_test_files/subfolder
   cp ~/Desktop/dj_test_files/*.mp3 ~/Desktop/dj_test_files/subfolder/
   ```
2. Uncheck "Recursive" checkbox
3. Press `P` (Preview)
4. Note the file count
5. Check "Recursive" checkbox
6. Press `P` (Preview) again
7. Note the new file count

**Expected:**
- ✅ Unchecked: Only files in root directory counted
- ✅ Checked: Files in root + subfolder counted
- ✅ Total increases when recursive is enabled

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 1.9: Reset Button
**Steps:**
1. Fill in path and template
2. Press `P` to preview
3. Press `Ctrl+R` or click "Reset"

**Expected:**
- ✅ Directory Path cleared
- ✅ Template reset to default
- ✅ Recursive checkbox reset to checked
- ✅ Stats panel shows "Ready for new directory"
- ✅ Results panel cleared

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 1.10: Keyboard Shortcuts
**Steps:**
1. Press `?` key

**Expected:**
- ✅ Help screen appears showing all shortcuts

**Test each shortcut:**
- `P` → Preview works
- `R` → Rename works (after preview)
- `Ctrl+R` → Reset works
- `Q` → Quit application
- `Ctrl+C` → Force quit

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 1.11: Scrolling Long Results
**Steps:**
1. Use directory with 20+ MP3 files
2. Press `P` to preview
3. Use arrow keys or mouse to scroll results

**Expected:**
- ✅ Results panel scrollable
- ✅ Can see all files
- ✅ Scroll position indicator visible

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 1.12: Files Without ID3 Tags
**Steps:**
1. Create MP3 without tags:
   ```bash
   dd if=/dev/zero of=~/Desktop/dj_test_files/no_tags.mp3 bs=1024 count=10 2>/dev/null
   ```
2. Press `P` to preview

**Expected:**
- ✅ File appears in "Skipped" count
- ✅ Message: "No readable tags" or similar
- ✅ Status: Yellow ⊘

**Pass/Fail:** _____ | **Notes:** _____________________

---

## Test Suite 2: Command-Line Interface (CLI)

### Test 2.1: Basic CLI Help
```bash
cd /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename
python3 dj_mp3_renamer.py --help
```

**Expected:**
- ✅ Help text displays
- ✅ Shows all options: --recursive, --dry-run, --workers, -l, -v, --template
- ✅ Shows default template

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 2.2: CLI Dry-Run
```bash
python3 dj_mp3_renamer.py ~/Desktop/dj_test_files --dry-run -v
```

**Expected:**
- ✅ Shows "DRY" prefix for each file
- ✅ Displays old → new filename
- ✅ Shows summary at end (Total, Renamed, Skipped, Errors)
- ✅ No files actually renamed
- ✅ Exit code 0

**Verification:**
```bash
echo $?  # Should output: 0
```

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 2.3: CLI Actual Rename
```bash
# First, make a backup
cp -r ~/Desktop/dj_test_files ~/Desktop/dj_test_files_backup

# Then rename
python3 dj_mp3_renamer.py ~/Desktop/dj_test_files -v
```

**Expected:**
- ✅ Shows "REN" prefix for each renamed file
- ✅ Progress bar visible (if tqdm installed)
- ✅ Files actually renamed
- ✅ Summary shows correct counts

**Verification:**
```bash
ls -la ~/Desktop/dj_test_files/
# Files should have new names
```

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 2.4: CLI Custom Template
```bash
# Restore backup first
rm -rf ~/Desktop/dj_test_files
cp -r ~/Desktop/dj_test_files_backup ~/Desktop/dj_test_files

python3 dj_mp3_renamer.py ~/Desktop/dj_test_files \
  --template "{bpm} - {key} - {artist} - {title}" \
  --dry-run -v
```

**Expected:**
- ✅ Files show custom format: "128 - Am - Artist - Title.mp3"
- ✅ Template applied correctly

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 2.5: CLI Recursive Mode
```bash
python3 dj_mp3_renamer.py ~/Desktop/dj_test_files --recursive --dry-run -v
```

**Expected:**
- ✅ Processes files in root directory
- ✅ Processes files in subdirectories
- ✅ Shows paths with subdirectory names

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 2.6: CLI Workers Parameter
```bash
python3 dj_mp3_renamer.py ~/Desktop/dj_test_files --workers 8 --dry-run -v
```

**Expected:**
- ✅ Runs without error
- ✅ Processes files (potentially faster with more workers)

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 2.7: CLI Log File
```bash
python3 dj_mp3_renamer.py ~/Desktop/dj_test_files \
  --dry-run -v \
  -l ~/Desktop/rename_log.txt
```

**Expected:**
- ✅ Creates log file at ~/Desktop/rename_log.txt
- ✅ Log contains detailed information
- ✅ Console still shows output

**Verification:**
```bash
cat ~/Desktop/rename_log.txt
# Should show detailed log
```

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 2.8: CLI Verbosity Levels
```bash
# No verbosity
python3 dj_mp3_renamer.py ~/Desktop/dj_test_files --dry-run

# Level 1
python3 dj_mp3_renamer.py ~/Desktop/dj_test_files --dry-run -v

# Level 2
python3 dj_mp3_renamer.py ~/Desktop/dj_test_files --dry-run -vv
```

**Expected:**
- ✅ Each level shows progressively more detail
- ✅ -vv shows debug information

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 2.9: CLI Empty Directory
```bash
mkdir ~/Desktop/empty_dir
python3 dj_mp3_renamer.py ~/Desktop/empty_dir --dry-run
```

**Expected:**
- ✅ Error message: "No .mp3 files found"
- ✅ Exit code 1

**Verification:**
```bash
echo $?  # Should output: 1
```

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 2.10: CLI Non-existent Path
```bash
python3 dj_mp3_renamer.py /fake/path/does/not/exist --dry-run
```

**Expected:**
- ✅ Error message about invalid path
- ✅ Exit code 1 or 2

**Pass/Fail:** _____ | **Notes:** _____________________

---

## Test Suite 3: Python API (Programmatic Usage)

### Test 3.1: Basic API Import
```bash
cd /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename
python3 -c "
from dj_mp3_renamer.api import RenamerAPI, RenameRequest, RenameStatus
print('✓ API imports successfully')
"
```

**Expected:**
- ✅ No errors
- ✅ Prints success message

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 3.2: API Dry-Run
```bash
python3 << 'EOF'
from pathlib import Path
from dj_mp3_renamer.api import RenamerAPI, RenameRequest

# Create API instance
api = RenamerAPI(workers=4)

# Create request
request = RenameRequest(
    path=Path("~/Desktop/dj_test_files").expanduser(),
    recursive=True,
    dry_run=True,
    template="{artist} - {title}{mix_paren}{kb}"
)

# Execute
status = api.rename_files(request)

# Check results
print(f"Total: {status.total}")
print(f"To Rename: {status.renamed}")
print(f"Skipped: {status.skipped}")
print(f"Errors: {status.errors}")

# Show first 3 results
for i, result in enumerate(status.results[:3]):
    if result.dst:
        print(f"{result.src.name} → {result.dst.name}")
    else:
        print(f"{result.src.name} - {result.message}")
EOF
```

**Expected:**
- ✅ Prints statistics
- ✅ Shows file mappings
- ✅ No actual files renamed

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 3.3: API Actual Rename
```bash
python3 << 'EOF'
from pathlib import Path
from dj_mp3_renamer.api import RenamerAPI, RenameRequest

api = RenamerAPI()
request = RenameRequest(
    path=Path("~/Desktop/dj_test_files").expanduser(),
    recursive=False,
    dry_run=False,  # ACTUAL RENAME
)

status = api.rename_files(request)

if status.renamed > 0:
    print(f"✓ Successfully renamed {status.renamed} files")
else:
    print("⚠ No files renamed")
EOF
```

**Expected:**
- ✅ Files actually renamed
- ✅ Success message printed

**Verification:**
```bash
ls -la ~/Desktop/dj_test_files/
```

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 3.4: API Custom Template
```bash
python3 << 'EOF'
from pathlib import Path
from dj_mp3_renamer.api import RenamerAPI, RenameRequest

api = RenamerAPI()
request = RenameRequest(
    path=Path("~/Desktop/dj_test_files").expanduser(),
    template="{bpm} - {camelot} - {artist} - {title}",
    dry_run=True,
)

status = api.rename_files(request)
print(f"Template test: {status.total} files processed")
EOF
```

**Expected:**
- ✅ Custom template applied
- ✅ Files show BPM and Camelot first

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 3.5: API Error Handling
```bash
python3 << 'EOF'
from pathlib import Path
from dj_mp3_renamer.api import RenamerAPI, RenameRequest

api = RenamerAPI()
request = RenameRequest(
    path=Path("/fake/path"),
    dry_run=True,
)

try:
    status = api.rename_files(request)
    print(f"Total: {status.total}")
except Exception as e:
    print(f"✓ Exception caught: {e}")
EOF
```

**Expected:**
- ✅ Either returns status with total=0 or raises exception
- ✅ No crash

**Pass/Fail:** _____ | **Notes:** _____________________

---

## Test Suite 4: Web UI (Optional)

### Test 4.1: Launch Web Server
```bash
cd /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename
python run_web.py
```

**Expected:**
- ✅ Server starts on http://127.0.0.1:8000
- ✅ No errors in console

**Keep server running for tests 4.2-4.10**

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 4.2: Access Web UI
**Steps:**
1. Open browser
2. Go to: http://localhost:8000

**Expected:**
- ✅ Page loads
- ✅ "DJ MP3 Renamer" title visible
- ✅ Theme toggle button (sun/moon icon) visible
- ✅ Two mode buttons: "Upload Files" and "Local Directory"

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 4.3: Web UI - Upload Mode (File Upload)
**Steps:**
1. Click "Upload Files" mode (should be active by default)
2. Click "Browse Files" or drag & drop MP3 files
3. Select 3-5 MP3 files from ~/Desktop/dj_test_files

**Expected:**
- ✅ Upload progress visible
- ✅ Files list appears showing uploaded files
- ✅ Template section appears (Step 2)
- ✅ Default template shown

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 4.4: Web UI - Preview Changes (Upload Mode)
**Steps:**
1. After uploading files
2. Click "Preview Changes" button

**Expected:**
- ✅ Results section appears (Step 3)
- ✅ Stats show: Total, To Rename, Skipped, Errors
- ✅ Results list shows: old name → new name
- ✅ "Rename Files" button becomes enabled

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 4.5: Web UI - Rename Files (Upload Mode)
**Steps:**
1. After preview
2. Click "Rename Files" button in results section
3. Confirm dialog

**Expected:**
- ✅ Confirmation dialog appears
- ✅ After confirming, files renamed
- ✅ "Download Renamed Files" button appears
- ✅ Success toast notification

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 4.6: Web UI - Download Renamed Files
**Steps:**
1. After renaming
2. Click "Download Renamed Files" button

**Expected:**
- ✅ ZIP file downloads
- ✅ Filename: renamed-files-YYYY-MM-DD.zip
- ✅ ZIP contains renamed MP3 files

**Verification:**
```bash
cd ~/Downloads
unzip -l renamed-files-*.zip
# Should list renamed files
```

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 4.7: Web UI - Local Directory Mode
**Steps:**
1. Click "Local Directory" mode button
2. Type path: `~/Desktop/dj_test_files`
3. Click "Process Directory" button

**Expected:**
- ✅ Path input visible
- ✅ Quick access buttons visible (Music, Documents, Downloads, Desktop)
- ✅ Preview appears after clicking "Process Directory"
- ✅ "Rename Files" button appears in results

**Note:** This may show error about path validation if security restrictions apply.

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 4.8: Web UI - Theme Toggle
**Steps:**
1. Click theme toggle button (sun/moon icon)
2. Observe color change
3. Refresh page

**Expected:**
- ✅ Colors switch from light to dark (or vice versa)
- ✅ Smooth transition
- ✅ Theme persists after refresh
- ✅ Icon changes (sun ↔ moon)

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 4.9: Web UI - Start New Batch
**Steps:**
1. After completing upload/rename workflow
2. Click "Start New Batch" button

**Expected:**
- ✅ Returns to upload section
- ✅ All fields cleared
- ✅ Ready for new files

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 4.10: Web UI - Custom Template
**Steps:**
1. Upload files
2. Change template to: `{bpm} - {key} - {artist} - {title}`
3. Click "Preview Changes"

**Expected:**
- ✅ Results show custom format
- ✅ BPM and key appear first

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 4.11: Stop Web Server
**Steps:**
1. Go to terminal where server is running
2. Press `Ctrl+C`

**Expected:**
- ✅ Server stops cleanly
- ✅ No errors

**Pass/Fail:** _____ | **Notes:** _____________________

---

## Test Suite 5: Edge Cases & Error Handling

### Test 5.1: Special Characters in Filenames
```bash
cd ~/Desktop/dj_test_files
touch "Artist: Song (Remix) [2024].mp3"
touch "Track / with / slashes.mp3"
touch 'Track "with" quotes.mp3'

# Test with CLI
python3 /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/dj_mp3_renamer.py . --dry-run -v
```

**Expected:**
- ✅ Special characters sanitized
- ✅ No crashes
- ✅ Safe filenames generated

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 5.2: Very Long Filenames
```bash
cd ~/Desktop/dj_test_files
touch "$(printf 'A%.0s' {1..200}).mp3"

python3 /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/dj_mp3_renamer.py . --dry-run -v
```

**Expected:**
- ✅ Filename truncated to 140 characters
- ✅ No crash

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 5.3: Unicode Characters
```bash
cd ~/Desktop/dj_test_files
touch "Björk - Song Title.mp3"
touch "Café del Mar - Track.mp3"
touch "日本語のファイル.mp3"

python3 /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/dj_mp3_renamer.py . --dry-run -v
```

**Expected:**
- ✅ Unicode characters normalized
- ✅ Readable output
- ✅ No mojibake

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 5.4: File Name Collisions
```bash
cd ~/Desktop/dj_test_files
# Create two files that would rename to same name
# (This requires files with same artist/title but different original names)
# Test that collision detection adds _2, _3, etc.
```

**Expected:**
- ✅ Second file gets suffix: filename_2.mp3
- ✅ No files overwritten
- ✅ Warning in output

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 5.5: Read-Only Files
```bash
cd ~/Desktop/dj_test_files
touch readonly.mp3
chmod 444 readonly.mp3

python3 /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/dj_mp3_renamer.py . --dry-run -v
```

**Expected:**
- ✅ Dry-run works
- ✅ Actual rename would fail gracefully

**Cleanup:**
```bash
chmod 644 readonly.mp3
```

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 5.6: Large Batch (Performance)
```bash
# Create 50 test files
cd ~/Desktop/dj_test_files
for i in {1..50}; do
    cp "$(ls *.mp3 | head -1)" "test_$i.mp3" 2>/dev/null || touch "test_$i.mp3"
done

# Time the operation
time python3 /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/dj_mp3_renamer.py . --dry-run
```

**Expected:**
- ✅ Processes all 50 files
- ✅ Completes in reasonable time (< 10 seconds)
- ✅ No crashes or slowdowns

**Pass/Fail:** _____ | **Notes:** _____________________

---

## Test Suite 6: Template Tokens

### Test 6.1: All Token Types
```bash
# Create a test with a real MP3 that has full metadata
# Or use your Bebel Gilberto files which should have tags

python3 /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/dj_mp3_renamer.py \
  ~/Desktop/dj_test_files \
  --template "{track} - {artist} - {title} - {album} - {year} - {label} - {bpm} - {key} - {camelot}" \
  --dry-run -v
```

**Expected:**
- ✅ All tokens replaced with actual values or left empty
- ✅ No "{token}" left in output (unless value is missing)

**Pass/Fail:** _____ | **Notes:** _____________________

---

### Test 6.2: Conditional Tokens (mix_paren, kb)
**Test with file that has mix:**
```bash
# File: "Artist - Title (Extended Mix).mp3"
# Template: "{artist} - {title}{mix_paren}"
# Expected: "Artist - Title (Extended Mix).mp3"
```

**Test with file that has no mix:**
```bash
# File: "Artist - Title.mp3"
# Template: "{artist} - {title}{mix_paren}"
# Expected: "Artist - Title.mp3" (no space before .mp3)
```

**Expected:**
- ✅ {mix_paren} only adds " (Mix)" if mix exists
- ✅ {kb} only adds " [Key BPM]" if both exist

**Pass/Fail:** _____ | **Notes:** _____________________

---

## Test Suite 7: Cleanup

### Test 7.1: Remove Test Files
```bash
rm -rf ~/Desktop/dj_test_files
rm -rf ~/Desktop/dj_test_files_backup
rm -rf ~/Desktop/empty_dir
rm -f ~/Desktop/rename_log.txt
```

**Expected:**
- ✅ All test files removed

**Pass/Fail:** _____ | **Notes:** _____________________

---

## Summary Checklist

After completing all tests, verify:

- [ ] **TUI:** Launches, previews, renames successfully
- [ ] **CLI:** All flags work, dry-run and actual rename work
- [ ] **API:** Programmatic usage works
- [ ] **Web UI:** Uploads, previews, renames (optional)
- [ ] **Error Handling:** Invalid paths, empty dirs handled gracefully
- [ ] **Edge Cases:** Special chars, unicode, collisions handled
- [ ] **Templates:** All tokens work, custom templates work
- [ ] **Performance:** Handles 50+ files without issues

---

## Test Results Summary

**Date Tested:** _______________
**Total Tests:** 70+
**Tests Passed:** _____
**Tests Failed:** _____
**Tests Skipped:** _____

**Critical Issues Found:**
1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

**Minor Issues Found:**
1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

**Overall Assessment:**
- [ ] Ready for production use
- [ ] Needs minor fixes
- [ ] Needs major fixes

**Tester Signature:** _______________

---

## Quick Test (5 Minutes)

If you're short on time, run these essential tests:

1. **TUI Preview & Rename:**
   ```bash
   python run_tui.py
   # Enter path, press P, then R
   ```

2. **CLI Dry-Run:**
   ```bash
   python3 dj_mp3_renamer.py ~/Desktop/dj_test_files --dry-run -v
   ```

3. **API Test:**
   ```bash
   python3 -c "
   from pathlib import Path
   from dj_mp3_renamer.api import RenamerAPI, RenameRequest
   api = RenamerAPI()
   req = RenameRequest(path=Path('~/Desktop/dj_test_files').expanduser(), dry_run=True)
   status = api.rename_files(req)
   print(f'Total: {status.total}, Renamed: {status.renamed}')
   "
   ```

**If all 3 pass:** ✅ Core functionality working

---

**Good luck with testing!** 🧪
