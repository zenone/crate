# Red Flags Analysis: Per-Album Smart Detection

**Date**: 2026-01-31
**Feature**: Per-Album Smart Detection
**Task**: #115 - Pre-Implementation Red Flags Review
**Status**: Analysis Complete

---

## Executive Summary

This document systematically addresses all potential red flags before implementing the per-album smart detection feature. Each concern is analyzed with specific scenarios, risks, and mitigations.

**Overall Risk Assessment**: ⚠️ **MODERATE**
- High complexity feature with multiple interaction points
- Significant race condition risks (mitigated)
- Moderate breaking change risk (feature flag mitigates)
- Good error handling design (graceful degradation)

**Recommendation**: ✅ **PROCEED WITH CAUTION**
- Follow implementation plan carefully
- Test thoroughly before enabling feature flag
- Monitor for issues in production

---

## 1. Initialization / Timing Issues

### 🚩 RED FLAG #1: Context Detection Not Complete Before User Action

**Scenario**:
```
T0: User loads directory
T1: Context detection API call starts (async)
T2: User immediately clicks "Apply to Selected" button
T3: Button is enabled but perAlbumState is empty/incomplete
→ RISK: Apply with no data, undefined behavior
```

**Risk Level**: 🔴 **CRITICAL**

**Mitigation Strategy**:
```javascript
// 1. Disable buttons until detection complete
showPerAlbumBanner(data) {
    if (data.status === "analyzing") {
        this.disableAllPerAlbumButtons();
        this.showLoadingSpinner();
    } else if (data.status === "complete") {
        this.enablePerAlbumButtons();
        this.hideLoadingSpinner();
    }
}

// 2. Defensive check in Apply handler
onApplyPerAlbumSelection() {
    if (!this.perAlbumState || !this.perAlbumState.albums) {
        console.error("Cannot apply: per-album state not ready");
        this.showToast("Please wait for detection to complete", "warning");
        return;
    }

    // Proceed with apply
    // ...
}
```

**Testing**: Load directory and immediately spam-click Apply button → should be disabled until detection completes

---

### 🚩 RED FLAG #2: Race Between Directory Load and Context Detection

**Scenario**:
```
T0: Load directory A → context detection A starts
T1: User immediately loads directory B → context detection B starts
T2: Detection A completes → shows banner for directory A
T3: User is viewing directory B files but sees directory A banner
→ RISK: Templates applied to wrong directory's files
```

**Risk Level**: 🔴 **CRITICAL**

**Mitigation Strategy**:
```javascript
class CrateApp {
    constructor() {
        this.currentDirectory = null;
        this.contextDetectionAbortController = null;
    }

    async loadDirectory(path) {
        // Cancel previous detection
        if (this.contextDetectionAbortController) {
            this.contextDetectionAbortController.abort();
            console.log("Cancelled previous context detection");
        }

        // Clear previous state immediately
        this.clearPerAlbumState();

        // Track current directory
        this.currentDirectory = path;

        // Load files
        await this.loadFilesFromDirectory(path);

        // Start new detection with abort controller
        this.contextDetectionAbortController = new AbortController();
        await this.checkSmartDetection(path, this.contextDetectionAbortController.signal);
    }

    async checkSmartDetection(path, signal) {
        try {
            const data = await fetchContextDetection(path, signal);

            // CRITICAL: Verify directory hasn't changed
            if (path !== this.currentDirectory) {
                console.log("Ignoring stale context detection for:", path);
                return;
            }

            this.showPerAlbumBanner(data);
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log("Context detection aborted (expected)");
                return;
            }
            throw error;
        }
    }
}
```

**Testing**:
1. Load directory A
2. Immediately (< 100ms) load directory B
3. Verify only directory B banner shows
4. Verify no banner from directory A appears

---

### 🚩 RED FLAG #3: State Cleared Too Early vs Too Late

**Scenario (Too Early)**:
```
T0: User selects albums in banner
T1: User clicks "Apply to Selected"
T2: State cleared prematurely
T3: Preview generation fails (no state)
→ RISK: Feature breaks mid-operation
```

**Scenario (Too Late)**:
```
T0: User loads directory A, selects albums
T1: User loads directory B (state not cleared)
T2: State from directory A still present
T3: Directory B templates applied with directory A selections
→ RISK: Wrong albums get wrong templates
```

**Risk Level**: 🟠 **HIGH**

