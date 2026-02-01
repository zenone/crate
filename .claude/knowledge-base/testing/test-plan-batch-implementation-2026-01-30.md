# Test Plan: Batch Implementation - 2026-01-30

**Date**: 2026-01-30
**Tasks Implemented**: #100, #101, #89, #84
**Status**: Ready for User Testing

---

## Overview

This test plan covers 4 new features implemented in a single batch:

1. **Task #100**: Disc number support for multi-disc albums
2. **Task #101**: Filename fallback for missing track numbers
3. **Task #89**: Cancel button on preview loading
4. **Task #84**: Remember last directory with intelligent fallback

Plus verification of previously completed v16 fix:
- **Task #99**: Rename operations using temporary template (RETEST Test 5)

---

## Test Environment Setup

**Prerequisites**:
- Fresh server restart to load all changes
- Clear browser cache (or use cache-busted URLs)
- Test data prepared (see each test case)

**How to Restart Server**:
```bash
# Stop current server (Ctrl+C in terminal)
# Start again
cd /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename
python -m web.main
```

---

## Test Case 1: v16 Fix - Rename Operations Use Temporary Template (RETEST)

**Priority**: CRITICAL
**Task**: #99
**Estimated Time**: 3 minutes

### Objective
Verify that rename operations now use the temporary Smart Track Detection template (previously failed in Test 5).

### Setup
1. Ensure custom template is set in settings: `{artist} - {title} [{camelot} {bpm}]`
2. Load directory with album that triggers Smart Track Detection (e.g., Big Audio Dynamite)

### Steps
1. Wait for Smart Track Detection banner to appear
2. Banner should suggest: `{track} - {artist} - {title}`
3. Click "Use This" button
4. Verify toast notification: "Temporary template applied: {track} - {artist} - {title} (not saved to settings)"
5. Verify preview column shows track numbers (e.g., "01 - Big Audio Dynamite - Medicine Show.mp3")
6. Select all files (should auto-select)
7. Click "Rename Now" (either from main page or preview modal)
8. Wait for rename to complete

### Expected Results
✅ Files renamed WITH track numbers using Smart Track Detection template:
   - "01 - Big Audio Dynamite - Medicine Show.mp3"
   - "02 - Big Audio Dynamite - Sony.mp3"
   - "03 - Big Audio Dynamite - E=mc2.mp3"
   - etc.

✅ Console log shows: "Using temporary template from Smart Track Detection for rename: {track} - {artist} - {title}"

✅ Result message: "Complete! Renamed 8 of 8 files" (or similar)

### Failure Criteria
❌ Files renamed WITHOUT track numbers (using settings template)
❌ Files renamed as: "Big Audio Dynamite - Medicine Show [12B 117].mp3"
❌ Console shows: "Using template from settings for rename"

### Notes
- This was Test 5 from previous session that FAILED in v15
- Should now PASS in v16

---

## Test Case 2: Disc Number Support - Multi-Disc Album

**Priority**: HIGH
**Task**: #100
**Estimated Time**: 5 minutes

### Objective
Verify that multi-disc albums are correctly detected and each disc is analyzed separately.

### Setup
Prepare test data with multi-disc album structure:
```
Test Album/
  Disc 1/
    01 - Artist - Track 1.mp3  (ID3: Album="Test Album", Disc=1, Track=1)
    02 - Artist - Track 2.mp3  (ID3: Album="Test Album", Disc=1, Track=2)
    03 - Artist - Track 3.mp3  (ID3: Album="Test Album", Disc=1, Track=3)
  Disc 2/
    01 - Artist - Track 4.mp3  (ID3: Album="Test Album", Disc=2, Track=1)
    02 - Artist - Track 5.mp3  (ID3: Album="Test Album", Disc=2, Track=2)
```

**Note**: If you don't have multi-disc albums with disc numbers in ID3, you can:
- Use a music library manager (Mp3tag, MusicBrainz Picard) to set TPOS tags
- Or **skip this test case** and just verify no regression on single-disc albums

### Steps
1. Load the multi-disc album directory
2. Observe Smart Track Detection analysis

### Expected Results
✅ Each disc detected separately as ALBUM:
   - Disc 1: Sequential tracks 1-3 → suggests `{track} - {artist} - {title}`
   - Disc 2: Sequential tracks 1-2 → suggests `{track} - {artist} - {title}`

