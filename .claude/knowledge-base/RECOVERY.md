# Quick Recovery Guide - Crate Development

**Last Updated**: 2026-01-30T00:52:22Z
**Session**: post-rebrand-ux-fixes-2026-01-29

---

## 🎯 Current Priority

**Start with Task #43** - Fix file selection checkboxes in directory browser (CRITICAL BUG - blocking user workflow)

---

## 📋 Active Tasks Quick Reference

### Critical (Fix First):
- **#42**: Auto-populate preview column on file load - Status: `pending` ⚠️ CRITICAL UX
  - User still sees "Click 🔄 to load" - must auto-populate without button click
  - **NEXT UP**

- **#43**: Fix file selection checkboxes in directory browser - Status: `✅ COMPLETED`
  - Checkboxes now work, button text updates, visual feedback added

### High Priority:
- **#44**: Dynamic button text: "Select Folder" vs "Select Files" - Status: `✅ COMPLETED`
  - Button text changes to "Select Files (N)" when files selected

### Medium Priority:
- **#45**: Add track number variable and option - Status: `pending`
  - Add {track} button, zero-padding option, album presets

- **#46**: Verify all ID3 tag variables are exposed - Status: `pending`
  - Audit backend vs UI, ensure all variables have buttons

- **#47**: Expand template presets with best practices - Status: `pending`
  - Add 16+ presets grouped by category (DJ/Album/Producer/Radio/Special)

---

## 📂 Key Files & Locations

### For Task #43 (File Selection Fix):
- `web/static/js/ui.js:430-485` - File rendering code (add checkbox listeners here)
- `web/static/js/ui.js:1-50` - UI class constructor (add selectedFiles Set)
- `web/static/css/styles.css` - Add visual feedback styles

### For Task #42 (Auto-Populate Previews):
- `web/static/js/app.js:205-280` - renderFileList() method (add auto-load call)
- `web/static/js/app.js:728-790` - loadAllPreviews() method (already exists)
- `web/static/index.html` - Remove 🔄 button from table header

### For Task #44 (Dynamic Button):
- `web/static/js/ui.js` - updateSelectButtonText() method (create new)
- `web/static/index.html` - Verify "browser-select-btn" ID exists

### For Task #45 (Track Numbers):
- `web/static/index.html:369-428` - Add {track} button to template builder
- `crate/core/template.py:71-95` - Implement zero-padding logic
- `crate/core/config.py:15-45` - Add zero_pad_tracks field

### For Task #46 (Variable Audit):
- `crate/core/template.py:71-95` - List all backend variables
- `web/static/index.html:369-428` - Count UI buttons
- Create gap analysis

### For Task #47 (Expand Presets):
- `web/static/js/app.js:1029-1064` - Expand TEMPLATE_PRESETS object
- `web/static/index.html:400-410` - Add optgroups to dropdown

---

## 🚀 Commands to Resume

```bash
# Check if server is running
ps aux | grep uvicorn

# Start server (if not running)
cd /Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename
./start_crate_web.sh

# Open in browser
open https://127.0.0.1:8000

# Run tests
pytest tests/test_template.py -v

# Check syntax
python -m py_compile web/static/js/ui.js
python -m py_compile web/static/js/app.js

# Git status
git status

# View logs
tail -f /tmp/dj_renamer_web.log
```

---

## 📖 Context Links

### Task Documentation:
- **Full Task Details**: `./claude/active-tasks-2026-01-29.md` (7,500+ words, complete specs)
- **Session State**: `./claude/session-state-2026-01-29-20-52.md` (this snapshot)
- **Lessons Learned**: `./claude/lessons-learned.md` (patterns, best practices)

### Research & Background:
- **DJ Best Practices**: `./claude/dj-naming-conventions-research-2025-2026.md`
- **Metadata Logic**: `./claude/metadata-lookup-logic.md`
- **Rebrand Strategy**: `./claude/app-naming-research-2025-2026.md`
- **Market Research**: `./claude/market-research-2025-2026.md`

### User Feedback:
- Screenshot 1 (16.38.57.png): Shows preview column with "Click 🔄 to load"
- Screenshot 2 (16.41.36.png): Shows broken file selection checkboxes

---

## 🎬 Quick Start Actions

### For Next Session (Recommended Order):

