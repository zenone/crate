# Bug Analysis - 2026-01-30

**Session**: Post-browser connection fix
**Issues Found**: 2 critical bugs

---

## Bug #1: Smart Track Detection Banner Not Appearing

### Status
🔴 **CRITICAL** - Feature completely non-functional

### Symptom
User loaded 12-track Alabama Shakes album with sequential track numbers (01-12) but no smart suggestion banner appeared, even though the feature is enabled in settings.

### Root Cause
**Timing issue**: Smart detection runs BEFORE metadata is loaded.

**Code Flow**:
1. Files are loaded and rows created (`createFileRow()` at line 803-806)
2. Each row triggers async metadata loading (`loadFileMetadata()` at line 999)
3. Metadata loads in background and stores to `file.metadata` (line 1023)
4. **BUT**: `analyzeAndShowSuggestion()` is called immediately at line 825
5. Smart detection tries to analyze files with NO metadata (line 2436-2442)
6. Empty album tags + no track numbers = classified as SINGLES
7. SINGLES context = no banner shown

**File References**:
- `web/static/js/app.js:825` - Smart detection called too early
- `web/static/js/app.js:999` - Metadata loads asynchronously
- `web/static/js/app.js:1023` - Metadata stored to file object
- `web/static/js/app.js:2436-2442` - Smart detection expects metadata

### Impact
- Smart Track Detection feature completely broken
- No album suggestions ever shown
- Users miss the benefit of automatic template suggestions

### Fix Options

**Option 1**: Wait for all metadata before calling smart detection
```javascript
// After line 806
for (const file of this.currentFiles) {
    const row = await this.createFileRow(file);
    tbody.appendChild(row);
}

// NEW: Wait for all metadata to load
await Promise.all(this.currentFiles.map(f =>
    this.waitForMetadata(f.path)
));

// THEN call smart detection
if (!sessionStorage.getItem('smart-suggestion-dismissed')) {
    await this.analyzeAndShowSuggestion();
}
```

**Option 2**: Move smart detection to after metadata loading completes
- Track when all metadata requests finish
- Call `analyzeAndShowSuggestion()` from the last metadata callback

**Option 3**: Make smart detection request metadata from API
- Change `analyzeAndShowSuggestion()` to call `/api/files` endpoint with full metadata
- Don't rely on client-side cached metadata

### Recommended Fix
**Option 1** - Most reliable, cleanest code, ensures metadata is available.

### Test Case
1. Load Alabama Shakes album (12 tracks, sequential 01-12)
2. Enable Smart Track Detection in settings
3. Expected: Banner shows "Complete album with sequential tracks detected"
4. Actual (before fix): No banner appears

---

## Bug #2: "Preview Generation Failed" Error on Every Preview

### Status
🟡 **HIGH PRIORITY** - Confusing UX, but feature works

### Symptom
User sees yellow warning notification "Preview generation failed. You can still rename files." every time previews are loaded, even though:
- Green success notification also appears: "Loaded previews for 12 file(s)"
- Preview column shows correct renamed filenames
- No actual failure occurs

### Suspected Root Cause
**Code structure issue**: Operations outside try-catch blocks in `loadAllPreviews()`.

**Code Flow**:
1. Auto-load triggers after files load (line 815)
2. `loadAllPreviews()` is called
3. Line 1212: `showPreviewProgress()` called OUTSIDE try block
4. Lines 1214-1259: Try block succeeds, shows success message
5. Lines 1265-1270: Finally block references undefined `loadBtn` variable
6. Something throws error after try block
7. Error caught by outer catch block at line 816
8. Warning message shown at line 818

**File References**:
- `web/static/js/app.js:815` - Auto-load call
- `web/static/js/app.js:818` - Warning message displayed
- `web/static/js/app.js:1212` - Operation outside try-catch
- `web/static/js/app.js:1266-1269` - References undefined `loadBtn`

### Impact
- Confusing user experience (success + error messages)
- Users may think feature is broken
- Reduced confidence in application reliability

### Debugging Needed
Need browser console output to see actual error:
```
Console should show: "Preview auto-load failed: [actual error]"
```

This will reveal what's actually throwing.

### Likely Fixes
1. Move `showPreviewProgress()` inside try block
2. Remove or fix `loadBtn` reference in finally block (undefined variable)
3. Wrap entire function body in try-catch

### Test Case
1. Load directory with MP3 files
2. Wait for auto-preview to load
3. Expected: Only success notification
4. Actual: Success + warning notifications

---

## Additional Findings

### MusicBrainz Badge Display (✅ RESOLVED)
- **Question**: Will MusicBrainz show as separate badge in SOURCE column?
- **Answer**: YES - when MusicBrainz provides data, it shows as "MusicBrainz" badge
- **Why user sees "ID3 + AI"**: MusicBrainz didn't have BPM/Key for their files (common), so system fell back to audio analysis
- **Code Reference**: `crate/core/audio_analysis.py:310, 316`

### SOURCE Column Naming (✅ RESOLVED)
- **Question**: Keep "SOURCE" (singular) or change to "SOURCES" (plural)?
- **Recommendation**: Keep "SOURCE" (singular) - standard in data/metadata contexts
- **Reasoning**: Refers to the source tracking system, not count of individual sources

---

## Priority Ranking

1. **🔴 CRITICAL**: Bug #1 (Smart Detection) - Feature completely broken
2. **🟡 HIGH**: Bug #2 (Preview Error) - Confusing UX but works
3. **✅ DONE**: MusicBrainz question answered
4. **✅ DONE**: SOURCE naming question answered

---

## Next Steps

1. **Fix Smart Detection** (Bug #1)
   - Implement Option 1: Wait for metadata before running analysis
   - Test with Alabama Shakes album
   - Verify banner appears with correct suggestion

2. **Debug Preview Error** (Bug #2)
   - Request browser console output from user
   - Identify actual error being thrown
   - Apply appropriate fix based on error

3. **Manual Testing**
   - Test all 18 features from previous session
   - Verify Smart Detection works correctly
   - Confirm no preview errors appear

---

**Documentation Created**: 2026-01-30
**Status**: Analysis complete, fixes identified, awaiting implementation
