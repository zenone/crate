# Design Document: Per-Album Smart Detection

**Date**: 2026-01-31
**Feature**: Per-album smart track detection and template application
**Status**: Design Phase (Task #108)

---

## Problem Statement

### Current Limitation
Smart Track Detection operates globally across all files in a loaded directory. When a parent directory contains multiple album subdirectories, the system shows ONE banner with ONE template suggestion that applies to ALL albums.

### Real-World Scenario
DJ loads `/Music/New_Acquisitions/` containing 10 album subdirectories:
- Some albums need smart template (`{track} - {title}`)
- Some albums are already perfectly named
- Some albums are compilations (shouldn't use track numbers)
- No way to selectively apply templates per album

### Business Impact
- User must load each album individually (10 separate operations)
- High friction, low efficiency
- Error-prone workflow
- Defeats purpose of batch renaming

---

## Proposed Solution

### High-Level Overview
Enable per-album smart detection with low-friction selection UI:

1. **Detection**: Analyze files grouped by subdirectory (per-album analysis)
2. **Presentation**: Show list of albums with detection results and suggested templates
3. **Selection**: User quickly selects which albums should use smart template
4. **Application**: Apply correct template per album during rename

### Key Principle
**LOW FRICTION** - Minimize clicks, maximize clarity, instant feedback

---

## User Workflows

### Primary Flow (Happy Path)

1. **Load Directory**
   ```
   User: Opens /Music/New_Acquisitions/ (contains 10 album subdirs)
   System: Loads all files from all subdirectories
   ```

2. **Context Detection**
   ```
   System: Groups files by subdirectory
   System: Runs context detection per album (parallel)
   System: Analyzes each album independently
   ```

3. **Show Per-Album Banner**
   ```
   System: Displays banner with album list
   For each album:
     - Album name (subdirectory name)
     - File count
     - Detection result (ALBUM/SINGLES/etc)
     - Suggested template
     - Checkbox (selected by default if detection = ALBUM)
   ```

4. **User Selection**
   ```
   User: Reviews list
   User: Unchecks albums that don't need smart template
   User: Keeps albums checked that need smart template
   Quick actions: "Select All", "Deselect All"
   ```

5. **Apply Templates**
   ```
   User: Clicks "Apply to Selected" button
   System: Generates previews with correct template per album
     - Selected albums → use smart template
     - Unselected albums → use global template from settings
   System: Updates preview column
   ```

6. **Review & Rename**
   ```
   User: Reviews previews
   User: Clicks Rename button
   System: Executes rename with per-album templates
   System: Only renames selected files
   ```

### Alternative Flow: Single Banner Fallback

```
IF feature flag OFF OR only 1 album detected:
  Show current single-banner UI (backward compatibility)
ELSE:
  Show per-album multi-selection UI
```

---

## Edge Cases & Solutions

### 1. Flat Directory (No Subdirectories)

**Scenario**: User loads directory with files but no subdirectories
**Solution**: Treat entire directory as single album → show current single-banner UI

```python
if all files in same directory:
    use_single_banner_mode()
else:
    use_per_album_mode()
```

### 2. Mixed Structure

**Scenario**: Some files in parent directory, some in subdirectories
**Solution**: Create virtual album "Root Files" for parent-level files

```
Albums detected:
- [Root Files] (5 files in parent directory)
- Album_A (12 files in subdirectory)
- Album_B (8 files in subdirectory)
```

### 3. Nested Subdirectories

**Scenario**: Albums contain disc subdirectories (Album_A/Disc_1/, Album_A/Disc_2/)
**Solution**: Only analyze first level of subdirectories

```
Current directory: /Music/New_Acquisitions/
Analyze:
  ✅ /Music/New_Acquisitions/Album_A/  (all files recursively)
  ✅ /Music/New_Acquisitions/Album_B/
Ignore:
  ❌ /Music/New_Acquisitions/Album_A/Disc_1/  (included in Album_A)
```

**Rationale**: Multi-disc detection already handles disc grouping within an album

### 4. Large Number of Albums (100+)

**Scenario**: User loads directory with 100+ album subdirectories
**Solutions**:
- **Performance**: Limit to first 100 albums analyzed (show warning)
- **UI**: Scrollable list with search/filter
- **UX**: Show progress indicator during analysis

```javascript
const MAX_ALBUMS = 100;
if (albums.length > MAX_ALBUMS) {
    showWarning(`Only analyzing first ${MAX_ALBUMS} albums for performance`);
    albums = albums.slice(0, MAX_ALBUMS);
}
```

### 5. Album Classification Conflicts

**Scenario**: Album subdirectory contains mix of ALBUM and SINGLES files
**Solution**: Use highest-confidence classification per album

```python
# Within one subdirectory
tracks_1_5 = ALBUM detection (high confidence)
tracks_6_10 = missing (gaps)
Result: PARTIAL_ALBUM → suggest template with caution
```

### 6. User Changes Selection Mid-Preview

**Scenario**: Preview loading → user toggles album selection → previews become stale
**Solution**: Cancel in-flight previews, regenerate with new selection

```javascript
onAlbumSelectionChange() {
    if (this.previewAbortController) {
        this.previewAbortController.abort();  // Cancel current previews
    }
    this.loadAllPreviews();  // Regenerate with new selection
}
```

### 7. User Changes Selection During Rename

**Scenario**: Rename in progress → user changes album selection
**Solution**: Disable selection UI during rename operation

```javascript
startRename() {
    this.disableAlbumSelectionUI();
    // ... execute rename ...
}

renameComplete() {
    this.enableAlbumSelectionUI();
}
```

### 8. Fast Directory Switches

**Scenario**: User loads Dir A → immediately loads Dir B → stale state from Dir A
**Solution**: Clear per-album state immediately on new directory load

```javascript
onDirectorySelected(newPath) {
    this.clearPerAlbumState();  // Clear immediately
    this.loadDirectory(newPath);
    this.checkSmartDetection();
}
```

---

## Data Model

### Frontend State

```javascript
// Main state object
app.perAlbumState = {
    enabled: false,  // Feature flag state
    albums: [
        {
            path: "New_Acquisitions/Album_A",  // Relative path from loaded directory
            name: "Greatest Hits",              // Album name (from metadata or dirname)
            fileCount: 12,
            files: ["01.mp3", "02.mp3", ...],  // File paths
            detection: {
                type: "ALBUM",                  // ALBUM, PARTIAL_ALBUM, SINGLES, etc.
                confidence: "high",             // high, medium, low
                suggestedTemplate: "{track} - {title}",
                reason: "Sequential tracks 1-12"
            },
            selected: true,                     // User selection
            expanded: false                     // UI expansion state
        },
        // ... more albums
    ],
    globalTemplate: "{track} - {title}"         // Fallback for unselected albums
};
```

### Backend Response (from `/api/preview/context`)

```json
{
    "perAlbumMode": true,
    "albums": [
        {
            "path": "New_Acquisitions/Album_A",
            "albumName": "Greatest Hits",
            "fileCount": 12,
            "files": ["file1.mp3", "file2.mp3"],
            "detection": {
                "type": "ALBUM",
                "confidence": "high",
                "suggestedTemplate": "{track} - {title}",
                "reason": "Sequential tracks 1-12"
            }
        }
    ],
    "globalSuggestion": "{track} - {title}"
}
```

### Rename Request Payload

```json
{
    "directory": "/Music/New_Acquisitions",
    "template": "{track} - {title}",            // Global template (for unselected)
    "perAlbumSelections": {
        "New_Acquisitions/Album_A": {
            "selected": true,
            "template": "{track} - {title}"
        },
        "New_Acquisitions/Album_B": {
            "selected": false,
            "template": null                    // Use global template
        }
    }
}
```

---

## Race Conditions & Mitigations

### 1. Context Detection Not Complete

**Race Condition**:
```
T0: User loads directory
T1: Context detection starts (async)
T2: User immediately clicks "Apply" button
T3: Context detection still running
→ RISK: Apply with incomplete/no data
```

**Mitigation**:
```javascript
// Disable action buttons until detection completes
showPerAlbumBanner(data) {
    if (data.status === "analyzing") {
        this.disableApplyButton();
        this.showSpinner();
    } else if (data.status === "complete") {
        this.enableApplyButton();
        this.hideSpinner();
    }
}
```

### 2. Preview Loading + Selection Change

**Race Condition**:
```
T0: User clicks "Apply" → preview loading starts
T1: Preview for Album_A loading...
T2: User unchecks Album_A
T3: Preview for Album_A completes (using smart template)
→ RISK: Preview shows smart template but album now unselected
```

**Mitigation**:
```javascript
onAlbumSelectionChange() {
    // Cancel all in-flight preview requests
    if (this.previewAbortController) {
        this.previewAbortController.abort();
    }

    // Regenerate previews with new selection
    this.loadAllPreviews();
}
```

### 3. Rename In Progress + Selection Change

**Race Condition**:
```
T0: User starts rename operation
T1: Rename processing Album_A with smart template
T2: User unchecks Album_A
T3: Rename continues with smart template (stale state)
→ RISK: Unexpected rename results
```

**Mitigation**:
```javascript
executeRename() {
    // Lock per-album state
    this.lockPerAlbumState();

    // Execute rename with locked state
    // ...
}

renameComplete() {
    // Unlock after completion
    this.unlockPerAlbumState();
}
```

### 4. Fast Directory Switches

**Race Condition**:
```
T0: Load /Music/DirA → context detection starts
T1: Load /Music/DirB → context detection starts
T2: DirA detection completes → shows banner for DirA
T3: User is viewing DirB files but sees DirA banner
→ RISK: Template applied to wrong files
```

**Mitigation**:
```javascript
loadDirectory(path) {
    // Cancel previous detection
    if (this.contextDetectionAbortController) {
        this.contextDetectionAbortController.abort();
    }

    // Clear previous state immediately
    this.clearPerAlbumState();

    // Track current directory
    this.currentDirectory = path;

    // Start new detection with directory tracking
    this.checkSmartDetection(path);
}

onContextDetectionComplete(path, data) {
    // Ignore if directory changed
    if (path !== this.currentDirectory) {
        console.log("Ignoring stale context detection result");
        return;
    }

    this.showPerAlbumBanner(data);
}
```

---

## Breaking Changes Assessment

### Features That Could Be Affected

1. **Smart Track Detection (Current Single Banner)** ⚠️
   - **Risk**: High
   - **Impact**: Replaced by per-album banner when feature enabled
   - **Mitigation**: Feature flag OFF by default, maintain single-banner as fallback

2. **Temporary Template System** ⚠️
   - **Risk**: Medium
   - **Impact**: Per-album templates override temporary template
   - **Mitigation**: Clear temporary template when showing per-album banner

3. **Banner Dismissal Behavior** ⚠️
   - **Risk**: Low
   - **Impact**: Dismissal applies to entire per-album banner, not per album
   - **Mitigation**: Document behavior, consider per-album dismissal in future

4. **Preview Generation** ⚠️
   - **Risk**: High
   - **Impact**: Must iterate albums and apply correct template
   - **Mitigation**: Refactor preview logic to accept per-album templates

5. **Rename Operations** ⚠️
   - **Risk**: High
   - **Impact**: Must pass per-album selections to backend
   - **Mitigation**: Add new parameter, maintain backward compatibility

### Code Paths Requiring Updates

**Frontend (`web/static/js/app.js`)**:
- ✅ `checkSmartDetectionForDirectory()` - Parse per-album response
- ✅ `showSmartBanner()` - Render per-album UI or single banner
- ✅ `onSmartBannerUseThis()` - Apply to selected albums only
- ✅ `loadAllPreviews()` - Apply per-album templates
- ✅ `executeRename()` - Pass per-album selections
- ✅ `executeRenameNow()` - Pass per-album selections
- ✅ `onDirectorySelected()` - Clear per-album state

**Backend (`crate/core/context_detection.py`)**:
- ✅ `analyze_directory_context()` - Group by subdirectory, return per-album
- ✅ New function: `group_files_by_subdirectory()`
- ✅ New function: `analyze_album_group()`

**Backend (`web/main.py`)**:
- ✅ `/api/preview` endpoint - Accept per-album selections
- ✅ `/api/rename` endpoint - Accept per-album selections
- ✅ Apply templates per album during rename

---

## Error Handling Strategy

### 1. Context Detection Fails for One Album

**Scenario**: Album_A detection succeeds, Album_B throws exception
**Handling**:
```python
for album in albums:
    try:
        result = analyze_album(album)
        results.append(result)
    except Exception as e:
        logger.warning(f"Detection failed for {album}: {e}")
        results.append({
            "path": album,
            "detection": {"type": "UNKNOWN", "confidence": "none"},
            "error": str(e)
        })
```

**UX**: Show album in list but indicate detection unavailable, disable checkbox

### 2. Backend Returns Malformed Data

**Scenario**: `/api/preview/context` returns invalid JSON
**Handling**:
```javascript
try {
    const data = await fetchContextDetection();
    if (!data.albums || !Array.isArray(data.albums)) {
        throw new Error("Invalid response structure");
    }
    this.showPerAlbumBanner(data);
} catch (error) {
    console.error("Per-album detection failed:", error);
    this.fallbackToSingleBanner();  // Graceful degradation
}
```

**UX**: Fall back to current single-banner behavior

### 3. User Has No Permission to Rename

**Scenario**: User can read directory but not write to Album_A
**Handling**:
- Backend validates permissions per album during rename
- Return partial success: `{ renamed: 8, failed: 4, errors: [...] }`
- Frontend shows which albums succeeded/failed

**UX**: Show detailed error message with album names that failed

### 4. Preview Generation Fails

**Scenario**: Preview API call fails for Album_A
**Handling**:
```javascript
try {
    const preview = await generatePreview(file, template);
    return preview;
} catch (error) {
    console.error(`Preview failed for ${file}:`, error);
    return { preview: "[Error]", error: true };
}
```

**UX**: Show "[Error]" in preview column, allow user to proceed or skip album

---

## Performance Considerations

### Analysis Performance

**Current**: Single analysis of all files (~100ms for 100 files)
**Per-Album**: Multiple analyses (10 albums × ~10ms = ~100ms)
**Conclusion**: Negligible performance difference

**Optimization**: Run album analyses in parallel
```python
async def analyze_all_albums(albums):
    tasks = [analyze_album(album) for album in albums]
    return await asyncio.gather(*tasks)
```

### UI Rendering Performance

**Concern**: Rendering 100+ album rows could be slow
**Solutions**:
- Limit to 100 albums (show warning if exceeded)
- Virtual scrolling for large lists
- Lazy rendering (render visible rows only)

**Measurement**: Test with 100 albums, target < 200ms render time

### Preview Generation Performance

**Current**: Sequential preview loading with progress bar
**Per-Album**: Same, but with per-album template application
**Conclusion**: No significant change

---

## UI/UX Design Constraints

### Low Friction Requirements

1. **Minimize Clicks**: Target ≤ 2 clicks from load to rename
   - Click 1: "Apply to Selected" (auto-select albums with ALBUM detection)
   - Click 2: "Rename"

2. **Instant Feedback**: Show selection changes immediately in preview

3. **Smart Defaults**: Auto-select albums with high-confidence ALBUM detection

4. **Quick Actions**: "Select All", "Deselect All", "Invert Selection"

5. **Keyboard Support**: Space to toggle, Enter to apply

### Visual Design Principles

1. **Grouping**: Clear visual separation between albums
2. **Hierarchy**: Album name prominent, details secondary
3. **Status Indicators**: Icons for detection type (✓ ALBUM, ~ PARTIAL, ✗ SINGLES)
4. **Progressive Disclosure**: Expand/collapse album details on demand
5. **Accessibility**: ARIA labels, keyboard navigation, screen reader support

---

## Feature Flag Strategy

### Configuration

```python
# crate/core/config.py
DEFAULT_CONFIG = {
    # ...
    "enable_per_album_detection": False,  # OFF by default
}
```

```javascript
// web/static/js/app.js
class CrateApp {
    constructor() {
        this.settings = {
            enablePerAlbumDetection: false  // Synced from backend
        };
    }
}
```

### Usage Pattern

```javascript
// Check flag before showing per-album UI
if (this.settings.enablePerAlbumDetection && data.albums.length > 1) {
    this.showPerAlbumBanner(data);
} else {
    this.showSingleBanner(data);
}
```

### Rollback Plan

**Immediate Rollback**: Toggle flag OFF in settings
**Code Rollback**: Git revert specific commits
**Gradual Rollout**: Keep flag OFF for initial deployment, enable after validation

---

## Success Criteria

### Functional Requirements
- ✅ User can select which albums to apply smart template to
- ✅ Selected albums get smart template, unselected get global template
- ✅ Previews update correctly when selection changes
- ✅ Rename applies correct template per album
- ✅ Feature flag OFF → current behavior unchanged

### Performance Requirements
- ✅ Analysis time ≤ 200ms for 10 albums
- ✅ UI render time ≤ 200ms for 10 albums
- ✅ Preview generation time unchanged from current

### UX Requirements
- ✅ ≤ 2 clicks from load to rename (with smart defaults)
- ✅ Clear indication of which albums selected
- ✅ Instant visual feedback on selection changes
- ✅ Graceful degradation on errors

### Safety Requirements
- ✅ No race conditions causing incorrect renames
- ✅ State cleared properly on directory changes
- ✅ Errors logged but don't break workflow
- ✅ Rollback available via feature flag

---

## Open Questions (To Review with User)

1. **Subdirectory Depth**: Analyze only first level or recursively?
   - **Recommendation**: First level only (matches current multi-disc handling)

2. **Album Limit**: What's reasonable max for performance?
   - **Recommendation**: 100 albums (show warning if exceeded)

3. **Auto-Selection Logic**: Auto-select all ALBUM detections or none?
   - **Recommendation**: Auto-select high-confidence ALBUM, user unchecks if wrong

4. **Banner Dismissal**: Dismiss entire per-album banner or per album?
   - **Recommendation**: Entire banner (simpler, consistent with current behavior)

5. **Preview Auto-Update**: Regenerate previews on every selection change?
   - **Recommendation**: Yes, with debouncing (300ms delay) to avoid excessive calls

6. **Selection Persistence**: Remember selections if user loads same directory again?
   - **Recommendation**: No (YAGNI - keep simple, re-analyze each time)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation | Severity |
|------|-----------|--------|------------|----------|
| Race condition causes wrong template applied | Medium | High | Lock state during operations | **Critical** |
| UI performance degrades with many albums | Low | Medium | Limit to 100 albums | Moderate |
| User confusion with new UI | Medium | Low | Clear labels, smart defaults | Low |
| Breaking change to existing workflows | Low | High | Feature flag OFF by default | Moderate |
| Context detection fails for some albums | Medium | Low | Graceful degradation per album | Low |
| Preview generation becomes slow | Low | Medium | Same algorithm as current | Low |

---

## Implementation Order

### Phase 1: Backend Foundation (Task #110)
1. Add `group_files_by_subdirectory()` function
2. Modify context detection to return per-album results
3. Update `/api/preview/context` endpoint
4. Add per-album parameter to rename endpoint

### Phase 2: Frontend State Management (Task #111)
1. Add `perAlbumState` data structure
2. Parse per-album backend response
3. Implement selection change handlers
4. Clear state on directory change

### Phase 3: Frontend UI (Task #111)
1. Create per-album banner HTML/CSS
2. Render album list with checkboxes
3. Wire up selection interactions
4. Add "Select All" / "Deselect All" buttons

### Phase 4: Preview Integration (Task #111)
1. Modify preview loading to apply per-album templates
2. Update preview display logic
3. Handle preview cancellation on selection change

### Phase 5: Rename Integration (Task #111)
1. Pass per-album selections to backend
2. Backend applies correct template per album
3. Return per-album results

### Phase 6: Error Handling & Polish (Task #111)
1. Add error handling for all failure modes
2. Add console logging for debugging
3. Add loading indicators
4. Test all edge cases

### Phase 7: Feature Flag & Rollback (Task #114)
1. Add feature flag to settings
2. Implement flag checks throughout
3. Document rollback procedures

### Phase 8: Testing & Documentation (Tasks #112, #113)
1. Create comprehensive test plan
2. Execute tests
3. Document feature
4. Update lessons learned

---

## Next Steps

1. **Review this design with user** (Task #115)
   - Confirm approach
   - Resolve open questions
   - Get go/no-go decision

2. **Proceed to UI design** (Task #109)
   - Create wireframes
   - Design component specifications
   - Plan interaction patterns

3. **Begin implementation** (Tasks #110, #111)
   - Start with backend (less risky)
   - Then frontend
   - Iterate based on testing

---

**Design Status**: ✅ Complete - Ready for Review
**Next Task**: #115 (Review with user - red flags check)
