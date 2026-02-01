# Implementation Plan: Remember Last Directory in File Browser

**Feature**: Task #84
**Estimated Time**: 70 minutes (single session)
**Priority**: LOW (after critical bugs)
**Status**: Ready for Implementation

---

## Architecture Overview

**Current Flow:**
1. User clicks "Browse" button → opens DirectoryBrowser modal
2. User navigates and selects directory → calls `onDirectorySelected(path)`
3. App loads directory contents with `loadDirectory()`
4. DirectoryBrowser starts at home (~) or current path from input field

**Target Flow (with memory):**
1. **On startup**: Load last directory from config, validate it, auto-load if valid
2. **On browse**: When user selects directory, save it to config immediately
3. **Fallback logic**: If saved path doesn't exist, walk up parent chain until valid

---

## Phase 1: Backend Configuration (config.py)

**File**: `/Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/crate/core/config.py`

### Step 1.1: Add Config Keys to DEFAULT_CONFIG (Line 19-31)

Add two new configuration keys:
```python
DEFAULT_CONFIG = {
    # ... existing config ...
    "last_directory": "",  # Last browsed directory path (empty = not set)
    "remember_last_directory": True,  # Enable/disable feature (default: enabled)
}
```

**Line numbers**: After line 30 (after `"enable_smart_detection": False,`)

### Step 1.2: Create Helper Function for Path Validation (After line 283)

Add new function `get_valid_directory_with_fallback()`:
```python
def get_valid_directory_with_fallback(saved_path: str) -> str:
    """
    Get valid directory with intelligent fallback strategy.

    Strategy:
    1. Try saved path directly
    2. Walk up parent directories until valid dir found
    3. Ultimate fallback: home directory (~)

    Args:
        saved_path: Last saved directory path (can be empty)

    Returns:
        Valid directory path that exists

    Examples:
        >>> get_valid_directory_with_fallback("/Users/dj/Music/Deleted")
        "/Users/dj/Music"  # If Deleted doesn't exist but Music does

        >>> get_valid_directory_with_fallback("")
        "/Users/dj"  # Falls back to home
    """
    import os
    from pathlib import Path

    # If no saved path, return home
    if not saved_path:
        return str(Path.home())

    try:
        # Expand ~ and resolve path
        path = Path(saved_path).expanduser().resolve()

        # Try saved path directly
        if path.exists() and path.is_dir():
            return str(path)

        # Walk up parent directories
        current = path
        while current != current.parent:  # Not at root
            parent = current.parent
            if parent.exists() and parent.is_dir():
                return str(parent)
            current = parent

    except Exception:
        # Any error in path handling - fall back to home
        pass

    # Ultimate fallback: home directory
    return str(Path.home())
```

**Line numbers**: Add after `mark_first_run_complete()` function (after line 282)

---

## Phase 2: Backend API Endpoint (web/main.py)

**File**: `/Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/web/main.py`

### Step 2.1: Add Get Initial Directory Endpoint (After line 262)

Add new endpoint after `/api/directory/browse`:
```python
@app.get("/api/directory/initial")
async def get_initial_directory():
    """
    Get initial directory to load on startup with intelligent fallback.

    Returns directory to auto-load based on:
    - last_directory config value (if remember_last_directory enabled)
    - Validates path exists, walks up parents if needed
    - Falls back to home directory

    Returns:
        {
            "path": "/Users/dj/Music",
            "source": "remembered|fallback|home",
            "original_path": "/Users/dj/Music/Albums" (if fell back)
        }
    """
    try:
        from crate.core.config import load_config, get_valid_directory_with_fallback

        config = load_config()

        # Check if feature is enabled
        remember_enabled = config.get("remember_last_directory", True)
        saved_path = config.get("last_directory", "")

        if not remember_enabled or not saved_path:
            # Feature disabled or no saved path - return home
            return {
                "path": str(Path.home()),
                "source": "home",
                "original_path": None
            }

        # Get valid directory with fallback
        valid_path = get_valid_directory_with_fallback(saved_path)

        # Determine source
        if valid_path == saved_path:
            source = "remembered"
            original_path = None
        elif valid_path == str(Path.home()):
            source = "home"
            original_path = saved_path
        else:
            source = "fallback"
            original_path = saved_path

        return {
            "path": valid_path,
            "source": source,
            "original_path": original_path
        }

    except Exception as e:
        logger.error(f"Error getting initial directory: {e}", exc_info=True)
        # On any error, return home directory
        return {
            "path": str(Path.home()),
            "source": "home",
            "original_path": None
        }
```