**Mitigation Strategy**:
```javascript
// Clear state at the RIGHT moment - start of new directory load
loadDirectory(path) {
    // 1. FIRST: Clear state (even before cancelling detection)
    this.clearPerAlbumState();

    // 2. Cancel previous operations
    if (this.contextDetectionAbortController) {
        this.contextDetectionAbortController.abort();
    }

    // 3. Set new directory
    this.currentDirectory = path;

    // 4. Proceed with load
    // ...
}

// State structure includes directory path for validation
this.perAlbumState = {
    directory: path,  // ADDED: Track which directory this state is for
    albums: [],
    timestamp: Date.now()  // ADDED: Track when state was created
};

// Validate state before using
isPerAlbumStateValid() {
    if (!this.perAlbumState) return false;
    if (this.perAlbumState.directory !== this.currentDirectory) {
        console.warn("Per-album state is for different directory");
        return false;
    }

    // Check if state is too old (> 5 minutes)
    const age = Date.now() - this.perAlbumState.timestamp;
    if (age > 5 * 60 * 1000) {
        console.warn("Per-album state is stale");
        return false;
    }

    return true;
}
```

**Testing**:
1. Load directory A, select albums
2. Load directory B immediately
3. Verify state from A not present in B
4. Verify no errors/warnings in console

---

### 🚩 RED FLAG #4: Dependencies Not Ready (Settings Not Loaded)

**Scenario**:
```
T0: App initializes
T1: Context detection code runs before settings loaded
T2: Feature flag undefined
T3: Code attempts to access this.settings.enablePerAlbumDetection → undefined
→ RISK: Feature behaves unexpectedly
```

**Risk Level**: 🟡 **MEDIUM**

**Mitigation Strategy**:
```javascript
async init() {
    // 1. Load settings FIRST
    await this.loadSettings();

    // 2. Initialize UI
    this.setupEventListeners();

    // 3. Load initial directory (if "remember last directory" enabled)
    await this.loadInitialDirectory();

    // 4. Context detection runs AFTER settings loaded
    this.checkSmartDetection();
}

// Defensive checks
checkSmartDetection() {
    // Guard: Settings not loaded yet
    if (!this.settings) {
        console.warn("Settings not loaded, skipping smart detection");
        return;
    }

    // Guard: Feature disabled
    if (!this.settings.enableSmartDetection) {
        return;
    }

    // Guard: Per-album feature disabled
    if (!this.settings.enablePerAlbumDetection) {
        // Use single-banner mode
        this.checkSmartDetectionSingleMode();
        return;
    }

    // Proceed with per-album detection
    this.checkSmartDetectionPerAlbumMode();
}
```

**Testing**:
1. Reload app with network throttling (slow settings load)
2. Verify feature waits for settings
3. Verify no console errors

---

## 2. Breaking Changes

### 🚩 RED FLAG #5: Current Single-Banner Flow Breaks

**Affected Code Paths**:
```
✅ checkSmartDetectionForDirectory()  - Must handle both modes
✅ showSmartBanner()                  - Must render correct banner type
✅ onSmartBannerUseThis()             - Must handle single vs per-album
✅ onSmartBannerIgnore()              - Must handle single vs per-album
✅ dismissSmartBanner()               - Must handle both banner types
```

**Risk Level**: 🟠 **HIGH**

**Mitigation Strategy**:
```javascript
// Branching logic based on feature flag and album count
checkSmartDetectionForDirectory() {
    const data = await fetchContextDetection();

    // Decision tree
    const usePerAlbumMode =
        this.settings.enablePerAlbumDetection &&  // Feature enabled
        data.perAlbumMode &&                      // Backend supports it
        data.albums &&                             // Has albums array
        data.albums.length > 1;                    // Multiple albums

    if (usePerAlbumMode) {
        this.showPerAlbumBanner(data);
    } else {
        this.showSingleBanner(data);  // Current behavior (unchanged)
    }
}

// Separate functions for each mode (no mixing)
showSingleBanner(data) {
    // Current implementation (untouched)
    // ...
}

showPerAlbumBanner(data) {
    // New implementation
    // ...
}

// Event handlers check mode
onSmartBannerUseThis() {
    if (this.perAlbumState && this.perAlbumState.enabled) {
        this.onPerAlbumApply();
    } else {
        this.onSingleBannerApply();  // Current behavior
    }
}
```

**Testing (Regression Tests)**:
1. Feature flag OFF → verify single-banner still works exactly as before
2. Single album directory → verify single-banner used (not per-album)
3. Feature flag ON but backend returns single-banner data → verify fallback works

---

### 🚩 RED FLAG #6: Temporary Template System Interaction

**Current Behavior**: User clicks "Use This" → sets `this.temporaryTemplate` → applies to all files

**New Behavior**: Per-album mode → multiple templates (one per album)

