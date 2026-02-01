# Bug Report: Rename Button Remains Active with No Files Selected

**Date**: 2026-01-30
**Severity**: HIGH
**Priority**: HIGH
**Status**: Open (Task #58 created)

---

## Description

The "Rename Now" button remains active (clickable) when all files are unchecked after generating a preview. This could lead users to accidentally rename files they didn't intend to modify.

---

## Steps to Reproduce

1. Load a directory with MP3 files
2. Generate preview for files (preview column populates)
3. Observe: "Rename Now" button becomes active
4. Uncheck ALL files (selection count = 0)
5. Observe: "Rename Now" button remains active (BUG)
6. Click "Rename Now"
7. Result: Attempts to rename ALL previewed files (not just selected ones)

---

## Expected Behavior

**Step 4 Expected**: When all files are unchecked (selection count = 0):
- "Rename Now" button should become disabled/grayed out
- Button should display disabled state visually
- Tooltip should indicate "No files selected"

**Button State Logic**:
```
IF preview_generated AND selected_count > 0:
    button.enabled = true
ELSE:
    button.enabled = false
```

---

## Current Behavior

**Incorrect Logic**:
```
IF preview_generated:
    button.enabled = true  # WRONG - ignores selection count
```

Button state appears to be tied only to preview completion, not selection count.

---

## Root Cause Analysis

### Likely Issues

**1. Checkbox Event Handler Missing State Update**:
```javascript
// Current (likely)
checkbox.addEventListener('change', (e) => {
    // Updates selection array
    // Does NOT update button state
});

// Should be
checkbox.addEventListener('change', (e) => {
    this.updateSelection();
    this.updateRenameButtonState();  // MISSING
});
```

**2. Button State Function Missing Selection Check**:
```javascript
// Current (likely)
updateRenameButtonState() {
    const hasPreview = this.previewGenerated;
    button.disabled = !hasPreview;  // WRONG - ignores selection
}

// Should be
updateRenameButtonState() {
    const hasPreview = this.previewGenerated;
    const hasSelection = this.getSelectedFiles().length > 0;
    button.disabled = !(hasPreview && hasSelection);  // CORRECT
}
```

**3. Backend Not Validating File Count**:
```python
# Current (possibly)
@app.post("/api/rename")
async def rename_files(request: RenameRequest):
    # May not validate file_paths.length > 0
    for file in request.file_paths:
        ...

# Should validate
@app.post("/api/rename")
async def rename_files(request: RenameRequest):
    if len(request.file_paths) == 0:
        raise HTTPException(400, "No files selected")
```

---

## Impact

**Severity**: HIGH

**User Impact**:
- Risk of accidental bulk rename of unintended files
- Confusing UX (button active when nothing selected)
- Potential data loss if user clicks rename accidentally

**Frequency**: Every time user unchecks all files after preview

---

## Proposed Fix

### Backend (API First) - `web/main.py`

**Add validation to /api/rename endpoint**:
```python
@app.post("/api/rename")
async def rename_files(request: ExecuteRenameRequest):
    # Validate file_paths array
    if not request.file_paths or len(request.file_paths) == 0:
        raise HTTPException(
            status_code=400,
            detail="No files selected for rename operation"
        )

    # Continue with existing logic
    ...
```

**Test**:
```python
def test_rename_empty_files_returns_400():
    response = client.post("/api/rename", json={
        "path": "/test/path",
        "file_paths": [],  # Empty array
        "template": "{artist} - {title}"
    })
    assert response.status_code == 400
    assert "No files selected" in response.json()["detail"]
```

### Frontend - `web/static/js/app.js`

**1. Add updateRenameButtonState() method**:
```javascript
updateRenameButtonState() {
    const renameBtn = document.getElementById('rename-now-btn');
    const previewBtn = document.getElementById('preview-btn');

    const selectedFiles = this.getSelectedFiles();
    const hasSelection = selectedFiles.length > 0;
    const hasPreview = this.previewGenerated;

    // Rename button: needs preview AND selection
    renameBtn.disabled = !(hasPreview && hasSelection);

    // Preview button: needs selection only
    previewBtn.disabled = !hasSelection;

    // Update button text with count
    if (hasSelection) {
        renameBtn.textContent = `✅ Rename Now (${selectedFiles.length})`;
    } else {
        renameBtn.textContent = `✅ Rename Now`;
    }
}
```

**2. Call updateRenameButtonState() in checkbox handlers**:
```javascript
// In setupFileListListeners() or similar
document.querySelectorAll('.file-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', () => {
        this.updateSelection();
        this.updateRenameButtonState();  // ADD THIS
    });
});

// In select-all checkbox handler
document.getElementById('select-all').addEventListener('change', (e) => {
    this.toggleSelectAll(e.target.checked);
    this.updateRenameButtonState();  // ADD THIS
});
```

**3. Call after preview generation**:
```javascript
async loadAllPreviews() {
    // ... preview generation logic ...

    this.previewGenerated = true;
    this.updateRenameButtonState();  // ADD THIS
}
```

### Frontend - User Feedback

**Add tooltip when button disabled**:
```javascript
updateRenameButtonState() {
    // ... existing logic ...

    if (!hasSelection) {
        renameBtn.title = "Select files to rename";
    } else if (!hasPreview) {
        renameBtn.title = "Generate preview first";
    } else {
        renameBtn.title = "Rename selected files";
    }
}
```

---

## Test Plan

### Unit Tests

**Backend**:
```python
def test_rename_with_empty_files():
    """API should reject empty file_paths array"""

def test_rename_with_valid_files():
    """API should accept non-empty file_paths array"""
```

**Frontend** (manual):
1. Load files → Preview → Check button enabled
2. Uncheck all → Check button disabled
3. Check one file → Check button enabled
4. Uncheck that file → Check button disabled
5. Use Select All → Check button enabled
6. Uncheck Select All → Check button disabled

### Integration Test

**Full Workflow**:
1. Load directory (100 files)
2. Select 10 files
3. Generate preview
4. Verify: Rename button active
5. Uncheck 5 files (5 remaining)
6. Verify: Rename button still active
7. Uncheck all files (0 selected)
8. Verify: Rename button disabled
9. Try to click (should be prevented)
10. Check 3 files
11. Verify: Rename button active again
12. Click Rename
13. Verify: Only 3 files renamed

---

## Related Issues

- May also affect "Preview Rename" button logic
- Similar pattern might exist in other file operations
- Consider adding selection count display: "5 files selected"

---

## Files to Modify

1. **web/main.py** - Add validation to /api/rename endpoint
2. **web/static/js/app.js** - Add updateRenameButtonState() method
3. **web/static/js/app.js** - Call updateRenameButtonState() in checkbox handlers
4. **tests/test_api.py** - Add test for empty file_paths validation

---

## Estimated Fix Time

- Backend validation: 10 minutes
- Frontend button logic: 15 minutes
- Testing: 10 minutes
- Documentation: 5 minutes

**Total**: 30-40 minutes

---

## Priority Justification

**HIGH Priority** because:
1. User could accidentally rename wrong files (data integrity risk)
2. Confusing UX (button active when nothing to do)
3. Easy to fix (< 1 hour)
4. Affects core rename functionality
5. Reproducible 100% of the time

---

**Created**: 2026-01-30
**Reported By**: User
**Assigned To**: Task #58
**Target**: Fix before next deployment
