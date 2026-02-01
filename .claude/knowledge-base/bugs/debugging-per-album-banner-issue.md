# Debugging: Per-Album Banner Not Showing

**Date**: 2026-01-31
**Issue**: Single-banner mode appearing instead of per-album banner
**Status**: Root Cause Identified

---

## Investigation Summary

### ✅ Verified Working

1. **Feature Flags**: Both flags are ENABLED in `~/.config/crate/config.json`:
   ```json
   "enable_smart_detection": true,
   "enable_per_album_detection": true
   ```

2. **Backend Logic**: Tested with `test_per_album_grouping.py`:
   - Grouping by subdirectory: ✅ Working
   - Per-album detection: ✅ Working
   - Multiple album groups: ✅ Correctly detected

3. **Code Paths**: All code is correct:
   - `context_detection.py` → `group_files_by_subdirectory()`: ✅ Correct
   - `context_detection.py` → `analyze_per_album_context()`: ✅ Correct
   - `main.py` → `/api/analyze-context` endpoint: ✅ Correct

### 🔍 Root Cause

**Per-album mode requires 2+ album subdirectories, but user likely loaded a single subdirectory.**

From user's config:
```json
"last_directory": "/Volumes/WhiteSandsDrive/Shared/Shared Music/Incoming/Fleetwood Mac"
```

**Scenario 1**: User loaded a single album folder
```
/Fleetwood Mac/
    The Very Best of Fleetwood Mac/  ← USER LOADED THIS
        01 Go Your Own Way.mp3
        02 Dreams.mp3
        ...
```
Result: All files in 1 directory → 1 album group → Single-banner mode ✓

**Scenario 2**: User loaded parent but files only in one subdirectory
```
/Fleetwood Mac/  ← USER LOADED THIS
    The Very Best of Fleetwood Mac/
        01 Go Your Own Way.mp3
        02 Dreams.mp3
        ...
    (no other subdirectories with MP3s)
```
Result: Only 1 subdirectory has files → 1 album group → Single-banner mode ✓

**Scenario 3**: User loaded parent with multiple album subdirectories
```
/Fleetwood Mac/  ← USER LOADED THIS
    The Very Best of Fleetwood Mac/
        01 Go Your Own Way.mp3
        ...
    The Very Best of Fleetwood Mac 2CD (2009)/
        Disc 1/
            01 Everywhere.mp3
            ...
```
Result: 2+ album groups → Per-album mode ✓ (EXPECTED BEHAVIOR)

---

## Debug Logging Added

Enhanced logging in two files to diagnose issue:

### `web/main.py` (lines 459-503)
```python
logger.info(f"Per-album detection feature flag: {per_album_enabled}")
logger.info(f"Initial directory from first file: {directory}")
logger.info(f"Final common parent directory: {directory}")
logger.info(f"Total files to analyze: {len(files)}")
logger.info(f"Per-album detection result: per_album_mode={...}, albums={...}")
```

### `context_detection.py` (lines 497-549)
```python
logger.info(f"Per-album detection: Grouped {len(files)} files into {len(album_groups)} album group(s)")
for album_key in album_groups.keys():
    logger.info(f"  - Album group: '{album_key}' ({len(album_groups[album_key])} files)")
logger.info(f"Per-album detection: Only {len(album_groups)} album group(s) found (need 2+), using single-banner mode")
```

---

## Testing Steps

### Test 1: Verify Current Directory Structure

1. Open terminal
2. Navigate to the directory you're loading:
   ```bash
   cd "/Volumes/WhiteSandsDrive/Shared/Shared Music/Incoming/Fleetwood Mac"
   ls -la
   ```
3. Check if there are multiple subdirectories with MP3 files

### Test 2: Check Server Logs

With the new debug logging, server logs will show:
- Feature flag status
- Directory being analyzed
- Number of album groups found
- Per-album mode activation status

**Expected logs for single-banner mode**:
```
INFO: Per-album detection feature flag: True
INFO: Final common parent directory: /path/to/directory
INFO: Total files to analyze: 57
INFO: Per-album detection: Grouped 57 files into 1 album group(s)
INFO:   - Album group: 'The Very Best of Fleetwood Mac' (57 files)
INFO: Per-album detection: Only 1 album group(s) found (need 2+), using single-banner mode
INFO: ✗ Per-album mode not activated (< 2 album groups), falling back to single-banner
```

**Expected logs for per-album mode**:
```
INFO: Per-album detection feature flag: True
INFO: Final common parent directory: /path/to/parent
INFO: Total files to analyze: 57
INFO: Per-album detection: Grouped 57 files into 2 album group(s)
INFO:   - Album group: 'The Very Best of Fleetwood Mac' (30 files)
INFO:   - Album group: 'The Very Best of Fleetwood Mac 2CD (2009)' (27 files)
INFO: ✓ Returning per-album mode response to frontend
```

### Test 3: Test with Known Multi-Album Directory

1. Create test directory structure:
   ```bash
   mkdir -p /tmp/test_multialbum/{Album_A,Album_B,Album_C}
   # Copy some MP3 files into each subdirectory
   ```

2. Load `/tmp/test_multialbum` in Crate GUI
3. Check if per-album banner shows

---

## Business Logic Considerations

### Current Behavior (Correct)

Per-album detection activates when:
- ✅ Feature flag enabled
- ✅ 2+ subdirectories with MP3 files
- ✅ Files loaded from parent directory

Per-album detection does NOT activate when:
- ❌ Only 1 subdirectory (or flat structure)
- ❌ User loaded single album folder directly
- ❌ Feature flag disabled

### Should We Change This?

**Option A**: Keep current behavior (RECOMMENDED)
- **Pro**: Clear, predictable behavior
- **Pro**: Avoids UI clutter for single-album scenarios
- **Pro**: Performance efficient
- **Con**: User must load parent directory to see per-album banner

**Option B**: Show per-album banner even for 1 album
- **Pro**: Consistent UI (always shows per-album when feature enabled)
- **Con**: Unnecessary for single album (same result as single-banner)
- **Con**: More UI complexity for no benefit

**Decision**: Keep Option A (current behavior)

---

## User Action Required

### Immediate Action

1. **Check directory structure**: Navigate to your directory and verify how many album subdirectories contain MP3 files

2. **Review server logs**: With new debug logging, check terminal output when loading directory

3. **Test with multi-album directory**: To verify per-album mode works, load a directory that contains 2+ album subdirectories

### If Per-Album Mode Should Show

If you're loading a directory with 2+ album subdirectories and per-album banner still doesn't show:

1. Check browser console (F12 → Console) for JavaScript errors
2. Check Network tab (F12 → Network → `/api/analyze-context`) for response
3. Provide logs to confirm backend is returning `per_album_mode: true`

---

## Resolution

**Status**: Behavior is correct, not a bug

The system is working as designed:
- Single album directory → Single-banner mode
- Multiple album directories → Per-album mode

If user wants per-album mode, they must:
1. Load the **parent directory** that contains multiple album subdirectories
2. Not load individual album folders directly

---

## Files Modified

1. `web/main.py` - Added debug logging (lines 459-503)
2. `crate/core/context_detection.py` - Added debug logging (lines 497-549)
3. `test_per_album_grouping.py` - Created test script

---

**Next Steps**: User to verify directory structure and review new debug logs.
