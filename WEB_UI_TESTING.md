# Web UI Manual Testing Guide

## Prerequisites

```bash
# Ensure you're in project root
cd /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename

# Install web dependencies
pip install -r requirements-web.txt

# Verify installation
python3 -c "from web.server import app; print('✓ Ready')"
```

---

## Test 1: Launch Server

### Test 1a: Basic Launch
```bash
python run_web.py
```

**Expected:**
```
🎵 DJ MP3 Renamer Web UI
📡 Starting server at http://127.0.0.1:8000
✨ Press Ctrl+C to stop

INFO:     Started server process [...]
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Test 1b: Custom Port
```bash
python run_web.py --port 3000
```

**Expected:** Server starts on port 3000

### Test 1c: Development Mode
```bash
python run_web.py --reload
```

**Expected:** Auto-reload enabled, shows file watching

---

## Test 2: UI Loading & Theme

### Test 2a: Open Browser
1. Start server: `python run_web.py`
2. Open: http://localhost:8000
3. Verify page loads with:
   - DJ MP3 Renamer logo (music note icon)
   - Upload section visible
   - Theme toggle button (sun icon)

### Test 2b: Theme Toggle
1. Click theme toggle button (sun icon)
2. **Verify:**
   - Background changes from light to dark
   - Text colors invert appropriately
   - Icon changes from sun to moon
   - Smooth transition (no flash)

3. Refresh page
4. **Verify:** Theme persists (localStorage)

### Test 2c: System Theme
1. Open browser DevTools (F12)
2. Toggle system theme:
   - Chrome: DevTools > More tools > Rendering > Emulate CSS media prefers-color-scheme
   - Firefox: about:config > ui.systemUsesDarkTheme
3. **Verify:** UI updates automatically

### Test 2d: Responsive Design
1. Open DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M)
3. Test at widths:
   - 1920px (desktop)
   - 768px (tablet)
   - 375px (mobile)
4. **Verify:**
   - Layout adapts smoothly
   - No horizontal scroll
   - Buttons stack on mobile
   - Text remains readable

---

## Test 3: File Upload

### Test 3a: Browse Button Upload
1. Click "Browse Files" button
2. Select 2-3 MP3 files from your library
3. **Verify:**
   - Loading spinner appears
   - Files appear in "Uploaded Files" list
   - File names and sizes displayed correctly
   - Config section appears (Step 2)

### Test 3b: Drag & Drop
1. Drag 2-3 MP3 files from file manager
2. Hover over upload zone
3. **Verify:**
   - Upload zone changes appearance (border color, background)
   - "Drag over" state is visible
4. Drop files
5. **Verify:**
   - Upload zone returns to normal
   - Files uploaded successfully
   - Toast notification appears: "Uploaded X file(s) successfully"

### Test 3c: Mixed File Types
1. Try uploading .txt, .jpg, and .mp3 files together
2. **Verify:**
   - Only .mp3 files are processed
   - Non-MP3 files are filtered out

### Test 3d: No Files Selected
1. Click "Browse Files"
2. Click Cancel
3. **Verify:**
   - No error
   - UI stays on upload section

---

## Test 4: Template Configuration

### Test 4a: Default Template
1. Upload files
2. **Verify:**
   - Template input shows: `{artist} - {title}{mix_paren}{kb}`
   - This is the default from the API

### Test 4b: Template Help
1. Click "Available tokens" disclosure
2. **Verify:**
   - Token list expands
   - Shows all tokens with descriptions
   - Tokens displayed in monospace font

### Test 4c: Custom Template
1. Clear template input
2. Type: `{artist} - {bpm} - {title}`
3. **Verify:**
   - Input accepts changes
   - No validation errors

### Test 4d: Empty Template
1. Clear template input completely
2. Click "Preview Changes"
3. **Verify:**
   - Error toast appears: "Please enter a template"

---

## Test 5: Preview Mode (Dry Run)

### Test 5a: Basic Preview
1. Upload files (with actual metadata if possible)
2. Use default template
3. Click "Preview Changes"
4. **Verify:**
   - Loading spinner appears with "Generating preview..."
   - Results section appears (Step 3)
   - Stats show: Total, To Rename, Skipped, Errors
   - Results list shows: old filename → new filename

### Test 5b: Preview with Custom Template
1. Upload files
2. Set template: `{bpm} - {artist} - {title}`
3. Click "Preview Changes"
4. **Verify:**
   - Preview shows new format
   - BPM appears first in new names

### Test 5c: Skipped Files
1. Upload files without metadata (or create fake .mp3 files)
2. Click "Preview Changes"
3. **Verify:**
   - Some files show "Skipped" status
   - Message explains why (e.g., "No readable tags")
   - Skipped count increments

---

## Test 6: Rename Execution

### Test 6a: Confirm Dialog
1. After preview, click "Rename Files"
2. **Verify:**
   - Browser confirmation dialog appears
   - Message: "This will rename your files. Are you sure?"

### Test 6b: Execute Rename
1. Confirm the dialog
2. **Verify:**
   - Loading spinner: "Renaming files..."
   - Results update with actual rename counts
   - Success toast: "Successfully renamed X file(s)"
   - Stats show accurate counts

### Test 6c: Cancel Rename
1. Click "Rename Files"
2. Click "Cancel" in confirmation
3. **Verify:**
   - No action taken
   - Still in preview mode

---

## Test 7: Results Display

### Test 7a: Stats Cards
**Verify:**
- Total count is correct
- Renamed count (green color)
- Skipped count (yellow/warning color)
- Errors count (red color)

### Test 7b: Results List
**Verify:**
- Each result shows old → new filename
- Color coding:
  - Green left border: Success
  - Yellow: Skipped
  - Red: Error
- Results are scrollable if many files

### Test 7c: New Batch Button
1. Click "Start New Batch"
2. **Verify:**
   - Returns to upload section (Step 1)
   - Previous files cleared
   - Template reset
   - Ready for new upload

---

## Test 8: API Endpoints

### Test 8a: Health Check
```bash
curl http://localhost:8000/api/health
```

**Expected:**
```json
{"status":"ok","version":"1.0.0"}
```

### Test 8b: Templates Endpoint
```bash
curl http://localhost:8000/api/templates
```

**Expected:**
```json
{
  "default": "{artist} - {title}{mix_paren}{kb}",
  "tokens": {
    "artist": "Artist name",
    ...
  }
}
```

### Test 8c: API Documentation
1. Visit: http://localhost:8000/docs
2. **Verify:**
   - FastAPI auto-generated docs appear
   - All endpoints listed
   - Can test endpoints interactively

---

## Test 9: Error Handling

### Test 9a: Network Error
1. Stop the server (Ctrl+C)
2. Try uploading files
3. **Verify:**
   - Error toast appears
   - Graceful error message
   - UI doesn't crash

### Test 9b: Invalid Template Tokens
1. Enter template: `{invalid_token}`
2. Click "Preview Changes"
3. **Verify:**
   - Tokens that don't exist stay as-is: `{invalid_token}`
   - No crash

### Test 9c: Large File Count
1. Try uploading 20+ files at once
2. **Verify:**
   - All files upload successfully
   - UI remains responsive
   - Results display properly (scrollable)

---

## Test 10: Architecture Verification

### Test 10a: API Independence
```bash
# Verify API still works without web UI
python3 -c "
from pathlib import Path
from dj_mp3_renamer.api import RenamerAPI, RenameRequest