✅ No error about "duplicate track numbers"

✅ Smart Track Detection banner appears (for at least one disc)

✅ When "Use This" clicked, previews show track numbers correctly per disc

### Failure Criteria
❌ Multi-disc album classified as "non-sequential" or "singles"
❌ Error about duplicate track numbers
❌ Smart Track Detection doesn't appear

### Fallback Test (No Multi-Disc Albums Available)
If you don't have multi-disc test data:
1. Load any single-disc album with sequential tracks
2. Verify Smart Track Detection still works (no regression)
3. Verify files rename correctly with track numbers

---

## Test Case 3: Filename Fallback for Track Numbers

**Priority**: LOW
**Task**: #101
**Estimated Time**: 5 minutes

### Objective
Verify that track numbers are extracted from filenames when ID3 tags are missing.

### Setup
Prepare test files with track numbers in filename but NO track number in ID3 tags:
```
Test Files/
  03 - Test Artist - Test Title.mp3  (ID3: NO TRCK tag)
  04 - Test Artist - Another Title.mp3  (ID3: NO TRCK tag)
  05. Test Artist - Third Title.mp3  (ID3: NO TRCK tag)
```

**How to Remove Track Numbers from ID3**:
- Use Mp3tag or similar tool
- Or rename existing files and skip this test if too complex

### Steps
1. Load directory with files that have track numbers in filename but not in ID3
2. Enable Smart Track Detection (Settings → Enable Smart Track Detection)
3. Load the test directory
4. Check browser console logs for: "Extracted track number from filename: 03"

### Expected Results
✅ Console logs show track numbers extracted from filenames

✅ Smart Track Detection analyzes the files as if they had track numbers in ID3

✅ If sequential (03, 04, 05), banner suggests album template

✅ Preview and rename work correctly using extracted track numbers

### Failure Criteria
❌ Smart Track Detection says "no track numbers found"
❌ Files not detected as sequential album

### Fallback Test
If too complex to prepare test data:
1. Verify that normal files (with ID3 track numbers) still work correctly
2. Check that ID3 tags take precedence over filename (optional)

---

## Test Case 4: Cancel Button on Preview Loading

**Priority**: MEDIUM
**Task**: #89
**Estimated Time**: 3 minutes

### Objective
Verify that preview loading can be cancelled mid-operation.

### Setup
1. Load directory with many files (50+ MP3s if possible)
2. Ensure you have a template set that requires preview generation

### Steps
1. Load directory with many files
2. Click "Preview Rename" button (or let auto-preview trigger)
3. Preview loading indicator appears with spinner and "Loading preview..." text
4. **Immediately** click the "Cancel" button that now appears below the loading text
5. Observe the result

### Expected Results
✅ "Cancel" button is visible below "Loading preview..." spinner

✅ Clicking Cancel stops the preview loading immediately

✅ Loading indicator disappears

✅ Toast notification shows: "Preview loading cancelled"

✅ No error messages in console (except maybe AbortError which is expected)

✅ App remains functional - can start new preview loading

### Failure Criteria
❌ Cancel button not visible
❌ Cancel button doesn't work (loading continues)
❌ Error messages shown to user after cancel

### Alternative Test (Few Files)
If you only have few files (preview loads too fast to cancel):
1. Just verify Cancel button is visible when loading starts
2. Test that it doesn't break anything if clicked after loading completes

---

## Test Case 5: Remember Last Directory

**Priority**: MEDIUM
**Task**: #84
**Estimated Time**: 10 minutes

### Objective
Verify that the app remembers and auto-loads the last browsed directory on startup.

### Test 5a: Normal Flow (Directory Still Exists)

#### Steps
1. Start app (fresh browser session if possible)
2. Browse to a specific directory (e.g., `/Users/szenone/Music/Test Album 1`)
3. Verify directory loads and files appear
4. **Stop and restart the server** (Ctrl+C, then restart)
5. **Refresh browser** (or open new tab to app)
6. Observe what happens on startup

#### Expected Results
✅ App auto-loads the last directory: `/Users/szenone/Music/Test Album 1`

✅ Directory path input shows the correct path

✅ Files from that directory are displayed immediately

✅ Console log shows: "Restored last directory: /Users/szenone/Music/Test Album 1"

✅ No toast notification (silent restore is expected behavior)