**Conflict Scenario**:
```
T0: User has temporaryTemplate = "{artist} - {title}" set from previous action
T1: User loads new directory (multi-album)
T2: Shows per-album banner
T3: User applies per-album templates
→ QUESTION: Which takes precedence? Temporary template or per-album templates?
```

**Risk Level**: 🟡 **MEDIUM**

**Mitigation Strategy**:
```javascript
// DECISION: Per-album mode REPLACES temporary template
showPerAlbumBanner(data) {
    // Clear temporary template (per-album templates take over)
    this.temporaryTemplate = null;

    // Show per-album banner
    // ...
}

// When applying per-album templates
onPerAlbumApply() {
    // Store per-album templates (not temporary template)
    this.perAlbumTemplates = {};
    this.perAlbumState.albums.forEach(album => {
        if (album.selected) {
            this.perAlbumTemplates[album.path] = album.detection.suggestedTemplate;
        }
    });

    // Clear temporary template (avoid conflicts)
    this.temporaryTemplate = null;

    // Generate previews
    this.loadAllPreviews();
}

// Preview generation checks per-album first
getTemplateForFile(file) {
    // 1. Check per-album templates first
    const albumPath = this.getAlbumPathForFile(file);
    if (this.perAlbumTemplates && this.perAlbumTemplates[albumPath]) {
        return this.perAlbumTemplates[albumPath];
    }

    // 2. Fall back to temporary template
    if (this.temporaryTemplate) {
        return this.temporaryTemplate;
    }

    // 3. Fall back to settings template
    return this.settings.renameTemplate;
}
```

**Testing**:
1. Set temporary template → load multi-album directory → verify temporary template cleared
2. Apply per-album templates → verify previews use per-album templates (not temporary)
3. Apply per-album, then load single-album directory → verify can set temporary template again

---

### 🚩 RED FLAG #7: Preview Generation Code Paths

**Current**: Single template for all files
**New**: Per-album templates (different template per subdirectory)

**Risk**: Preview generation must iterate albums and apply correct template

**Risk Level**: 🟠 **HIGH**

**Mitigation Strategy**:
```javascript
// Refactor preview generation to be template-aware
async loadAllPreviews() {
    const files = this.currentFiles;

    for (const file of files) {
        // Get correct template for this file
        const template = this.getTemplateForFile(file);

        // Generate preview with correct template
        const preview = await this.api.previewRename(file.path, template);

        // Update UI
        this.updateFilePreview(file.path, preview);
    }
}

// Helper: Determine which album this file belongs to
getAlbumPathForFile(file) {
    if (!this.perAlbumState || !this.perAlbumState.albums) {
        return null;
    }

    // Find album that contains this file
    for (const album of this.perAlbumState.albums) {
        if (file.path.startsWith(album.path)) {
            return album.path;
        }
    }

    return null;
}

// Helper: Get correct template (per-album, temporary, or settings)
getTemplateForFile(file) {
    // 1. Per-album mode active?
    if (this.perAlbumTemplates) {
        const albumPath = this.getAlbumPathForFile(file);
        if (albumPath && this.perAlbumTemplates[albumPath]) {
            return this.perAlbumTemplates[albumPath];
        }
    }

    // 2. Temporary template set?
    if (this.temporaryTemplate) {
        return this.temporaryTemplate;
    }

    // 3. Fall back to settings
    return this.settings.renameTemplate;
}
```

**Testing**:
1. Multi-album directory with 2 albums selected, 1 unselected
2. Verify selected albums show smart template in preview
3. Verify unselected album shows settings template in preview
4. Verify no files get wrong template

---

### 🚩 RED FLAG #8: Rename Operation Must Pass Per-Album Data

**Current**: `executeRename(template)` - single template parameter
**New**: Must pass per-album selections to backend

**Risk**: Backend must know which albums to apply which template to

**Risk Level**: 🟠 **HIGH**

**Mitigation Strategy**:
```javascript
// Modify rename operations to accept per-album selections
async executeRename() {
    // Build rename request payload
    const payload = {
        directory: this.currentDirectory,
        template: this.settings.renameTemplate,  // Global fallback
        perAlbumSelections: null  // NEW: Per-album data
    };

    // If per-album mode active, include selections
    if (this.perAlbumTemplates) {
        payload.perAlbumSelections = {};

        this.perAlbumState.albums.forEach(album => {
            payload.perAlbumSelections[album.path] = {
                selected: album.selected,
                template: album.selected ? album.detection.suggestedTemplate : null
            };
        });
    }

    // Send to backend
    const result = await this.api.executeRename(payload);

    // Handle result
    // ...
}

// Backend endpoint must handle per-album selections
// web/main.py
@app.post("/api/rename")
async def rename_files(request: RenameRequest):
    if request.perAlbumSelections:
        # Per-album mode: apply templates per album
        results = {}
        for album_path, selection in request.perAlbumSelections.items():
            if selection['selected']:
                template = selection['template']
                results[album_path] = apply_template_to_album(album_path, template)
            else:
                # Use global template
                results[album_path] = apply_template_to_album(album_path, request.template)

        return {"perAlbumResults": results}
    else:
        # Single-template mode (current behavior)
        return apply_template_globally(request.template)
```