**Line numbers**: Insert after line 262 (after `/api/directory/browse` endpoint)

---

## Phase 3: Frontend API Client (api.js)

**File**: `/Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/web/static/js/api.js`

### Step 3.1: Add getInitialDirectory Method (After line 174)

Add new method after `updateConfig()`:
```javascript
/**
 * Get initial directory to load on startup
 * @returns {Promise<Object>} { path, source, original_path }
 */
async getInitialDirectory() {
    return this._fetch('/api/directory/initial');
}
```

**Line numbers**: Insert after line 174 (after `updateConfig()` method)

---

## Phase 4: Frontend App Logic (app.js)

**File**: `/Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/web/static/js/app.js`

### Step 4.1: Auto-Load Last Directory on Startup (In init() method, ~line 47-90)

Modify the `init()` method to auto-load last directory:

**Location**: Around line 84 (after event listener setup, before end of init())

Add:
```javascript
// Auto-load last directory if enabled
try {
    const initialDir = await this.api.getInitialDirectory();

    if (initialDir.path) {
        // Set path in input
        document.getElementById('directory-path').value = initialDir.path;

        // Show notification based on source
        if (initialDir.source === 'remembered') {
            console.log(`Restored last directory: ${initialDir.path}`);
            // Silently load (no toast needed for expected behavior)
        } else if (initialDir.source === 'fallback') {
            console.log(`Last directory not found (${initialDir.original_path}), using parent: ${initialDir.path}`);
            this.ui.warning(`Previous directory no longer exists. Loaded parent folder.`);
        }

        // Auto-load the directory
        await this.loadDirectory();
    }
} catch (error) {
    console.error('Error loading initial directory:', error);
    // Don't show error to user - it's not critical
}
```

**Line numbers**: Insert around line 84 (before the closing brace of `init()` method, after `this.openDirectoryBrowser()` line)

### Step 4.2: Save Directory on Selection (In onDirectorySelected(), ~line 688)

Modify `onDirectorySelected()` to save the directory:

**Location**: Line 688-697

After line 690 (`document.getElementById('directory-path').value = path;`), add:
```javascript
// Save last directory to config (asynchronously, don't block)
this.saveLastDirectory(path).catch(error => {
    console.error('Failed to save last directory:', error);
    // Don't show error to user - non-critical background operation
});
```

**Line numbers**: Insert after line 690

### Step 4.3: Add saveLastDirectory Helper Method (End of App class, ~line 2605)

Add new method before the closing brace of the App class:
```javascript
/**
 * Save last browsed directory to config
 * @param {string} path - Directory path to save
 */
async saveLastDirectory(path) {
    try {
        await this.api.updateConfig({
            last_directory: path
        });
        console.log(`Saved last directory: ${path}`);
    } catch (error) {
        // Log but don't show to user - non-critical
        console.error('Failed to save last directory:', error);
    }
}
```

**Line numbers**: Insert before line 2606 (before the closing brace of App class)

---

## Phase 5: Settings UI (index.html)

**File**: `/Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/web/static/index.html`

### Step 5.1: Add Toggle to Settings Modal (In settings modal form)

Add new setting in the settings modal (after existing checkboxes):
```html
<div class="setting-item">
    <label class="checkbox-label">
        <input type="checkbox" id="remember-last-directory" checked>
        <span>Remember Last Directory</span>
    </label>
    <p class="setting-description">
        Automatically return to your last browsed directory on startup.
        If the directory no longer exists, the closest parent folder will be used.
    </p>
</div>
```

**Location**: In the settings modal, after other checkbox settings (e.g., after `enable-smart-detection`)

### Step 5.2: Wire Up Setting in app.js (loadSettings() and saveSettings())

**In loadSettings()** (around line 2120):
Add after line 2120:
```javascript
document.getElementById('remember-last-directory').checked = config.remember_last_directory !== false;
```

