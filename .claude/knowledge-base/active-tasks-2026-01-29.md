# Active Tasks - Crate Web UI Improvements
**Created**: 2026-01-29
**Status**: In Progress
**Session**: Post-Rebrand UX Enhancements

## Overview
User testing revealed several critical UX issues and missing features in the web UI. These tasks address preview auto-loading, file selection, template builder enhancements, and preset expansion.

---

## Task #42: Auto-Populate Preview Column on File Load ⚠️ CRITICAL UX

**Priority**: HIGH (Bad UX - requires unnecessary user action)

**Problem**:
- Preview column shows "Click 🔄 to load" placeholder
- Requires manual button click to see preview filenames
- Confusing two-step process (load files → click 🔄 → see previews)

**Current Behavior**:
```
1. User loads directory → Files appear in table
2. Preview column shows "Click 🔄 to load"
3. User must manually click 🔄 button
4. Previews load and populate column
```

**Desired Behavior**:
```
1. User loads directory → Files appear in table
2. Preview column shows loading indicator
3. Previews auto-populate as they complete
4. No manual action required
```

**Screenshots**: Screenshot 1 shows "Click 🔄 to load" in Preview column

**Implementation Plan**:

1. **Remove Manual 🔄 Button** (`web/static/index.html`):
   ```html
   <!-- REMOVE THIS -->
   <button id="load-previews-btn" class="btn btn-icon-small">🔄</button>
   ```

2. **Auto-Load After Metadata Completes** (`web/static/js/app.js`):
   ```javascript
   async renderFileList() {
       // ... render files ...

       // Load metadata for all files
       await this.loadAllMetadata();

       // AUTO-LOAD PREVIEWS (NEW)
       await this.loadAllPreviews();
   }
   ```

3. **Show Inline Loading State** (`web/static/js/app.js`):
   ```javascript
   // While loading, show: "(loading...)" in preview cell
   previewCell.innerHTML = '<span class="preview-loading">(loading...)</span>';
   ```

4. **Update Cells Progressively**:
   - Already implemented in `updatePreviewCell()` method
   - Reuse existing progress tracking from Task #40-41

**Files to Modify**:
- ✏️ `web/static/index.html` - Remove 🔄 button from table header
- ✏️ `web/static/js/app.js` - Call `loadAllPreviews()` automatically after metadata loads
- ✏️ `web/static/css/styles.css` - Add `.preview-loading` style (optional)

**Testing Checklist**:
- [ ] Load directory with MP3 files
- [ ] Preview column shows "(loading...)" immediately
- [ ] Previews populate automatically (no button click)
- [ ] Progress bar shows during loading
- [ ] Green badges appear for new filenames
- [ ] "(same)" appears for unchanged files

**Success Criteria**:
- ✅ Preview column populates automatically without any button clicks
- ✅ User sees new filenames immediately after metadata loads
- ✅ Loading states are clear and non-blocking
- ✅ No 🔄 button visible in UI

---

## Task #43: Fix File Selection Checkboxes in Directory Browser ⚠️ CRITICAL BUG