**Testing**:
1. Rename with per-album selections
2. Verify backend receives correct payload
3. Verify correct template applied per album
4. Verify unselected albums use global template

---

## 3. Error Handling

### 🚩 RED FLAG #9: Context Detection Fails for One Album

**Scenario**:
```
Album A: Detection succeeds → ALBUM detected
Album B: Detection throws exception → undefined
Album C: Detection succeeds → SINGLES detected
→ QUESTION: Show partial results? Skip Album B? Show error?
```

**Risk Level**: 🟡 **MEDIUM**

**Mitigation Strategy**:
```python
# Backend: crate/core/context_detection.py
def analyze_all_albums(directory, files):
    albums = group_files_by_subdirectory(files)
    results = []

    for album_path, album_files in albums.items():
        try:
            detection = analyze_album_group(album_files)
            results.append({
                "path": album_path,
                "fileCount": len(album_files),
                "detection": detection,
                "error": None
            })
        except Exception as e:
            logger.warning(f"Detection failed for {album_path}: {e}")
            # Include album but mark as error
            results.append({
                "path": album_path,
                "fileCount": len(album_files),
                "detection": {"type": "UNKNOWN", "confidence": "none"},
                "error": str(e)
            })

    return results  # Return partial results
```

```javascript
// Frontend: Show album with error state
renderAlbumItem(album) {
    if (album.error) {
        return `
            <div class="album-item album-item-error">
                <label class="album-checkbox-label">
                    <input type="checkbox" disabled>
                    <span class="album-detection-icon">⚠</span>
                    <span class="album-name">${album.path}</span>
                </label>
                <span class="album-error-badge">Detection failed</span>
            </div>
        `;
    }

    // Normal rendering
    // ...
}
```

**UX**: Show partial results, disable checkbox for failed albums, allow user to proceed with successful albums

**Testing**:
1. Create album with corrupted files
2. Verify detection fails gracefully for that album
3. Verify other albums still work
4. Verify user can apply templates to successful albums

---

### 🚩 RED FLAG #10: Backend Returns Malformed Data

**Scenario**:
```
API response:
{
    "albums": "not an array",  // Wrong type
    "perAlbumMode": true
}
→ RISK: Frontend crashes trying to iterate albums
```

**Risk Level**: 🟡 **MEDIUM**

**Mitigation Strategy**:
```javascript
async checkSmartDetection() {
    try {
        const data = await fetchContextDetection();

        // Validate response structure
        if (!data || typeof data !== 'object') {
            throw new Error("Invalid response: not an object");
        }

        if (data.perAlbumMode) {
            if (!Array.isArray(data.albums)) {
                throw new Error("Invalid response: albums is not an array");
            }

            if (data.albums.length === 0) {
                throw new Error("Invalid response: albums array is empty");
            }

            // Additional validation
            for (const album of data.albums) {
                if (!album.path || !album.fileCount || !album.detection) {
                    throw new Error(`Invalid album data: ${JSON.stringify(album)}`);
                }
            }
        }

        // Validation passed, proceed
        this.showPerAlbumBanner(data);

    } catch (error) {
        console.error("Context detection failed:", error);

        // Graceful degradation: fall back to single-banner or disable
        if (this.settings.enableSmartDetection) {
            this.checkSmartDetectionSingleMode();  // Try single-banner
        } else {
            this.showToast("Smart detection unavailable", "info");
        }
    }
}
```

**Testing**:
1. Mock backend to return malformed data
2. Verify frontend catches error
3. Verify graceful degradation
4. Verify no console errors crash app

---

### 🚩 RED FLAG #11: Preview Generation Fails Mid-Operation

**Scenario**:
```
T0: User applies per-album templates
T1: Preview for Album A files loading...
T2: Preview for file #5 fails (network error)
T3: Remaining files not previewed
→ QUESTION: Show partial previews? Retry failed files? Skip failed files?
```

**Risk Level**: 🟡 **MEDIUM**