**In saveSettings()** (around line 2363):
Add after line 2363:
```javascript
remember_last_directory: document.getElementById('remember-last-directory').checked,
```

---

## Testing Strategy

### Test Case 1: Normal Flow (Happy Path)
```
Steps:
1. Start app
2. Browse to /Users/test/Music/Albums
3. Stop server (Ctrl+C)
4. Start server again
5. Verify: App auto-loads /Users/test/Music/Albums
6. Verify: No error messages
```

### Test Case 2: Directory Deleted (Fallback to Parent)
```
Steps:
1. Browse to /Users/test/Music/Albums/Electronic
2. Stop server
3. Delete /Users/test/Music/Albums/Electronic folder
4. Start server
5. Verify: App loads /Users/test/Music/Albums (parent)
6. Verify: Warning toast shown about fallback
```

### Test Case 3: Entire Path Deleted (Fallback to Home)
```
Steps:
1. Browse to /Users/test/Music/Albums/Electronic
2. Stop server
3. Delete entire /Users/test/Music directory
4. Start server
5. Verify: App loads home directory (~)
6. Verify: Warning toast shown
```

### Test Case 4: Feature Disabled
```
Steps:
1. Browse to /Users/test/Music
2. Open Settings
3. Uncheck "Remember Last Directory"
4. Save settings
5. Stop server
6. Start server
7. Verify: App loads home directory (doesn't remember)
```

### Test Case 5: First Run (No Saved Path)
```
Steps:
1. Delete config file (~/.config/crate/config.json)
2. Start server
3. Verify: App loads home directory
4. Verify: No errors
```

---

## Edge Cases to Handle

### Edge Case 1: Symlinks
- If saved path is a symlink that breaks, fallback should work
- Handled by `Path.resolve()` and `exists()` checks

### Edge Case 2: Permission Changes
- If user loses read permissions to saved directory
- API endpoint handles with try/except
- Falls back to home directory

### Edge Case 3: Network Drives (macOS/Windows)
- If saved path is on unmounted network drive
- `Path.exists()` will return False
- Fallback logic handles automatically

### Edge Case 4: Race Conditions
- Config save happens asynchronously (don't block UI)
- If save fails, next startup uses old path (acceptable)
- User can always browse manually

### Edge Case 5: Invalid JSON in Config
- Handled by existing `load_config()` error handling
- Returns DEFAULT_CONFIG if parse fails

---

## Implementation Sequence

**Order of changes (single session workflow):**

1. **Backend Config** (10 mins)
   - Update `config.py` with new keys and helper function
   - Test helper function in isolation

2. **Backend API** (10 mins)
   - Add `/api/directory/initial` endpoint in `main.py`
   - Test endpoint with curl/browser

3. **Frontend API Client** (5 mins)
   - Add `getInitialDirectory()` to `api.js`

4. **Frontend App Logic** (15 mins)
   - Modify `init()` to auto-load
   - Modify `onDirectorySelected()` to save
   - Add `saveLastDirectory()` helper

5. **Settings UI** (10 mins)
   - Add checkbox to settings modal
   - Wire up in `loadSettings()` and `saveSettings()`

6. **Testing** (20 mins)
   - Run all test cases
   - Verify edge cases

**Total estimated time**: 70 minutes (1 session)

---

## Files to Modify

1. `/Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/crate/core/config.py`
   - Lines 19-31: Add config keys
   - After line 282: Add fallback helper function

2. `/Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/web/main.py`
   - After line 262: Add `/api/directory/initial` endpoint

3. `/Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/web/static/js/api.js`
   - After line 174: Add `getInitialDirectory()` method

4. `/Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/web/static/js/app.js`
   - Line ~84: Auto-load on startup
   - Line ~690: Save on browse
   - Before line 2606: Add `saveLastDirectory()` helper
   - Line ~2120: Load setting in `loadSettings()`
   - Line ~2363: Save setting in `saveSettings()`

5. `/Users/szenone/Documents/CODE/PYTHON/DJ/batch_rename/web/static/index.html`
   - Settings modal: Add checkbox for feature toggle

---

## Implementation Ready

This plan is complete and ready for implementation. All code is provided with exact line numbers and implementation details.

**Next Steps**: Wait for user to confirm v11 testing, then implement this feature.