api = RenamerAPI()
print('✓ API works independently')
"
```

### Test 10b: No API Modifications
```bash
# Check that core API files are unchanged
git diff dj_mp3_renamer/api/
git diff dj_mp3_renamer/core/
```

**Expected:** No changes (or only the original TDD refactoring)

### Test 10c: Web Imports API
```bash
python3 -c "
import web.server
import inspect
source = inspect.getsource(web.server)
if 'from dj_mp3_renamer.api import' in source:
    print('✓ Web UI imports from API (API-first confirmed)')
"
```

---

## Test 11: Browser Console

### Test 11a: No Console Errors
1. Open DevTools Console (F12 → Console tab)
2. Perform all operations (upload, preview, rename)
3. **Verify:**
   - No red error messages
   - Only info/log messages
   - No 404 errors for resources

### Test 11b: Network Tab
1. Open DevTools Network tab
2. Upload files
3. **Verify:**
   - POST to `/api/upload` returns 200
   - Files are in request payload
   - Response includes session_id

---

## Test 12: Accessibility

### Test 12a: Keyboard Navigation
1. Tab through all interactive elements
2. **Verify:**
   - Focus indicators visible
   - Can activate buttons with Enter/Space
   - Logical tab order

### Test 12b: Screen Reader Labels
1. Inspect elements (right-click → Inspect)
2. **Verify:**
   - Buttons have `aria-label` where needed
   - Form inputs have labels
   - Semantic HTML used

### Test 12c: Contrast Ratios
1. Use browser accessibility checker
2. **Verify:**
   - WCAG AA compliance (4.5:1 for text)
   - Both light and dark modes pass

---

## Test 13: Performance

### Test 13a: Load Time
1. Hard refresh (Ctrl+Shift+R)
2. Check Network tab
3. **Verify:**
   - Page loads in < 1 second
   - No large asset downloads
   - Vanilla JS loads fast (no framework overhead)

### Test 13b: Theme Switch Speed
1. Click theme toggle repeatedly
2. **Verify:**
   - Instant response
   - Smooth transition (CSS transitions)
   - No lag

---

## Quick Test Checklist

Use this for rapid verification:

- [ ] Server starts successfully
- [ ] Page loads in browser
- [ ] Theme toggle works (light ↔ dark)
- [ ] Files upload via browse button
- [ ] Files upload via drag & drop
- [ ] Template input accepts text
- [ ] Preview shows results
- [ ] Rename executes successfully
- [ ] Results display correctly
- [ ] "Start New Batch" resets UI
- [ ] No console errors
- [ ] Responsive on mobile viewport
- [ ] API remains unchanged (`git diff dj_mp3_renamer/`)

---

## Troubleshooting

### Server won't start
```bash
# Check if port is in use
lsof -i :8000

# Use different port
python run_web.py --port 8001
```

### Theme doesn't persist
```bash
# Clear localStorage in browser console
localStorage.clear()
location.reload()
```

### Files don't upload
- Verify `web/uploads/` directory exists
- Check file extensions (.mp3 only)
- Check browser console for errors

### API import error
```bash
# Ensure you're in project root
pwd  # Should show: .../batch_rename

# Verify PYTHONPATH
python3 -c "import sys; print(sys.path)"
```

---

## Success Criteria

✅ All tests in Test 1-13 pass
✅ No console errors
✅ Theme toggle works smoothly
✅ Files upload and rename correctly
✅ UI is responsive on mobile
✅ API code is unchanged
✅ Dark mode uses soft blacks (#0f172a)
✅ Light mode is clear and readable

If all criteria met, web UI is ready for use! 🎉