**Mitigation Strategy**:
```javascript
async loadAllPreviewsWithPerAlbumTemplates() {
    const results = {
        success: [],
        failed: []
    };

    for (const file of this.currentFiles) {
        try {
            const template = this.getTemplateForFile(file);
            const preview = await this.api.previewRename(file.path, template);

            this.updateFilePreview(file.path, preview);
            results.success.push(file.path);

        } catch (error) {
            console.error(`Preview failed for ${file.path}:`, error);

            // Show error in preview column
            this.updateFilePreview(file.path, {
                preview: "[Error]",
                error: true
            });

            results.failed.push({ path: file.path, error: error.message });
        }
    }

    // Show summary
    if (results.failed.length > 0) {
        this.showToast(
            `Previews generated (${results.success.length} succeeded, ${results.failed.length} failed)`,
            "warning"
        );
    } else {
        this.showToast("Previews updated successfully", "success");
    }

    return results;
}
```

**UX**: Show partial previews, indicate failed files with "[Error]", allow user to proceed with successful files

**Testing**:
1. Mock API to fail for some files
2. Verify partial previews shown
3. Verify error indication in preview column
4. Verify user can still rename successful files

---

### 🚩 RED FLAG #12: User Lacks Permission to Rename Some Albums

**Scenario**:
```
Album A: /Music/ReadOnly/Album1  (user has read-only permission)
Album B: /Music/Editable/Album2  (user has write permission)

User selects both albums and clicks Rename
→ QUESTION: Fail entirely? Rename Album B only? Show partial success?
```

**Risk Level**: 🟡 **MEDIUM**

**Mitigation Strategy**:
```python
# Backend: web/main.py
@app.post("/api/rename")
async def rename_files(request: RenameRequest):
    results = {
        "renamed": 0,
        "failed": 0,
        "errors": [],
        "perAlbumResults": {}
    }

    if request.perAlbumSelections:
        for album_path, selection in request.perAlbumSelections.items():
            if not selection['selected']:
                continue

            try:
                # Check permissions before renaming
                if not has_write_permission(album_path):
                    raise PermissionError(f"No write permission for {album_path}")

                # Rename files in this album
                album_results = rename_album_files(album_path, selection['template'])

                results["renamed"] += album_results["renamed"]
                results["perAlbumResults"][album_path] = album_results

            except PermissionError as e:
                logger.error(f"Permission denied for {album_path}: {e}")
                results["failed"] += 1
                results["errors"].append({
                    "album": album_path,
                    "error": str(e),
                    "type": "permission"
                })

            except Exception as e:
                logger.error(f"Rename failed for {album_path}: {e}")
                results["failed"] += 1
                results["errors"].append({
                    "album": album_path,
                    "error": str(e),
                    "type": "unknown"
                })

    return results
```

```javascript
// Frontend: Show detailed error message
onRenameComplete(results) {
    if (results.errors && results.errors.length > 0) {
        const errorDetails = results.errors.map(e =>
            `${e.album}: ${e.error}`
        ).join('\n');

        this.showToast(
            `Renamed ${results.renamed} files, ${results.failed} failed:\n${errorDetails}`,
            "warning"
        );
    } else {
        this.showToast(`Successfully renamed ${results.renamed} files`, "success");
    }
}
```

**UX**: Partial success - rename what we can, show detailed errors for failures

**Testing**:
1. Create read-only album directory
2. Select both read-only and writable albums
3. Verify writable album renamed successfully
4. Verify read-only album shows permission error
5. Verify clear error message to user

---

## 4. Edge Cases

### 🚩 RED FLAG #13: User Changes Selection During Preview Loading

**Scenario**:
```
T0: User applies per-album templates (Album A, B, C selected)
T1: Preview loading starts (100 files, will take 10 seconds)
T2: User unchecks Album A (mid-loading)
T3: Previews for Album A still loading with smart template
→ RISK: Previews show smart template but album now unselected (stale state)
```

**Risk Level**: 🟠 **HIGH**

**Mitigation Strategy**:
```javascript
// Disable selection UI during preview loading
onApplyPerAlbumSelection() {
    // Lock UI
    this.lockPerAlbumState();

    // Load previews
    await this.loadAllPreviewsWithPerAlbumTemplates();

    // Unlock UI
    this.unlockPerAlbumState();
}

lockPerAlbumState() {
    this.perAlbumStateLocked = true;

    // Disable all checkboxes
    document.querySelectorAll('.album-checkbox').forEach(cb => {
        cb.disabled = true;
    });

    // Disable quick action buttons
    document.getElementById('select-all-albums').disabled = true;
    document.getElementById('deselect-all-albums').disabled = true;
    document.getElementById('invert-selection').disabled = true;

    // Show loading indicator
    document.getElementById('apply-per-album-selection').innerHTML =
        '<span class="spinner"></span> Loading previews...';
}

unlockPerAlbumState() {
    this.perAlbumStateLocked = false;

    // Re-enable UI
    document.querySelectorAll('.album-checkbox').forEach(cb => {
        cb.disabled = false;
    });

    // Re-enable buttons
    // ...
}
```