#### Failure Criteria
❌ App loads home directory instead
❌ Directory input is empty
❌ No files loaded

### Test 5b: Directory Deleted (Fallback to Parent)

#### Steps
1. Browse to a subdirectory (e.g., `/Users/szenone/Music/Test Album 1/Subfolder`)
2. Stop server
3. **Delete or rename the subdirectory** (so path no longer exists)
4. Restart server and refresh browser
5. Observe what happens

#### Expected Results
✅ App loads the parent directory: `/Users/szenone/Music/Test Album 1`

✅ Warning toast shown: "Previous directory no longer exists. Loaded parent folder."

✅ Console log shows fallback occurred

✅ App is still functional

#### Failure Criteria
❌ Error message or crash
❌ App loads home directory (should walk up to parent first)

### Test 5c: Feature Disabled in Settings

#### Steps
1. Browse to any directory
2. Open Settings (⚙️ icon)
3. **Uncheck** "Remember Last Directory" checkbox
4. Click "Save" button
5. Stop and restart server
6. Refresh browser
7. Observe startup behavior

#### Expected Results
✅ App loads home directory (doesn't remember)

✅ Last directory setting is ignored

✅ Checkbox remains unchecked in settings

#### Failure Criteria
❌ App still loads last directory even though feature is disabled

### Test 5d: Settings Toggle Persists

#### Steps
1. Open Settings
2. Toggle "Remember Last Directory" checkbox on and off
3. Save settings
4. Reopen settings
5. Verify checkbox state matches what you saved

#### Expected Results
✅ Checkbox state persists across settings modal open/close

✅ Checkbox state persists across server restarts

✅ Feature behaves according to checkbox state

---

## Test Case 6: No Regressions - General Functionality

**Priority**: HIGH
**Estimated Time**: 10 minutes

### Objective
Quick smoke test to ensure existing functionality still works.

### Subtests

#### 6a: Smart Track Detection (v13-v16 fixes)
1. Load album with sequential tracks
2. Verify banner appears
3. Click "Use This" → Files auto-select ✅
4. Click "Ignore" → Files auto-select ✅ (v14 fix)
5. Preview column shows correct template ✅ (v15 fix)
6. Rename works with Smart Track Detection template ✅ (v16 fix)

#### 6b: Basic Rename Operation
1. Load directory
2. Select files manually
3. Enter custom template in settings
4. Preview rename
5. Execute rename
6. Verify files renamed correctly ✅

#### 6c: Undo Operation
1. After rename, undo toast should appear
2. Click "Undo" link
3. Verify files restored to original names ✅

#### 6d: Settings Persistence
1. Change template in settings
2. Save settings
3. Restart server
4. Verify template persisted ✅

---

## Summary Checklist

**CRITICAL (Must Pass)**:
- [ ] Test 1: v16 Rename operations use temporary template
- [ ] Test 6a: Smart Track Detection no regressions
- [ ] Test 6b: Basic rename still works

**HIGH Priority (Should Pass)**:
- [ ] Test 2: Disc number support (or verify no single-disc regression)
- [ ] Test 6c: Undo operation works
- [ ] Test 6d: Settings persist

**MEDIUM Priority (Nice to Have)**:
- [ ] Test 4: Cancel button functional
- [ ] Test 5: Remember last directory all subtests

**LOW Priority (Optional)**:
- [ ] Test 3: Filename fallback (skip if complex to set up)

---

## Reporting Issues

If any test fails, please report:

1. **Test case number and name**
2. **What you expected to happen**
3. **What actually happened**
4. **Screenshots** (if UI-related)
5. **Browser console errors** (F12 → Console tab, copy any red errors)
6. **Steps to reproduce**

---

## Post-Testing

After all tests pass:
1. Mark completed tasks as verified
2. Archive this test plan
3. Update current-status.md with "All features tested and working"
4. Ready for production use!

---

## Quick Test Summary (5-Minute Version)

If short on time, run these essential tests:

1. **v16 Fix** (Test 1): Load album, click "Use This", rename → verify track numbers appear
2. **Cancel Button** (Test 4): Start preview, click Cancel → verify it stops
3. **Remember Directory** (Test 5a): Browse to folder, restart, verify auto-loads
4. **No Regressions** (Test 6): Do one complete rename operation start to finish

**Estimated time**: 5-7 minutes for quick validation