**Priority**: HIGH (Feature appears broken - checkboxes don't work)

**Problem**:
- File checkboxes appear in Browse Directories modal
- Clicking checkboxes has no effect (doesn't check/uncheck)
- No visual feedback when clicking
- Cannot select individual files

**Current Behavior**:
- Directory browser shows files with checkboxes
- Checkboxes are non-functional (visual only)
- Clicking does nothing

**Desired Behavior**:
- Clicking checkbox toggles checked state
- Visual feedback (checkbox fills, row highlights)
- Track selected files in state
- Can select multiple files

**Screenshots**: Screenshot 2 shows directory browser with non-functional checkboxes

**Root Cause** (Investigation Needed):
- Event listeners likely not attached to file checkboxes
- OR checkbox click events are being prevented/stopped
- Need to check `web/static/js/ui.js` - `renderFile()` or similar method

**Implementation Plan**:

1. **Investigate Current Code** (`web/static/js/ui.js`):
   ```javascript
   // Find file rendering code
   // Check if checkbox has onclick handler
   // Check if event propagation is stopped
   ```

2. **Add Checkbox Event Listeners**:
   ```javascript
   renderFile(file) {
       const checkbox = fileRow.querySelector('input[type="checkbox"]');

       // Add click handler
       checkbox.addEventListener('click', (e) => {
           e.stopPropagation(); // Don't trigger row click
           this.toggleFileSelection(file.path);
       });

       // Add row click handler (toggle checkbox)
       fileRow.addEventListener('click', () => {
           checkbox.checked = !checkbox.checked;
           this.toggleFileSelection(file.path);
       });
   }
   ```

3. **Track Selected Files**:
   ```javascript
   constructor() {
       this.selectedFiles = new Set(); // Track by file path
   }

   toggleFileSelection(filePath) {
       if (this.selectedFiles.has(filePath)) {
           this.selectedFiles.delete(filePath);
       } else {
           this.selectedFiles.add(filePath);
       }
       this.updateSelectButtonText();
   }
   ```

4. **Add Visual Feedback** (`web/static/css/styles.css`):
   ```css
   .file-row input[type="checkbox"]:checked {
       background: var(--primary);
       border-color: var(--primary);
   }

   .file-row:has(input[type="checkbox"]:checked) {
       background: rgba(99, 102, 241, 0.1);
       border-left: 3px solid var(--primary);
   }
   ```

**Files to Modify**:
- ✏️ `web/static/js/ui.js` - Add checkbox event listeners, track selection
- ✏️ `web/static/css/styles.css` - Visual feedback for checked state

**Testing Checklist**:
- [ ] Open Browse Directories modal
- [ ] Navigate to folder with files
- [ ] Click file checkbox → should toggle checked state
- [ ] Click file row → should also toggle checkbox
- [ ] Select multiple files → all stay checked
- [ ] Visual feedback shows selected state

**Success Criteria**:
- ✅ Clicking file checkbox toggles selection
- ✅ Visual feedback shows selected state (highlight row, colored border)
- ✅ Can select multiple files
- ✅ Selected files tracked in state (for Task #44)

---

## Task #44: Dynamic Button Text: "Select Folder" vs "Select Files"

**Priority**: MEDIUM (Confusing UX but not blocking)

**Problem**:
- Browse Directories modal always shows "Select Folder" button
- Misleading when user has selected specific files (not entire folder)

**Current Behavior**:
- Button always says "Select Folder"
- Confusing when individual files are checked

**Desired Behavior**:
- No files selected → "Select Folder" (load all files from folder)
- Files selected → "Select Files (3)" (load only checked files)
- Button text updates dynamically based on selection

**Screenshots**: Screenshot 2 shows "Select Folder" button at bottom

**Implementation Plan**:

1. **Watch Selection State Changes** (`web/static/js/ui.js`):
   ```javascript
   toggleFileSelection(filePath) {
       // ... toggle logic ...
       this.updateSelectButtonText(); // NEW
   }
   ```

2. **Update Button Text Dynamically**:
   ```javascript
   updateSelectButtonText() {
       const button = document.getElementById('browser-select-btn');
       const count = this.selectedFiles.size;

       if (count > 0) {
           button.textContent = `Select Files (${count})`;
           button.classList.add('has-selection');
       } else {
           button.textContent = 'Select Folder';
           button.classList.remove('has-selection');
       }
   }
   ```

3. **Update Click Handler Behavior**:
   ```javascript
   onSelectButtonClick() {
       if (this.selectedFiles.size > 0) {
           // Load only selected files
           const filePaths = Array.from(this.selectedFiles);
           this.closeModal();
           this.loadSpecificFiles(filePaths);
       } else {
           // Load all files from current folder
           this.closeModal();
           this.loadFolder(this.currentPath);
       }
   }
   ```

4. **Visual Differentiation** (`web/static/css/styles.css`):
   ```css
   .browser-select-btn.has-selection {
       background: var(--success);
       border-color: var(--success);
   }
   ```

**Files to Modify**:
- ✏️ `web/static/js/ui.js` - Button text update logic, dual-mode click handler
- ✏️ `web/static/index.html` - Add ID to select button if needed
- ✏️ `web/static/css/styles.css` - Visual differentiation for has-selection state

**Dependencies**:
- ⚠️ Requires Task #43 (file selection) to be completed first

**Testing Checklist**:
- [ ] Open browser, select no files → Button says "Select Folder"
- [ ] Check 3 files → Button says "Select Files (3)"
- [ ] Uncheck all → Button reverts to "Select Folder"
- [ ] Click "Select Files (3)" → Only those 3 files load
- [ ] Click "Select Folder" → All files in folder load

**Success Criteria**:
- ✅ Button text changes based on selection
- ✅ Shows count when files selected
- ✅ Clicking loads correct files (all vs selected)
- ✅ Visual differentiation between modes

---

## Task #45: Add Track Number Variable and Option

**Priority**: MEDIUM (Common use case for albums)

**Problem**:
- Albums have track numbers to maintain order
- {track} variable exists in backend but not exposed in web UI
- No presets use track numbers
- No option to zero-pad track numbers (01 vs 1)

**Current State**:
- ✅ {track} variable implemented in `crate/core/template.py`
- ❌ {track} button missing from web UI template builder
- ❌ No album-focused presets
- ❌ No zero-padding option

**Desired Features**:
1. {track} variable button in template builder (draggable)
2. Album presets using track numbers
3. Zero-padding option in Settings (01, 02, 03 vs 1, 2, 3)
4. Sort files by track number before rename (maintain album order)

**Implementation Plan**:

### 1. Add {track} Variable Button (`web/static/index.html`)

**Location**: In "Track Info" section of template builder

```html
<div class="variable-group">
    <div class="variable-group-label">📀 Track Info</div>
    <button class="btn-variable" data-variable="{artist}">🎤 Artist</button>
    <button class="btn-variable" data-variable="{title}">🎵 Title</button>
    <button class="btn-variable" data-variable="{album}">💿 Album</button>
    <button class="btn-variable" data-variable="{track}">🔢 Track #</button> <!-- NEW -->
</div>
```

### 2. Add Album Presets (`web/static/js/app.js`)

```javascript
const TEMPLATE_PRESETS = {
    // Existing presets...

    // NEW: Album presets
    'Album (with track)': '{track} - {artist} - {title}{kb}',
    'Album (full metadata)': '{track} - {artist} - {album} - {title}{mix_paren}',
    'Classical (album)': '{track} - {artist} - {title} - {album}',
    'Compilation': '{track} - {artist} - {title} ({album})',
};
```

### 3. Zero-Padding Option (`web/static/index.html` + Settings)

Add to Settings modal:
```html
<div class="setting-item">
    <label>
        <input type="checkbox" id="setting-zero-pad-tracks">
        Zero-pad track numbers (01, 02, 03 vs 1, 2, 3)
    </label>
    <p class="setting-description">
        Adds leading zeros to track numbers for better sorting (01, 02, ..., 10)
    </p>
</div>
```

Backend support (`crate/core/config.py`):
```python
@dataclass
class Config:
    # ... existing fields ...
    zero_pad_tracks: bool = True  # Default: enabled
```

Template formatting (`crate/core/template.py`):
```python
def build_default_components(meta: dict, config: Optional[Config] = None) -> dict:
    # ... existing code ...

    track = meta.get("track", "")
    if track and config and config.zero_pad_tracks:
        try:
            track = f"{int(track):02d}"  # Zero-pad to 2 digits
        except ValueError:
            pass  # Keep original if not a number

    return {
        # ... other fields ...
        "track": track,
    }
```

### 4. Sort by Track Number Before Rename (`crate/api/renamer.py`)

```python
def rename_files(self, request: RenameRequest) -> RenameResult:
    # ... existing code to get files ...

    # Sort by track number if present
    def track_sort_key(preview):
        try:
            meta = self._cache.get(preview.src)
            track = meta.get("track", "")
            return (int(track), preview.src) if track else (999, preview.src)
        except (ValueError, TypeError):
            return (999, preview.src)

    previews.sort(key=track_sort_key)

    # ... continue with rename ...
```

**Files to Modify**:
- ✏️ `web/static/index.html` - Add {track} button, zero-padding checkbox
- ✏️ `web/static/js/app.js` - Add album presets, save zero-pad setting
- ✏️ `crate/core/config.py` - Add `zero_pad_tracks` field
- ✏️ `crate/core/template.py` - Format track with zero-padding
- ✏️ `crate/api/renamer.py` - Sort files by track before rename

**Testing Checklist**:
- [ ] {track} button appears in template builder
- [ ] Drag-and-drop works for {track}
- [ ] Album presets populate template correctly
- [ ] Zero-padding checkbox in Settings
- [ ] Files with track 1-9 format as 01-09 when enabled
- [ ] Files rename in track order (01, 02, 03, ...)

**Success Criteria**:
- ✅ {track} variable available and draggable
- ✅ Album presets include track numbers
- ✅ Zero-padding option works correctly
- ✅ Files maintain album order during rename

---

## Task #46: Verify All ID3 Tag Variables Are Exposed

**Priority**: MEDIUM (Completeness - power users need all variables)

**Problem**:
- Need to ensure ALL supported ID3 tag variables have UI buttons
- Some variables may be in backend but missing from web UI
- Need comprehensive variable coverage for power users

**ID3 Variables Inventory**:

### Currently Exposed (Verify in UI):
- ✅ {artist} - Artist name
- ✅ {title} - Track title
- ✅ {album} - Album name
- ✅ {mix} - Mix version
- ✅ {mix_paren} - Mix with parentheses (composite)
- ✅ {year} - Release year
- ✅ {bpm} - Beats per minute
- ✅ {key} - Musical key
- ✅ {camelot} - Camelot notation
- ✅ {kb} - Key + BPM combo (composite)
- ✅ {genre} - Music genre
- ✅ {label} - Record label
- ✅ {catalog} - Catalog number

### Need to Verify/Add:
- ❓ {track} - Track number (see Task #45)
- ❓ {album_artist} - Album artist (different from track artist)
- ❓ {composer} - Composer name
- ❓ {disc} - Disc number (for multi-disc albums)
- ❓ {comment} - Comments field
- ❓ {date} - Full date (ISO format vs just year)
- ❓ {publisher} - Publisher/label
- ❓ {isrc} - International Standard Recording Code
- ❓ {copyright} - Copyright info
- ❓ {grouping} - Grouping/collection

**Implementation Plan**:

### 1. Audit Backend Variables (`crate/core/template.py`)

Check `build_default_components()` method:
```python
def build_default_components(meta: dict, config: Optional[Config] = None) -> dict:
    # Document ALL returned variables here
    return {
        # Which variables are supported?
        # Which are missing?
    }
```

### 2. Audit Web UI Buttons (`web/static/index.html`)

Count buttons in template builder:
```bash
grep -o 'data-variable="{[^}]*}"' web/static/index.html | sort | uniq
```

### 3. Add Missing Variables to Backend (if needed)

Example for {album_artist}:
```python
album_artist = meta.get("albumartist") or meta.get("album_artist") or artist
```

### 4. Add Missing Buttons to Web UI

Organize by category:
```html
<!-- Track Info -->
<div class="variable-group">
    <div class="variable-group-label">📀 Track Info</div>
    <button class="btn-variable" data-variable="{artist}">🎤 Artist</button>
    <button class="btn-variable" data-variable="{album_artist}">👥 Album Artist</button>
    <button class="btn-variable" data-variable="{title}">🎵 Title</button>
    <button class="btn-variable" data-variable="{album}">💿 Album</button>
</div>

<!-- Album Info -->
<div class="variable-group">
    <div class="variable-group-label">💿 Album Info</div>
    <button class="btn-variable" data-variable="{track}">🔢 Track</button>
    <button class="btn-variable" data-variable="{disc}">💽 Disc</button>
    <button class="btn-variable" data-variable="{year}">📅 Year</button>
    <button class="btn-variable" data-variable="{date}">📆 Date</button>
</div>

<!-- Label Info -->
<div class="variable-group">
    <div class="variable-group-label">🏷️ Label Info</div>
    <button class="btn-variable" data-variable="{label}">🏷️ Label</button>
    <button class="btn-variable" data-variable="{catalog}">📋 Catalog</button>
    <button class="btn-variable" data-variable="{publisher}">📰 Publisher</button>
    <button class="btn-variable" data-variable="{isrc}">🔢 ISRC</button>
</div>

<!-- Other -->
<div class="variable-group">
    <div class="variable-group-label">📝 Other</div>
    <button class="btn-variable" data-variable="{genre}">🎸 Genre</button>
    <button class="btn-variable" data-variable="{composer}">🎼 Composer</button>
    <button class="btn-variable" data-variable="{comment}">💬 Comment</button>
    <button class="btn-variable" data-variable="{grouping}">📂 Grouping</button>
    <button class="btn-variable" data-variable="{copyright}">©️ Copyright</button>
</div>
```

### 5. Update Variable Reference Table

In Settings modal, document all variables:
```html
<table class="variable-reference">
    <thead>
        <tr>
            <th>Variable</th>
            <th>Description</th>
            <th>Example</th>
        </tr>
    </thead>
    <tbody>
        <!-- Document every variable with examples -->
    </tbody>
</table>
```

**Files to Modify**:
- ✏️ `crate/core/template.py` - Add missing variable support
- ✏️ `web/static/index.html` - Add missing buttons, update reference table
- ✏️ `tests/test_template.py` - Test all variables

**Testing Checklist**:
- [ ] All backend variables have UI buttons
- [ ] All buttons are draggable
- [ ] Variable reference table lists all variables
- [ ] Test template with each variable works
- [ ] No duplicate variable names

**Success Criteria**:
- ✅ All supported ID3 variables have UI buttons
- ✅ Variables organized logically by category
- ✅ Variable reference table is comprehensive
- ✅ All variables tested

---

## Task #47: Expand Template Presets with Best Practices

**Priority**: MEDIUM (User experience - reduce learning curve)

**Problem**:
- Current presets are limited (Electronic, Hip-Hop, Techno)
- Users need more diverse presets covering different use cases
- DJ/producer best practices should be codified as presets

**Current Presets** (Verify):
```javascript
const TEMPLATE_PRESETS = {
    'Electronic': '{artist} - {title}{kb}',
    'Hip-Hop': '{artist} - {title} {bpm}',
    'Techno': '{artist} - {title} [{camelot} {bpm}]',
    // Need more!
};
```

**Best Practice Presets to Add** (based on ./claude/dj-naming-conventions-research-2025-2026.md):

### DJ Performance Presets:

1. **Rekordbox Standard** 🎧
   ```
   {artist} - {title} [{camelot} {bpm}]
   ```
   - Example: `Deadmau5 - Strobe [8A 128].mp3`
   - Most popular for harmonic mixing DJs

2. **Serato Standard** 🎚️
   ```
   {artist} - {title}{mix_paren} {bpm}
   ```
   - Example: `Deadmau5 - Strobe (Original Mix) 128.mp3`
   - Serato users prefer BPM at end (no brackets)

3. **Minimal (Key+BPM)** ✨
   ```
   {artist} - {title}{kb}
   ```
   - Example: `Deadmau5 - Strobe [8A 128].mp3`
   - Clean, uses composite variable

4. **Traktor Standard** 🎛️
   ```
   {artist} - {title} ({key} {bpm}BPM)
   ```
   - Example: `Deadmau5 - Strobe (Am 128BPM).mp3`
   - Uses musical key notation instead of Camelot

### Album/Collection Presets:

5. **Album (with track)** 💿
   ```
   {track} - {artist} - {title}
   ```
   - Example: `01 - Deadmau5 - Strobe.mp3`
   - Preserves album order

6. **Album (full metadata)** 📀
   ```
   {track} - {artist} - {album} - {title}{kb}
   ```
   - Example: `01 - Deadmau5 - For Lack of a Better Name - Strobe [8A 128].mp3`
   - Maximum info for archival

7. **Compilation** 🎶
   ```
   {track} - {artist} - {title} ({album})
   ```
   - Example: `01 - Deadmau5 - Strobe (Ministry of Sound Annual).mp3`
   - Good for mixed compilations

8. **Multi-Disc Album** 💽
   ```
   {disc}-{track} - {artist} - {title}
   ```
   - Example: `1-01 - Deadmau5 - Strobe.mp3`
   - For box sets and multi-disc albums

### Producer/Studio Presets:

9. **Producer (with label)** 🏷️
   ```
   {artist} - {title}{mix_paren} [{label}]
   ```
   - Example: `Deadmau5 - Strobe (Original Mix) [Mau5trap].mp3`
   - Label info for catalog management

10. **Studio (with date)** 📅
    ```
    {date} {artist} - {title} {bpm}
    ```
    - Example: `2009-11-05 Deadmau5 - Strobe 128.mp3`
    - Date-sorted for projects

11. **Catalog Number** 📋
    ```
    [{catalog}] {artist} - {title}
    ```
    - Example: `[MAU5CD001] Deadmau5 - Strobe.mp3`
    - Professional catalog organization

### Radio/Podcast Presets:

12. **Radio (artist first)** 📻
    ```
    {artist} - {title} ({year})
    ```
    - Example: `Deadmau5 - Strobe (2009).mp3`
    - Clean for radio playlists

13. **Podcast/Mix** 🎙️
    ```
    {track} {artist} - {title}{kb}
    ```
    - Example: `01 Deadmau5 - Strobe [8A 128].mp3`
    - Numbered for mix tracklists (no hyphen after track)

14. **Interview/Talk** 🎤
    ```
    {date} - {artist} - {title}
    ```
    - Example: `2009-11-05 - Deadmau5 - Interview.mp3`
    - For spoken word content

### Special Use Cases:

15. **Classical Music** 🎻
    ```
    {composer} - {title} - {artist} ({year})
    ```
    - Example: `Beethoven - Symphony No. 5 - Berlin Philharmonic (1963).mp3`
    - Composer first for classical

16. **Remix/Bootleg** 🔄
    ```
    {artist} - {title} ({mix}) [{label} {catalog}]
    ```
    - Example: `Deadmau5 - Strobe (Dimension Remix) [Mau5trap MAU5123].mp3`
    - Full remix credits

**Implementation**:

### 1. Update Presets Object (`web/static/js/app.js`)

```javascript
const TEMPLATE_PRESETS = {
    // DJ Performance
    'Rekordbox Standard': '{artist} - {title} [{camelot} {bpm}]',
    'Serato Standard': '{artist} - {title}{mix_paren} {bpm}',
    'Minimal (Key+BPM)': '{artist} - {title}{kb}',
    'Traktor Standard': '{artist} - {title} ({key} {bpm}BPM)',

    // Albums
    'Album (with track)': '{track} - {artist} - {title}',
    'Album (full metadata)': '{track} - {artist} - {album} - {title}{kb}',
    'Compilation': '{track} - {artist} - {title} ({album})',
    'Multi-Disc Album': '{disc}-{track} - {artist} - {title}',

    // Producer
    'Producer (with label)': '{artist} - {title}{mix_paren} [{label}]',
    'Studio (with date)': '{date} {artist} - {title} {bpm}',
    'Catalog Number': '[{catalog}] {artist} - {title}',

    // Radio/Podcast
    'Radio (artist first)': '{artist} - {title} ({year})',
    'Podcast/Mix': '{track} {artist} - {title}{kb}',
    'Interview/Talk': '{date} - {artist} - {title}',

    // Special
    'Classical Music': '{composer} - {title} - {artist} ({year})',
    'Remix/Bootleg': '{artist} - {title} ({mix}) [{label} {catalog}]',
};
```

### 2. Group Presets with optgroups (`web/static/index.html`)

```html
<select id="template-preset">
    <option value="">-- Select Preset --</option>

    <optgroup label="🎧 DJ Performance">
        <option value="Rekordbox Standard">Rekordbox Standard</option>
        <option value="Serato Standard">Serato Standard</option>
        <option value="Minimal (Key+BPM)">Minimal (Key+BPM)</option>
        <option value="Traktor Standard">Traktor Standard</option>
    </optgroup>

    <optgroup label="💿 Albums">
        <option value="Album (with track)">Album (with track)</option>
        <option value="Album (full metadata)">Album (full metadata)</option>
        <option value="Compilation">Compilation</option>
        <option value="Multi-Disc Album">Multi-Disc Album</option>
    </optgroup>

    <optgroup label="🏷️ Producer/Studio">
        <option value="Producer (with label)">Producer (with label)</option>
        <option value="Studio (with date)">Studio (with date)</option>
        <option value="Catalog Number">Catalog Number</option>
    </optgroup>

    <optgroup label="📻 Radio/Podcast">
        <option value="Radio (artist first)">Radio (artist first)</option>
        <option value="Podcast/Mix">Podcast/Mix</option>
        <option value="Interview/Talk">Interview/Talk</option>
    </optgroup>

    <optgroup label="🎻 Special">
        <option value="Classical Music">Classical Music</option>
        <option value="Remix/Bootleg">Remix/Bootleg</option>
    </optgroup>
</select>
```

### 3. Add Tooltips/Descriptions (Optional)

```javascript
const PRESET_DESCRIPTIONS = {
    'Rekordbox Standard': 'Most popular for harmonic mixing DJs',
    'Serato Standard': 'Serato users prefer BPM at end',
    'Album (with track)': 'Preserves album order with track numbers',
    // ... etc
};

// Show tooltip on hover
presetSelect.addEventListener('change', (e) => {
    const description = PRESET_DESCRIPTIONS[e.target.value];
    if (description) {
        showTooltip(description);
    }
});
```

**Files to Modify**:
- ✏️ `web/static/js/app.js` - Expand TEMPLATE_PRESETS object
- ✏️ `web/static/index.html` - Add optgroups to preset dropdown
- ✏️ `web/static/css/styles.css` - Style optgroups (optional)

**Testing Checklist**:
- [ ] All 16+ presets appear in dropdown
- [ ] Presets grouped by category (DJ/Album/Producer/Radio/Special)
- [ ] Clicking preset auto-fills template input
- [ ] Each preset produces expected output format
- [ ] Presets use correct variables (no undefined variables)

**Success Criteria**:
- ✅ 16+ presets covering all major use cases
- ✅ Presets organized by category with optgroups
- ✅ Clicking preset auto-fills template correctly
- ✅ Presets follow DJ/producer best practices

---

## Implementation Order (Recommended)

1. **Task #43** (Fix file selection checkboxes) - CRITICAL BUG
   - Foundation for Task #44
   - Blocking user workflow

2. **Task #44** (Dynamic button text) - Depends on #43
   - Improves UX for file selection flow

3. **Task #42** (Auto-populate previews) - CRITICAL UX
   - High user impact
   - Reduces friction

4. **Task #46** (Verify all variables) - Foundation for #45 and #47
   - Audit existing variables
   - Add missing variables to backend

5. **Task #45** (Add track number) - Depends on #46
   - Common use case for albums
   - Needed for album presets in #47

6. **Task #47** (Expand presets) - Depends on #45 and #46
   - Final UX polish
   - Uses all variables from previous tasks

---

## Testing Strategy

### Manual Testing Checklist:
- [ ] Load directory with 10+ MP3 files
- [ ] Verify previews auto-populate (Task #42)
- [ ] Open Browse Directories modal
- [ ] Select individual files using checkboxes (Task #43)
- [ ] Verify button changes to "Select Files (N)" (Task #44)
- [ ] Test {track} variable in template (Task #45)
- [ ] Test zero-padding option for track numbers (Task #45)
- [ ] Test all 16+ presets (Task #47)
- [ ] Verify drag-and-drop works for all variables (Task #46)

### Automated Testing:
- [ ] Update `tests/test_template.py` with new variables
- [ ] Add tests for zero-padding logic
- [ ] Add tests for file sorting by track number
- [ ] Verify all presets produce valid output

---

## Success Metrics

**User Experience**:
- Preview column auto-populates (no manual button click)
- File selection works correctly in browser
- 16+ presets cover all major use cases
- All ID3 variables available for drag-and-drop

**Technical Quality**:
- All tests passing
- No console errors
- Consistent UX patterns across features
- Documented in `./claude/lessons-learned.md`

---

## Notes for Future Sessions

**If conversation gets compressed**, refer to this file for:
- Complete task descriptions with implementation plans
- User screenshots showing issues
- Priority order and dependencies
- Success criteria for each task

**Related Documentation**:
- `./claude/lessons-learned.md` - Design patterns and lessons
- `./claude/dj-naming-conventions-research-2025-2026.md` - Preset research
- `./claude/metadata-lookup-logic.md` - Metadata system
- `./claude/app-naming-research-2025-2026.md` - Crate rebrand

**Key Files**:
- `web/static/js/app.js` - Main application logic
- `web/static/js/ui.js` - Directory browser and UI utilities
- `web/static/index.html` - Template builder and Settings
- `crate/core/template.py` - Template variable backend
- `crate/api/renamer.py` - Rename logic and file sorting

---

**Last Updated**: 2026-01-29
**Created By**: Claude Sonnet 4.5
**Status**: Ready for implementation