**Alternative Mitigation** (if user should be able to cancel):
```javascript
// Allow user to change selection → cancel and restart previews
onAlbumSelectionChange() {
    if (this.previewLoadingInProgress) {
        // Cancel in-flight previews
        this.previewAbortController.abort();

        // Show message
        this.showToast("Cancelled preview loading. Please re-apply.", "info");

        // Clear previews
        this.clearAllPreviews();

        // Reset state
        this.previewLoadingInProgress = false;
    }

    // Update state
    // ...
}
```

**Decision**: **Lock UI during preview loading** (simpler, less error-prone)

**Testing**:
1. Apply per-album templates
2. Try to change selection during preview loading
3. Verify checkboxes disabled
4. Verify no stale previews shown

---

### 🚩 RED FLAG #14: User Starts Rename Mid-Preview Loading

**Scenario**:
```
T0: User applies per-album templates
T1: Preview loading (50% complete)
T2: User clicks "Rename" button (impatient)
T3: Some files have previews, some don't
→ RISK: Rename files without user seeing previews
```

**Risk Level**: 🔴 **CRITICAL**

**Mitigation Strategy**:
```javascript
// Disable Rename button until previews complete
loadAllPreviewsWithPerAlbumTemplates() {
    // Disable rename button
    this.disableRenameButton();

    // Load previews
    for (const file of this.currentFiles) {
        // ...
    }

    // Re-enable rename button
    this.enableRenameButton();
}

disableRenameButton() {
    const renameBtn = document.getElementById('rename-selected-btn');
    renameBtn.disabled = true;
    renameBtn.setAttribute('aria-disabled', 'true');
    renameBtn.title = "Please wait for previews to load";
}

enableRenameButton() {
    const renameBtn = document.getElementById('rename-selected-btn');
    renameBtn.disabled = false;
    renameBtn.removeAttribute('aria-disabled');
    renameBtn.title = "Rename selected files";
}
```

**Testing**:
1. Apply per-album templates
2. Try to click Rename button during preview loading
3. Verify button is disabled
4. Verify button enabled after previews complete

---

### 🚩 RED FLAG #15: 1000+ Album Subdirectories

**Scenario**: User loads `/Music/Collection/` with 1000 album subdirectories

**Risk Level**: 🔴 **CRITICAL** (Performance)

**Mitigation Strategy**:
```python
# Backend: Limit max albums analyzed
MAX_ALBUMS_FOR_PER_ALBUM_MODE = 100

def analyze_directory_context(directory, files):
    albums = group_files_by_subdirectory(files)

    if len(albums) > MAX_ALBUMS_FOR_PER_ALBUM_MODE:
        logger.warning(f"Too many albums ({len(albums)}), limiting to {MAX_ALBUMS_FOR_PER_ALBUM_MODE}")

        # Truncate album list
        albums = dict(list(albums.items())[:MAX_ALBUMS_FOR_PER_ALBUM_MODE])

        # Return with warning
        return {
            "perAlbumMode": True,
            "albums": analyze_albums(albums),
            "warning": f"Only analyzing first {MAX_ALBUMS_FOR_PER_ALBUM_MODE} albums (out of {len(albums)} total)",
            "truncated": True
        }

    return {
        "perAlbumMode": True,
        "albums": analyze_albums(albums)
    }
```

```javascript
// Frontend: Show warning to user
showPerAlbumBanner(data) {
    if (data.warning) {
        this.showToast(data.warning, "warning");
    }

    if (data.truncated) {
        // Add warning badge to banner
        const warningBadge = `
            <div class="banner-warning">
                ⚠️ ${data.warning}
            </div>
        `;
        // Insert into banner
    }

    // Render albums (limited to 100)
    // ...
}
```

**Testing**:
1. Create directory with 200 album subdirectories
2. Load directory
3. Verify only 100 albums analyzed
4. Verify warning shown to user
5. Verify performance acceptable (< 2 seconds)

---

### 🚩 RED FLAG #16: Album with 0 Files

**Scenario**: Empty subdirectory or all files filtered out (e.g., only JPGs, no MP3s)