1. **First: Fix Critical Bug (Task #43)**
   ```bash
   # Open file selection code
   code web/static/js/ui.js

   # Find file rendering method (search for "renderFile" or "appendChild")
   # Add checkbox event listeners
   # Add selectedFiles Set to constructor
   ```

2. **Second: Fix Critical UX (Task #42)**
   ```bash
   # Open main app logic
   code web/static/js/app.js

   # Find renderFileList() method (line ~205)
   # Add: await this.loadAllPreviews();
   # Remove 🔄 button from HTML
   ```

3. **Third: Implement Dependent Feature (Task #44)**
   ```bash
   # After Task #43 works, add dynamic button text
   # Use this.selectedFiles.size to determine button text
   ```

4. **Fourth: Foundation Work (Task #46)**
   ```bash
   # Audit all variables
   # Read crate/core/template.py
   # Count buttons in web/static/index.html
   ```

5. **Fifth: Track Numbers (Task #45)**
   ```bash
   # Add {track} button
   # Implement zero-padding
   # Add album presets
   ```

6. **Sixth: Final Polish (Task #47)**
   ```bash
   # Expand TEMPLATE_PRESETS object
   # Add 16+ presets with optgroups
   ```

---

## ⚙️ Configuration & State

### Current Git Branch:
```bash
git branch --show-current
# main
```

### Server Configuration:
- **Port**: 8000 (HTTPS)
- **URL**: https://127.0.0.1:8000
- **PID File**: .crate_web.pid
- **Log File**: /tmp/dj_renamer_web.log

### Virtual Environment:
```bash
source .venv/bin/activate
```

### Key Dependencies:
- FastAPI, Uvicorn (web server)
- mutagen (MP3 metadata)
- Textual (TUI - not used in web)
- pytest (testing)

---

## 🔍 Testing Checklist (Before Marking Complete)

### Task #42:
- [ ] Preview column populates automatically (no 🔄 button)
- [ ] Progress bar shows during loading
- [ ] Green badges for new filenames
- [ ] "(same)" for unchanged files

### Task #43:
- [ ] Click checkbox → toggles selection
- [ ] Click row → also toggles checkbox
- [ ] Visual feedback (background, border)
- [ ] Multiple selections work

### Task #44:
- [ ] Button says "Select Folder" when no files selected
- [ ] Button says "Select Files (3)" when 3 files selected
- [ ] Clicking loads correct files (all vs selected)

### Task #45:
- [ ] {track} button appears and is draggable
- [ ] Zero-padding works (1 → 01)
- [ ] Album presets populate template
- [ ] Files rename in track order

### Task #46:
- [ ] All backend variables have UI buttons
- [ ] Variable reference table is complete
- [ ] No duplicate variable names

### Task #47:
- [ ] 16+ presets in dropdown
- [ ] Presets grouped by category
- [ ] Each preset produces valid output

---

## 🚨 Known Issues

### Issue 1: Preview Auto-Load (Task #42)
- **Status**: Not yet implemented
- **User Impact**: HIGH - every user hits this friction
- **Quote**: "do NOT require a user to press 🔄. That's a bad UX."

### Issue 2: File Selection Checkboxes (Task #43)
- **Status**: Broken - checkboxes non-functional
- **User Impact**: HIGH - blocking file-specific operations
- **Quote**: "I can't select files even though it looks like they have a check box"

### Issue 3: Confusing Button Text (Task #44)
- **Status**: Always says "Select Folder"
- **User Impact**: MEDIUM - misleading when files selected
- **Quote**: "there should be a new button for 'Select Files' and not 'Select Folder'"

---

## 💡 Quick Decisions Reference

- **Remove 🔄 button entirely** (don't hide, delete it)
- **Use Set() for selectedFiles** (not Array)
- **Show file count in button**: "Select Files (3)"
- **Zero-padding ON by default** (01, 02, 03)
- **16+ presets grouped by category** (DJ/Album/Producer/Radio/Special)

---

## 📊 Session Stats

- **Tasks Created**: 6 (#42-47)
- **Tasks Completed**: 0 (planning phase)
- **Documentation Created**: 3 files (~15,000 words)
- **Files to Modify**: 8 files identified
- **User Quotes Captured**: 7 direct quotes
- **Screenshots Analyzed**: 2 screenshots

---

## 🎯 Definition of Done (All Tasks)

### Task #42:
✅ Preview column populates automatically without button click
✅ Progress bar shows during loading
✅ No 🔄 button in UI

### Task #43:
✅ Checkboxes toggle when clicked
✅ Visual feedback for selected state
✅ Can select multiple files

### Task #44:
✅ Button text changes: "Select Folder" vs "Select Files (N)"
✅ Clicking loads correct files (all or selected)

### Task #45:
✅ {track} variable available and draggable
✅ Zero-padding option in Settings
✅ Album presets include track numbers

### Task #46:
✅ All backend variables have UI buttons
✅ Variables organized by category
✅ Reference table complete

### Task #47:
✅ 16+ presets covering major use cases
✅ Presets grouped with optgroups
✅ All presets produce valid output

---

**Recovery Status**: ✅ COMPLETE - Full context preserved
**Next Action**: Start implementing Task #43 (file selection fix)
**Estimated Work**: 4-6 hours for all 6 tasks
