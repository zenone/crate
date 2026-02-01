# UI Design: Per-Album Smart Detection Selection

**Date**: 2026-01-31
**Feature**: Per-Album Smart Detection Selection Interface
**Status**: UI Design Phase (Task #109)

---

## Design Goals

1. **LOW FRICTION**: ≤ 2 clicks from load to rename with smart defaults
2. **CLARITY**: User immediately understands what each album will do
3. **SPEED**: Quick selection changes with instant visual feedback
4. **SAFETY**: Clear indication of what will be renamed before executing

---

## Wireframe: Per-Album Banner

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 🎵 Smart Track Detection - Multiple Albums Detected                      [×] │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  Select which albums should use smart track detection:                       │
│                                                                               │
│  [Select All]  [Deselect All]  [Invert Selection]    [Apply to Selected] ◄── Primary action│
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ ☑ Album: Greatest Hits                           12 files    [▼ Expand] │ │
│  │   📁 New_Acquisitions/Greatest_Hits/                                    │ │
│  │   ✓ ALBUM detected (high confidence)                                    │ │
│  │   Template: {track} - {title}                                           │ │
│  │   Reason: Sequential tracks 1-12 found                                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ ☐ Album: Live Recordings                          8 files    [▶ Expand] │ │
│  │   📁 New_Acquisitions/Live_Recordings/                                  │ │
│  │   ~ PARTIAL_ALBUM detected (medium confidence)                          │ │
│  │   Template: {track} - {title}                                           │ │
│  │   Reason: Tracks 1, 3, 5, 7, 9, 11, 13, 15 found (gaps detected)       │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ ☐ Album: Various Artists - Top 40                22 files    [▶ Expand] │ │
│  │   📁 New_Acquisitions/VA_Top40/                                         │ │
│  │   ✗ SINGLES detected (no track sequence)                                │ │
│  │   Template: Not recommended                                             │ │
│  │   Reason: No sequential track numbers detected                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  [... more albums ...]                                                        │
│                                                                               │
│  ℹ️ Checked albums will use smart template. Unchecked albums will use your  │
│     global template from settings.                                            │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. Banner Container

**Element**: `.smart-banner-per-album`
**State**: Shown when `perAlbumMode === true && albums.length > 1`

```html
<div class="smart-banner smart-banner-per-album" role="region" aria-label="Per-album smart detection">
    <div class="banner-header">
        <div class="banner-title">
            <span class="banner-icon">🎵</span>
            <span class="banner-text">Smart Track Detection - Multiple Albums Detected</span>
        </div>
        <button class="banner-close" aria-label="Dismiss">×</button>
    </div>

    <div class="banner-content">
        <p class="banner-description">
            Select which albums should use smart track detection:
        </p>

        <div class="banner-actions-top">
            <button class="btn-secondary btn-sm" id="select-all-albums">Select All</button>
            <button class="btn-secondary btn-sm" id="deselect-all-albums">Deselect All</button>
            <button class="btn-secondary btn-sm" id="invert-selection">Invert Selection</button>
            <button class="btn-primary" id="apply-per-album-selection">Apply to Selected</button>
        </div>

        <div class="album-list" role="list">
            <!-- Album items rendered here -->
        </div>

        <div class="banner-info">
            <span class="info-icon">ℹ️</span>
            Checked albums will use smart template. Unchecked albums will use your global template from settings.
        </div>
    </div>
</div>
```

**CSS**:
```css
.smart-banner-per-album {
    max-height: 60vh;  /* Scrollable if many albums */
    overflow-y: auto;
}

.banner-actions-top {
    display: flex;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
}

.banner-actions-top .btn-primary {
    margin-left: auto;  /* Push to right */
}
```

### 2. Album Item (Collapsed)

**Element**: `.album-item`

```html
<div class="album-item" data-album-path="New_Acquisitions/Greatest_Hits" role="listitem">
    <div class="album-item-header">
        <label class="album-checkbox-label">
            <input type="checkbox"
                   class="album-checkbox"
                   checked
                   data-album-path="New_Acquisitions/Greatest_Hits">
            <span class="album-detection-icon">✓</span>
            <span class="album-name">Album: Greatest Hits</span>
        </label>

        <div class="album-header-info">
            <span class="album-file-count">12 files</span>
            <button class="album-expand-btn" aria-label="Expand album details" aria-expanded="false">
                <span class="expand-icon">▶</span>
            </button>
        </div>
    </div>

    <!-- Details shown when expanded -->
    <div class="album-item-details hidden">
        <div class="album-path">📁 New_Acquisitions/Greatest_Hits/</div>
        <div class="album-detection">
            <span class="detection-badge detection-album">✓ ALBUM detected (high confidence)</span>
        </div>
        <div class="album-template">
            <strong>Template:</strong> <code>{track} - {title}</code>
        </div>
        <div class="album-reason">
            <strong>Reason:</strong> Sequential tracks 1-12 found
        </div>
    </div>
</div>
```

**CSS**:
```css
.album-item {
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-sm);
    background: rgba(255, 255, 255, 0.02);
    transition: all 0.2s;
}

.album-item:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: var(--accent-primary);
}

.album-item.selected {
    border-color: var(--accent-primary);
    background: rgba(99, 102, 241, 0.1);
}

.album-item-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.album-checkbox-label {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    cursor: pointer;
    flex: 1;
}

.album-checkbox {
    width: 1.25rem;
    height: 1.25rem;
    cursor: pointer;
}

.album-detection-icon {
    font-size: 1.25rem;
    width: 1.5rem;
}

.album-name {
    font-weight: 600;
    color: var(--text-primary);
}

.album-header-info {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
}

.album-file-count {
    color: var(--text-secondary);
    font-size: 0.875rem;
}

.album-expand-btn {
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 0.25rem;
    transition: all 0.2s;
}

.album-expand-btn:hover {
    color: var(--accent-primary);
}

.album-expand-btn[aria-expanded="true"] .expand-icon {
    transform: rotate(90deg);
}

.album-item-details {
    margin-top: var(--spacing-md);
    padding-top: var(--spacing-md);
    border-top: 1px solid var(--border);
}

.album-item-details.hidden {
    display: none;
}

.album-path {
    color: var(--text-secondary);
    font-family: var(--font-mono);
    font-size: 0.875rem;
    margin-bottom: var(--spacing-sm);
}

.album-detection {
    margin-bottom: var(--spacing-sm);
}

.detection-badge {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    border-radius: var(--radius-sm);
    font-size: 0.875rem;
    font-weight: 500;
}

.detection-album {
    background: rgba(16, 185, 129, 0.2);
    color: var(--success);
}

.detection-partial {
    background: rgba(245, 158, 11, 0.2);
    color: var(--warning);
}

.detection-singles {
    background: rgba(239, 68, 68, 0.2);
    color: var(--error);
}

.album-template {
    margin-bottom: var(--spacing-sm);
    font-size: 0.875rem;
}

.album-template code {
    background: rgba(255, 255, 255, 0.1);
    padding: 0.125rem 0.375rem;
    border-radius: var(--radius-sm);
    font-family: var(--font-mono);
}

.album-reason {
    font-size: 0.875rem;
    color: var(--text-secondary);
}
```

### 3. Detection Type Icons

| Detection Type | Icon | Color | Meaning |
|---------------|------|-------|---------|
| ALBUM | ✓ | Green | High confidence, recommend template |
| PARTIAL_ALBUM | ~ | Yellow | Medium confidence, proceed with caution |
| INCOMPLETE_ALBUM | ⚠ | Orange | Gaps detected, may have issues |
| SINGLES | ✗ | Red | Not recommended for smart template |
| UNKNOWN | ? | Gray | Detection failed or unavailable |

**Icon Component**:
```javascript
function getDetectionIcon(detectionType) {
    const icons = {
        'ALBUM': '✓',
        'PARTIAL_ALBUM': '~',
        'INCOMPLETE_ALBUM': '⚠',
        'SINGLES': '✗',
        'UNKNOWN': '?'
    };
    return icons[detectionType] || '?';
}
```

### 4. Smart Defaults

**Auto-Selection Logic**:
```javascript
function getDefaultSelection(detection) {
    // Auto-select only high-confidence ALBUM detections
    if (detection.type === 'ALBUM' && detection.confidence === 'high') {
        return true;
    }
    return false;
}
```

**Rationale**:
- ALBUM + high confidence → likely correct, save user time
- PARTIAL_ALBUM → user should decide (unchecked by default)
- SINGLES → definitely wrong, unchecked
- User can easily change with one click

---

## Interaction Patterns

### 1. Loading & Initialization

**Sequence**:
```
1. User loads directory
2. System loads files
3. Show loading indicator: "Analyzing albums..."
4. Context detection completes
5. Banner slides down (animation)
6. Albums rendered with smart defaults (auto-checked)
7. Focus on "Apply to Selected" button (keyboard accessibility)
```

**Animation**:
```css
@keyframes slideDown {
    from {
        opacity: 0;
        transform: translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.smart-banner-per-album {
    animation: slideDown 0.3s ease-out;
}
```

### 2. Album Selection Toggle

**User Action**: Click checkbox or album name
**System Response**:
1. Toggle checkbox state
2. Update `perAlbumSelections` state
3. Update album item styling (add/remove `.selected`)
4. Update button state (enable "Apply to Selected" if any checked)
5. **No preview regeneration yet** (wait for Apply)

**Code**:
```javascript
onAlbumCheckboxChange(albumPath, checked) {
    // Update state
    this.perAlbumState.albums.find(a => a.path === albumPath).selected = checked;

    // Update UI
    const albumItem = document.querySelector(`[data-album-path="${albumPath}"]`);
    albumItem.classList.toggle('selected', checked);

    // Update button state
    this.updateApplyButtonState();
}

updateApplyButtonState() {
    const anySelected = this.perAlbumState.albums.some(a => a.selected);
    const applyBtn = document.getElementById('apply-per-album-selection');
    applyBtn.disabled = !anySelected;
}
```

### 3. Expand/Collapse Album Details

**User Action**: Click expand button or double-click album header
**System Response**:
1. Toggle `hidden` class on `.album-item-details`
2. Rotate expand icon (CSS transform)
3. Update `aria-expanded` attribute
4. Smooth height transition

**Code**:
```javascript
toggleAlbumExpanded(albumPath) {
    const albumItem = document.querySelector(`[data-album-path="${albumPath}"]`);
    const details = albumItem.querySelector('.album-item-details');
    const expandBtn = albumItem.querySelector('.album-expand-btn');

    const isExpanded = expandBtn.getAttribute('aria-expanded') === 'true';

    details.classList.toggle('hidden', isExpanded);
    expandBtn.setAttribute('aria-expanded', !isExpanded);
}
```

### 4. Quick Actions

**Select All**:
```javascript
onSelectAll() {
    this.perAlbumState.albums.forEach(album => {
        album.selected = true;
        this.updateAlbumUI(album.path, true);
    });
    this.updateApplyButtonState();
}
```

**Deselect All**:
```javascript
onDeselectAll() {
    this.perAlbumState.albums.forEach(album => {
        album.selected = false;
        this.updateAlbumUI(album.path, false);
    });
    this.updateApplyButtonState();
}
```

**Invert Selection**:
```javascript
onInvertSelection() {
    this.perAlbumState.albums.forEach(album => {
        album.selected = !album.selected;
        this.updateAlbumUI(album.path, album.selected);
    });
    this.updateApplyButtonState();
}
```

### 5. Apply to Selected

**User Action**: Click "Apply to Selected" button
**System Response**:
1. Disable selection UI (prevent changes during preview loading)
2. Show loading indicator on button ("Applying...")
3. Generate previews with per-album templates
4. Update preview column in file table
5. Scroll to file table
6. Re-enable selection UI
7. Hide banner (optional - TBD)

**Code**:
```javascript
async onApplyPerAlbumSelection() {
    try {
        // Disable UI
        this.lockPerAlbumState();
        this.showButtonLoading('apply-per-album-selection', 'Applying...');

        // Generate previews
        await this.loadAllPreviewsWithPerAlbumTemplates();

        // Scroll to file table
        document.querySelector('.file-table').scrollIntoView({ behavior: 'smooth' });

        // Success feedback
        this.showToast('Previews updated with per-album templates', 'success');

    } catch (error) {
        console.error('Apply failed:', error);
        this.showToast('Failed to apply templates. Please try again.', 'error');
    } finally {
        // Re-enable UI
        this.unlockPerAlbumState();
        this.hideButtonLoading('apply-per-album-selection', 'Apply to Selected');
    }
}
```

### 6. Keyboard Shortcuts

| Key | Action | Context |
|-----|--------|---------|
| **Space** | Toggle album selection | When focused on checkbox |
| **Enter** | Apply to selected | When focused on Apply button |
| **Tab** | Navigate albums | Standard focus management |
| **↑/↓** | Navigate album list | When focused on album items |
| **Escape** | Dismiss banner | When banner focused |

**Implementation**:
```javascript
onKeyDown(event) {
    if (event.target.classList.contains('album-checkbox')) {
        if (event.key === ' ') {
            event.preventDefault();
            event.target.click();
        }
    }

    if (event.key === 'Escape' && this.perAlbumBannerVisible) {
        this.dismissPerAlbumBanner();
    }
}
```

---

## Responsive Design

### Desktop (> 768px)

- Banner max-height: 60vh (scrollable)
- Albums displayed in grid (2 columns if many albums)
- Full details visible when expanded
- All quick action buttons visible

### Tablet (768px - 1024px)

- Banner max-height: 50vh
- Single column album list
- Compact album items (smaller padding)
- Quick actions in single row

### Mobile (< 768px)

- Banner max-height: 40vh
- Single column
- Minimize album item padding
- Quick actions stack vertically
- "Invert Selection" hidden (space constraint)
- Expand/collapse albums by default (show only selected)

**Media Queries**:
```css
@media (max-width: 768px) {
    .smart-banner-per-album {
        max-height: 40vh;
    }

    .banner-actions-top {
        flex-direction: column;
    }

    .banner-actions-top .btn-primary {
        margin-left: 0;
        order: -1;  /* Move to top */
    }

    #invert-selection {
        display: none;
    }

    .album-item {
        padding: var(--spacing-sm);
    }
}
```

---

## Accessibility Features

### ARIA Attributes

```html
<!-- Banner -->
<div role="region" aria-label="Per-album smart detection">

<!-- Album list -->
<div role="list" aria-label="Album selection list">

<!-- Album item -->
<div role="listitem">

<!-- Checkbox -->
<input type="checkbox"
       aria-label="Select Greatest Hits for smart template"
       aria-describedby="album-detection-greatest-hits">

<!-- Detection info -->
<div id="album-detection-greatest-hits" class="album-detection">
    ALBUM detected (high confidence)
</div>

<!-- Expand button -->
<button aria-label="Expand album details"
        aria-expanded="false"
        aria-controls="album-details-greatest-hits">
```

### Screen Reader Support

**Announcements**:
```javascript
// When album selected
announceToScreenReader(`${albumName} selected for smart template`);

// When Apply clicked
announceToScreenReader(`Applying templates to ${selectedCount} albums`);

// When complete
announceToScreenReader(`Previews updated for ${selectedCount} albums`);
```

**Helper Function**:
```javascript
function announceToScreenReader(message) {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    document.body.appendChild(announcement);
    setTimeout(() => announcement.remove(), 1000);
}
```

### Focus Management

```javascript
// When banner opens
function showPerAlbumBanner() {
    // ... render banner

    // Focus first interactive element
    setTimeout(() => {
        document.getElementById('select-all-albums').focus();
    }, 300);  // After animation
}

// When banner closes
function dismissPerAlbumBanner() {
    // Return focus to directory input
    document.getElementById('directory-input').focus();
}
```

---

## Visual States

### Album Item States

1. **Default** (unchecked, not hovered):
   - Border: `var(--border)`
   - Background: `rgba(255, 255, 255, 0.02)`

2. **Hover**:
   - Border: `var(--accent-primary)`
   - Background: `rgba(255, 255, 255, 0.05)`
   - Cursor: pointer

3. **Selected** (checked):
   - Border: `var(--accent-primary)`
   - Background: `rgba(99, 102, 241, 0.1)`
   - Checkbox: checked

4. **Disabled** (during operation):
   - Opacity: 0.5
   - Cursor: not-allowed
   - Pointer-events: none

5. **Error**:
   - Border: `var(--error)`
   - Background: `rgba(239, 68, 68, 0.1)`
   - Show error message in details

### Button States

**Primary Action ("Apply to Selected")**:
- Default: Enabled, accent color
- Disabled: Grayed out (no albums selected)
- Loading: Spinner + "Applying..." text
- Success: Briefly show checkmark (1s)

**Secondary Actions ("Select All", etc)**:
- Default: Secondary button style
- Hover: Slight highlight
- Active: Pressed effect

---

## Performance Optimizations

### Virtual Scrolling (if > 50 albums)

```javascript
// Only render visible albums + buffer
function renderVisibleAlbums(scrollTop, containerHeight) {
    const itemHeight = 80;  // Approximate height per album
    const buffer = 5;  // Extra items above/below viewport

    const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - buffer);
    const endIndex = Math.min(
        albums.length,
        Math.ceil((scrollTop + containerHeight) / itemHeight) + buffer
    );

    return albums.slice(startIndex, endIndex);
}
```

### Debounced Selection Changes

```javascript
// Debounce preview regeneration if user rapidly toggles
const debouncedPreviewRegeneration = debounce(() => {
    this.loadAllPreviewsWithPerAlbumTemplates();
}, 300);
```

### Lazy Loading Album Details

```javascript
// Load album file lists only when expanded
async function onAlbumExpand(albumPath) {
    const album = this.perAlbumState.albums.find(a => a.path === albumPath);

    if (!album.filesLoaded) {
        // Fetch detailed file list
        album.files = await this.fetchAlbumFiles(albumPath);
        album.filesLoaded = true;
    }

    this.renderAlbumDetails(album);
}
```

---

## Error States

### 1. Detection Failed for Album

**UI**:
```html
<div class="album-item album-item-error">
    <div class="album-item-header">
        <label class="album-checkbox-label">
            <input type="checkbox" disabled>
            <span class="album-detection-icon">⚠</span>
            <span class="album-name">Album: Unknown</span>
        </label>
        <span class="album-error-badge">Detection failed</span>
    </div>
</div>
```

**Behavior**:
- Checkbox disabled
- Show error badge
- Expand to show error details
- Allow user to proceed with other albums

### 2. No Albums Detected

**UI**: Fall back to single-banner mode (current behavior)

### 3. All Albums are SINGLES

**UI**:
```
┌──────────────────────────────────────────────────────────────┐
│ 🎵 Smart Track Detection - No Albums Detected          [×] │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ℹ️ No albums with sequential track numbers were detected.  │
│     Smart track detection is not recommended for these files.│
│                                                               │
│  [Dismiss]                                                    │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Testing Checklist

### Visual Tests
- [ ] Banner renders correctly with 1, 3, 10, 100 albums
- [ ] Album items display all information clearly
- [ ] Detection icons render correctly for each type
- [ ] Checkboxes are properly aligned
- [ ] Expand/collapse animation smooth
- [ ] Responsive design works on mobile/tablet/desktop
- [ ] Dark mode styling consistent with app

### Interaction Tests
- [ ] Clicking checkbox toggles selection
- [ ] Clicking album name toggles selection
- [ ] Expand button toggles details
- [ ] "Select All" selects all albums
- [ ] "Deselect All" deselects all albums
- [ ] "Invert Selection" inverts selections
- [ ] "Apply to Selected" generates previews
- [ ] Keyboard navigation works (Tab, Space, Enter)
- [ ] Banner dismisses on X click

### State Tests
- [ ] Smart defaults applied correctly (ALBUM = checked)
- [ ] Selection state persists during expand/collapse
- [ ] State cleared when loading new directory
- [ ] State locked during preview generation
- [ ] State unlocked after preview completes

### Accessibility Tests
- [ ] Screen reader announces changes
- [ ] ARIA attributes correct
- [ ] Focus management proper
- [ ] Keyboard shortcuts work
- [ ] Color contrast meets WCAG AA

### Error Tests
- [ ] Detection failure shows error state
- [ ] Error doesn't break other albums
- [ ] Graceful degradation to single-banner
- [ ] Error messages clear and actionable

---

## Implementation Notes

### Component Structure

```
PerAlbumBanner (parent component)
├── BannerHeader
│   ├── Title
│   └── CloseButton
├── BannerContent
│   ├── Description
│   ├── QuickActions
│   │   ├── SelectAllButton
│   │   ├── DeselectAllButton
│   │   ├── InvertButton
│   │   └── ApplyButton (primary)
│   ├── AlbumList (scrollable)
│   │   └── AlbumItem[] (repeated)
│   │       ├── AlbumHeader
│   │       │   ├── Checkbox
│   │       │   ├── DetectionIcon
│   │       │   ├── AlbumName
│   │       │   ├── FileCount
│   │       │   └── ExpandButton
│   │       └── AlbumDetails (expandable)
│   │           ├── Path
│   │           ├── DetectionBadge
│   │           ├── Template
│   │           └── Reason
│   └── InfoFooter
```

### Data Flow

```
1. Backend: context_detection.py
   └─> Returns per-album detection results

2. Frontend: app.checkSmartDetectionForDirectory()
   └─> Receives per-album data
   └─> Stores in this.perAlbumState

3. Frontend: app.showPerAlbumBanner()
   └─> Renders album list with smart defaults

4. User: Toggles album selections
   └─> Updates this.perAlbumState.albums[i].selected

5. User: Clicks "Apply to Selected"
   └─> app.loadAllPreviewsWithPerAlbumTemplates()
   └─> Iterates albums, applies correct template per album

6. User: Clicks "Rename"
   └─> app.executeRename(perAlbumSelections)
   └─> Backend applies templates per album
```

---

## Design Status

**Status**: ✅ Complete - Ready for Implementation
**Next Task**: #115 (Review design with user - red flags check)