**Risk Level**: 🟢 **LOW**

**Mitigation Strategy**:
```python
# Backend: Skip empty albums
def group_files_by_subdirectory(files):
    albums = {}

    for file in files:
        album_path = get_subdirectory(file)
        if album_path not in albums:
            albums[album_path] = []
        albums[album_path].append(file)

    # Remove empty albums
    albums = {path: files for path, files in albums.items() if len(files) > 0}

    return albums
```

**Testing**:
1. Create directory with empty subdirectory
2. Verify empty subdirectory not shown in banner
3. Verify no errors

---

### 🚩 RED FLAG #17: User Loads Directory While Rename In Progress

**Scenario**:
```
T0: User starts rename operation (100 files)
T1: Rename processing (50% complete)
T2: User loads different directory
T3: Rename still in progress for old directory
→ RISK: State confusion, unclear which operation is happening
```

**Risk Level**: 🟠 **HIGH**

**Mitigation Strategy**:
```javascript
// Block directory loading during rename
onDirectorySelected(newPath) {
    // Check if rename in progress
    if (this.renameInProgress) {
        this.showToast(
            "Cannot load directory while rename operation is in progress. Please wait or cancel the operation.",
            "warning"
        );
        return;
    }

    // Proceed with directory load
    this.loadDirectory(newPath);
}

// Set flag during rename
executeRename() {
    this.renameInProgress = true;

    // Execute rename
    // ...
}

onRenameComplete() {
    this.renameInProgress = false;

    // ...
}
```

**Testing**:
1. Start rename operation
2. Try to load different directory mid-rename
3. Verify blocked with clear message
4. Verify can load after rename completes

---

### 🚩 RED FLAG #18: Mixed Flat + Nested Structure

**Scenario**:
```
/Music/New_Acquisitions/
    file1.mp3  (in root)
    file2.mp3  (in root)
    Album_A/
        track1.mp3
        track2.mp3
    Album_B/
        track1.mp3
        track2.mp3
```

**Risk**: How to group root-level files?

**Risk Level**: 🟡 **MEDIUM**

**Mitigation Strategy**:
```python
def group_files_by_subdirectory(directory, files):
    albums = {}

    for file in files:
        # Get subdirectory relative to loaded directory
        rel_path = os.path.relpath(file, directory)
        subdir = os.path.dirname(rel_path)

        if subdir == '' or subdir == '.':
            # File is in root directory
            album_key = '[Root Files]'
        else:
            # File is in subdirectory
            album_key = subdir

        if album_key not in albums:
            albums[album_key] = []

        albums[album_key].append(file)

    return albums
```

**UX**: Show root-level files as virtual album "[Root Files]"

**Testing**:
1. Create mixed structure
2. Verify root files shown as "[Root Files]" album
3. Verify subdirectory files grouped correctly
4. Verify can select/unselect each group independently

---

## 5. Worst-Case Scenarios

### 🔥 WORST CASE #1: Complete Feature Failure

**Scenario**: Per-album detection completely broken, users can't rename anything

**Probability**: Low (feature flag OFF by default)

**Impact**: High if feature enabled

**Mitigation**:
1. **Feature Flag OFF by default** → Users must opt-in
2. **Graceful degradation** → Falls back to single-banner mode on any error
3. **Rollback plan** → Toggle feature flag OFF immediately
4. **Monitoring** → Log all errors to catch issues early

**Recovery Plan**:
```
1. Detect issue (user report or monitoring alert)
2. Immediately toggle feature flag OFF in settings
3. Inform users to refresh browser
4. System falls back to single-banner mode (working)
5. Investigate root cause
6. Fix and re-deploy
7. Re-enable feature flag after validation
```

---

### 🔥 WORST CASE #2: Wrong Templates Applied (Data Corruption Risk)

**Scenario**: Bug causes smart template applied to wrong albums → files renamed incorrectly

**Probability**: Low (extensive validation)

**Impact**: **CRITICAL** (user data loss)

**Mitigation**:
1. **Preview before rename** → User sees exact changes before executing
2. **Per-album validation** → Verify template matches album before renaming
3. **Undo operation** → Users can revert renames (existing feature)
4. **Extensive testing** → Comprehensive test plan covers all scenarios

**Prevention Code**:
```javascript
executeRename() {
    // CRITICAL: Re-validate per-album selections before rename
    if (!this.isPerAlbumStateValid()) {
        this.showToast("Cannot rename: per-album state is invalid. Please reload directory.", "error");
        return;
    }

    // Log selection for debugging
    console.log("Executing rename with per-album selections:", this.perAlbumTemplates);

    // Proceed with rename
    // ...
}
```

**Recovery**: User uses "Undo" feature to revert renames

---

### 🔥 WORST CASE #3: Performance Degradation (App Becomes Unusable)

**Scenario**: Feature causes app to freeze/lag with large directories

**Probability**: Medium (depending on directory size)

**Impact**: Medium (annoying but not data loss)

**Mitigation**:
1. **Limit max albums** → 100 albums max analyzed
2. **Virtual scrolling** → Only render visible albums in UI
3. **Progress indicators** → Show user what's happening
4. **Cancellation** → User can cancel slow operations

**Performance Budget**:
- Context detection: < 2 seconds for 100 albums
- UI rendering: < 200ms for 100 albums
- Preview generation: Same as current (not degraded)

**Testing**: Load directory with 100 albums, measure performance, optimize if needed

---

## 6. Summary & Recommendations

### Risk Summary

| Category | Red Flags | Critical | High | Medium | Low |
|----------|-----------|----------|------|--------|-----|
| Initialization/Timing | 4 | 2 | 1 | 1 | 0 |
| Breaking Changes | 4 | 0 | 3 | 1 | 0 |
| Error Handling | 4 | 0 | 0 | 4 | 0 |
| Edge Cases | 8 | 2 | 2 | 2 | 2 |
| **TOTAL** | **20** | **4** | **6** | **8** | **2** |

### Critical Risks (Must Address Before Implementation)

1. ✅ **Context detection race condition** → Mitigated with abort controllers + directory tracking
2. ✅ **Rename with wrong templates** → Mitigated with state validation + preview system
3. ✅ **User starts rename mid-preview** → Mitigated with button disabling
4. ✅ **1000+ albums performance** → Mitigated with 100 album limit

### Recommendations

✅ **PROCEED WITH IMPLEMENTATION** with following conditions:

1. **Implement all mitigations** described in this document
2. **Feature flag OFF by default** → Opt-in for users
3. **Extensive testing** following test plan (Task #112)
4. **Gradual rollout**:
   - Phase 1: Deploy with flag OFF (no impact)
   - Phase 2: Enable for internal testing
   - Phase 3: Enable for users after validation
5. **Monitoring**: Log errors, track usage, measure performance

### Implementation Order (Safest Approach)

1. **Backend first** (less risky, easier to test)
   - Implement album grouping
   - Implement per-album detection
   - Add feature flag checks
   - Test thoroughly

2. **Frontend state management** (foundation)
   - Add per-album state structure
   - Implement state lifecycle (clear, lock, unlock)
   - Add validation functions
   - Test state transitions

3. **Frontend UI** (visible to user)
   - Render per-album banner
   - Wire up interactions
   - Add error handling
   - Test all interactions

4. **Integration** (connect pieces)
   - Preview generation with per-album templates
   - Rename operation with per-album selections
   - Error handling end-to-end
   - Test complete workflows

5. **Polish** (UX improvements)
   - Loading indicators
   - Animations
   - Keyboard shortcuts
   - Accessibility

### Safety Net

**If anything goes wrong during implementation or testing**:

```
ROLLBACK PLAN:
1. Toggle feature flag OFF in settings
2. Deploy rollback
3. Investigate issue
4. Fix and re-test
5. Re-enable feature

FALLBACK BEHAVIOR:
- Feature flag OFF → Single-banner mode (current behavior, working)
- Detection fails → Single-banner mode
- Malformed data → Single-banner mode
- Any error → Graceful degradation
```

---

## Conclusion

**Overall Assessment**: ⚠️ **MODERATE RISK - PROCEED WITH CAUTION**

The per-album smart detection feature is complex with multiple potential failure points, but all critical risks have been identified and mitigated. The feature flag provides a safety net, and graceful degradation ensures the app continues working even if the feature fails.

**Key Success Factors**:
1. ✅ Comprehensive risk analysis (this document)
2. ✅ Detailed design and UI specs (Tasks #108, #109)
3. ⏳ Careful implementation following mitigations (Tasks #110, #111)
4. ⏳ Extensive testing (Task #112)
5. ⏳ Clear documentation (Task #113)
6. ✅ Feature flag for safety (Task #114)

**Recommendation**: ✅ **APPROVED FOR IMPLEMENTATION**

Proceed with tasks in order: #114 (feature flag) → #110 (backend) → #111 (frontend) → #112 (testing) → #113 (documentation)

---

**Red Flags Analysis Status**: ✅ **COMPLETE**
**Next Task**: #114 (Feature flag implementation) followed by #110 (Backend implementation)
