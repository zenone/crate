# UX Improvements: Proposed Changes for Crate

**Date**: 2026-01-30
**Status**: Proposed (Awaiting User Approval)
**Priority**: Based on Impact vs. Effort analysis
**Reference**: UX Audit (ux-audit-current-state.md), UX Research (ux-research-2025-2026.md)

---

## Executive Summary

This document proposes **10 specific, actionable improvements** to bring Crate's UX to 2025-2026 standards. Improvements are prioritized by impact and implementation complexity.

**Expected Outcomes:**
- ✅ 50% reduction in time to rename files
- ✅ 50% reduction in clicks required
- ✅ User anxiety reduced (undo pattern)
- ✅ Power user efficiency increased (keyboard shortcuts)
- ✅ Accessibility score: 5/10 → 8/10

**Total Estimated Effort**: ~20 hours (2-3 days of focused work)

---

## Improvement #1: Undo Pattern for Rename Operations

**Priority**: **CRITICAL**
**Impact**: HIGH - Reduces user anxiety, enables mistake recovery
**Effort**: LOW - ~2 hours
**Risk**: LOW - Additive change, no breaking changes

### Current Behavior (Problem)

```
User renames files → Success toast appears → No way to undo
```

**Issue**: Files are permanently renamed. If user made a mistake (wrong template, wrong selection), they must:
1. Remember original filenames
2. Manually rename back
3. OR reload backup (if they made one)

**User Impact**: High anxiety, careful double-checking, slow workflow

### Proposed Behavior (Solution)

```
User renames files → Success toast appears with [Undo] button →
Click [Undo] → Files revert to original names
```

**Toast Design:**
```
┌─────────────────────────────────────────┐
│ ✅ 45 files renamed successfully        │
│                                         │
│ [Undo] ← Clickable button              │
│                                         │
│ This action can be undone for 30s      │
└─────────────────────────────────────────┘
```

**Auto-dismiss**: Toast stays for 30 seconds, then fades out

### Technical Implementation

**Backend (web/main.py):**
```python
# Store rename history for undo
rename_history = {}  # session_id -> list of (src, dst) tuples

@app.post("/api/rename/execute")
async def execute_rename(request: ExecuteRenameRequest):
    # Existing rename logic...

    # NEW: Store rename history
    session_id = str(uuid.uuid4())
    rename_history[session_id] = [(old, new) for old, new in renamed_pairs]

    return {
        "success": True,
        "renamed_count": len(renamed_pairs),
        "session_id": session_id  # Return session ID for undo
    }

@app.post("/api/rename/undo")
async def undo_rename(session_id: str):
    if session_id not in rename_history:
        raise HTTPException(404, "Undo session expired or not found")

    # Revert renames
    pairs = rename_history[session_id]
    for new_name, old_name in pairs:  # Reverse direction
        os.rename(new_name, old_name)

    # Clean up history
    del rename_history[session_id]

    return {"success": True, "reverted_count": len(pairs)}
```

**Frontend (web/static/js/app.js):**
```javascript
async executeRenameNow() {
    // Execute rename...
    const result = await this.api.executeRename(...);

    // Show success toast with undo button
    this.ui.showUndoToast(
        `${result.renamed_count} files renamed successfully`,
        () => this.undoRename(result.session_id)
    );
}

async undoRename(sessionId) {
    try {
        await this.api.undoRename(sessionId);
        this.ui.success('Rename undone successfully');
        this.loadDirectory();  // Refresh file list
    } catch (error) {
        this.ui.error(`Failed to undo: ${error.message}`);
    }
}
```

**Frontend (web/static/js/ui.js):**
```javascript
showUndoToast(message, undoCallback) {
    const toast = document.createElement('div');
    toast.className = 'toast success';
    toast.innerHTML = `
        <div class="toast-message">${message}</div>
        <button class="toast-undo-btn">Undo</button>
        <div class="toast-timer">This action can be undone for 30s</div>
    `;

    const undoBtn = toast.querySelector('.toast-undo-btn');
    undoBtn.onclick = () => {
        undoCallback();
        toast.remove();
        clearTimeout(autoHideTimer);
    };

    document.getElementById('toast-container').appendChild(toast);

    // Auto-hide after 30 seconds
    const autoHideTimer = setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 30000);
}
```

### CSS Updates

```css
/* styles.css - Add undo button styles */
.toast-undo-btn {
    margin-top: var(--spacing-sm);
    padding: 0.5rem 1rem;
    background: var(--accent-primary);
    color: white;
    border: none;
    border-radius: var(--radius-sm);
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
}

.toast-undo-btn:hover {
    background: var(--accent-hover);
    transform: translateY(-1px);
}

.toast-timer {
    margin-top: var(--spacing-xs);
    font-size: 0.75rem;
    color: var(--text-muted);
    font-style: italic;
}

.toast.fade-out {
    animation: fadeOut 0.3s ease-out forwards;
}

@keyframes fadeOut {
    to {
        opacity: 0;
        transform: translateX(100%);
    }
}
```

### Testing Plan

**Manual Tests:**
1. Rename 5 files → Click Undo → Verify files reverted
2. Rename 100 files → Wait 31 seconds → Verify undo not available
3. Rename files → Click Undo → Rename again → Verify works
4. Rename files → Refresh page → Verify old session ID expired

**Edge Cases:**
- File already exists at original name (collision)
- User doesn't have write permissions
- Files deleted by external program before undo

### Before/After Comparison

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| User anxiety | High | Low | ✅ Reduced |
| Mistake recovery | Manual | One click | ✅ 95% faster |
| Time to fix error | 5+ minutes | 2 seconds | ✅ 99% faster |
| User confidence | Low | High | ✅ Increased |

---

## Improvement #2: Keyboard Shortcuts for Power Users

**Priority**: **HIGH**
**Impact**: HIGH - 30-50% faster workflow for power users
**Effort**: MEDIUM - ~3 hours
**Risk**: LOW - Additive change

### Current Behavior (Problem)

Only `Escape` key works (closes modals). No other keyboard shortcuts.

**User Impact**: Power users forced to use mouse for everything, slow workflow

### Proposed Shortcuts

| Shortcut | Action | Context |
|----------|--------|---------|
| `Ctrl+A` / `Cmd+A` | Select all files | File list view |
| `Ctrl+D` / `Cmd+D` | Deselect all files | File list view |
| `Escape` | Close modal | Any modal (already works) |
| `Enter` | Confirm action | Modals (new) |
| `Ctrl+P` / `Cmd+P` | Preview rename | Files selected |
| `Ctrl+R` / `Cmd+R` | Execute rename | After preview |
| `Ctrl+Z` / `Cmd+Z` | Undo rename | After rename (with #1) |
| `?` | Show shortcuts help | Anywhere |
| `Ctrl+/` | Focus template input | Anywhere |

### Implementation

**JavaScript (app.js):**
```javascript
setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ignore if user is typing in input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            // Exception: Allow Escape in inputs
            if (e.key === 'Escape') {
                e.target.blur();
            }
            return;
        }

        const ctrl = e.ctrlKey || e.metaKey;

        // Ctrl+A: Select all
        if (ctrl && e.key === 'a') {
            e.preventDefault();
            this.selectAllFiles();
        }

        // Ctrl+D: Deselect all
        if (ctrl && e.key === 'd') {
            e.preventDefault();
            this.deselectAllFiles();
        }

        // Ctrl+P: Preview
        if (ctrl && e.key === 'p') {
            e.preventDefault();
            if (!document.getElementById('preview-btn').disabled) {
                this.showPreview();
            }
        }

        // Ctrl+Z: Undo
        if (ctrl && e.key === 'z') {
            e.preventDefault();
            if (this.lastRenameSessionId) {
                this.undoRename(this.lastRenameSessionId);
            }
        }

        // ?: Show shortcuts help
        if (e.key === '?') {
            e.preventDefault();
            this.showKeyboardShortcutsHelp();
        }

        // Ctrl+/: Focus template input
        if (ctrl && e.key === '/') {
            e.preventDefault();
            document.getElementById('template-input').focus();
        }
    });
}
```

**Keyboard Shortcuts Help Modal:**
```html
<div id="shortcuts-modal" class="modal hidden">
    <div class="modal-overlay"></div>
    <div class="modal-content">
        <div class="modal-header">
            <h2>⌨️ Keyboard Shortcuts</h2>
            <button class="modal-close">×</button>
        </div>
        <div class="modal-body">
            <table class="shortcuts-table">
                <tr>
                    <td><kbd>Ctrl</kbd> + <kbd>A</kbd></td>
                    <td>Select all files</td>
                </tr>
                <tr>
                    <td><kbd>Ctrl</kbd> + <kbd>D</kbd></td>
                    <td>Deselect all files</td>
                </tr>
                <tr>
                    <td><kbd>Ctrl</kbd> + <kbd>P</kbd></td>
                    <td>Preview rename</td>
                </tr>
                <tr>
                    <td><kbd>Ctrl</kbd> + <kbd>R</kbd></td>
                    <td>Execute rename</td>
                </tr>
                <tr>
                    <td><kbd>Ctrl</kbd> + <kbd>Z</kbd></td>
                    <td>Undo last rename</td>
                </tr>
                <tr>
                    <td><kbd>Escape</kbd></td>
                    <td>Close modal</td>
                </tr>
                <tr>
                    <td><kbd>?</kbd></td>
                    <td>Show this help</td>
                </tr>
            </table>
        </div>
    </div>
</div>
```

**CSS for Kbd Elements:**
```css
kbd {
    display: inline-block;
    padding: 0.2rem 0.5rem;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 0.875rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```

### Visual Indicators

**Add shortcut hints to button tooltips:**
```javascript
// Update button titles to include shortcuts
document.getElementById('preview-btn').title = 'Preview rename (Ctrl+P)';
document.getElementById('rename-now-btn').title = 'Execute rename (Ctrl+R)';
```

### Before/After Comparison

| Task | Before | After | Time Saved |
|------|--------|-------|------------|
| Select all 100 files | Click checkbox | Ctrl+A | 2s → 0.1s |
| Show preview | Move mouse, click | Ctrl+P | 1s → 0.1s |
| Close modal | Move mouse, click X | Escape | 1s → 0.1s |
| Undo rename | N/A | Ctrl+Z | Impossible → 0.1s |
| **Total for rename workflow** | **~15s** | **~5s** | **⬇️ 66% faster** |

---

## Improvement #3: Progress Indicators & Skeleton Screens

**Priority**: **HIGH**
**Impact**: MEDIUM - Improves perceived performance
**Effort**: MEDIUM - ~2-3 hours
**Risk**: LOW - Visual-only changes

### Current Behavior (Problem)

When loading metadata:
- Shows full-screen spinner with "Processing..."
- No progress percentage
- No indication of what's happening
- **Feels slow/frozen**

### Proposed Behavior (Solution)

**Skeleton Screens During Load:**
```
┌─────────────────────────────────────────────┐
│ ▓▓▓▓▓░░░░░░░░░░░░░  Loading...  (23%)     │
│                                             │
│ □  ████████  ████████████  ███  ██████     │  ← Skeleton row
│ □  ████████  ████████████  ███  ██████     │
│ □  ████████  ████████████  ███  ██████     │
│                                             │
│ Loading metadata: 23/100 files...          │
│ Estimated time remaining: 12 seconds       │
└─────────────────────────────────────────────┘
```

**Progress Text:**
- "Loading metadata: 23/100 files (23%)"
- "Estimated time remaining: 12 seconds"
- "Processing: Artist - Song Title.mp3"

### Implementation

**HTML (Skeleton Rows):**
```html
<div id="file-list-skeleton" class="hidden">
    <div class="skeleton-row">
        <div class="skeleton-checkbox"></div>
        <div class="skeleton-text skeleton-filename"></div>
        <div class="skeleton-text skeleton-artist"></div>
        <div class="skeleton-text skeleton-title"></div>
        <div class="skeleton-text skeleton-bpm"></div>
    </div>
    <!-- Repeat 10 times -->
</div>
```

**CSS:**
```css
.skeleton-row {
    display: grid;
    grid-template-columns: 3rem 1fr 1fr 1fr 80px;
    gap: 1rem;
    padding: 1rem;
    border-bottom: 1px solid var(--border);
}

.skeleton-text {
    height: 1rem;
    background: linear-gradient(
        90deg,
        rgba(255,255,255,0.05) 25%,
        rgba(255,255,255,0.1) 50%,
        rgba(255,255,255,0.05) 75%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: var(--radius-sm);
}

@keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

.skeleton-filename { width: 80%; }
.skeleton-artist { width: 60%; }
.skeleton-title { width: 70%; }
.skeleton-bpm { width: 50%; }
```

**JavaScript (Progress Updates):**
```javascript
async loadAllMetadata() {
    const total = this.currentFiles.length;
    this.metadataLoadState.total = total;
    this.metadataLoadState.loaded = 0;
    this.metadataLoadState.startTime = Date.now();

    // Show skeleton
    this.ui.show('file-list-skeleton');
    this.ui.show('metadata-progress-banner');

    for (let i = 0; i < total; i++) {
        const file = this.currentFiles[i];

        // Load metadata...
        await this.loadFileMetadata(file);

        // Update progress
        this.metadataLoadState.loaded = i + 1;
        const percentage = Math.round((i + 1) / total * 100);

        // Calculate ETA
        const elapsed = Date.now() - this.metadataLoadState.startTime;
        const avgTimePerFile = elapsed / (i + 1);
        const remaining = (total - (i + 1)) * avgTimePerFile;
        const etaSeconds = Math.round(remaining / 1000);

        // Update UI
        document.getElementById('progress-text').textContent =
            `Loading metadata: ${i + 1}/${total} (${percentage}%)`;
        document.getElementById('progress-eta').textContent =
            `Estimated time remaining: ${etaSeconds}s`;
        document.getElementById('progress-current-file').textContent =
            `Processing: ${file.name}`;

        // Update progress bar
        document.getElementById('progress-bar-fill').style.width = `${percentage}%`;
    }

    // Hide skeleton, show real table
    this.ui.hide('file-list-skeleton');
    this.ui.hide('metadata-progress-banner');
    this.renderFileList();
}
```

### Before/After Comparison

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Perceived speed | Slow (spinner) | Fast (skeleton) | ✅ 2x faster feeling |
| User awareness | "Is it frozen?" | "23/100 done" | ✅ Clear feedback |
| Anxiety | High | Low | ✅ Reduced |
| Abandonment rate | Higher | Lower | ✅ Users wait longer |

---

## Improvement #4: Empty States with Clear CTAs

**Priority**: **HIGH**
**Impact**: MEDIUM - Helps new users
**Effort**: LOW - ~1 hour
**Risk**: NONE - Additive UI

### Current Behavior (Problem)

When no directory loaded: Shows empty file list (just blank space)

**User Impact**: New users confused - "What do I do now?"

### Proposed Empty State

```
┌─────────────────────────────────────────────┐
│                                             │
│              📁                             │
│                                             │
│      No directory selected yet              │
│                                             │
│   Click "Browse Files" to get started or   │
│   paste a directory path in the box above  │
│                                             │
│         [Browse Files]  [Use Examples]     │
│                                             │
└─────────────────────────────────────────────┘
```

### Implementation

**HTML:**
```html
<div id="file-list-empty" class="empty-state hidden">
    <div class="empty-icon">📁</div>
    <h3 class="empty-title">No directory selected yet</h3>
    <p class="empty-description">
        Click "Browse Files" to get started or paste a directory path in the box above
    </p>
    <div class="empty-actions">
        <button class="btn btn-primary" id="empty-browse-btn">
            📂 Browse Files
        </button>
        <button class="btn btn-secondary" id="empty-examples-btn">
            💡 Use Examples
        </button>
    </div>
</div>
```

**CSS:**
```css
.empty-state {
    text-align: center;
    padding: var(--spacing-xl) var(--spacing-md);
    color: var(--text-secondary);
}

.empty-icon {
    font-size: 4rem;
    margin-bottom: var(--spacing-md);
    opacity: 0.5;
}

.empty-title {
    font-size: 1.5rem;
    margin-bottom: var(--spacing-sm);
    color: var(--text-primary);
}

.empty-description {
    font-size: 1rem;
    margin-bottom: var(--spacing-lg);
    max-width: 500px;
    margin-left: auto;
    margin-right: auto;
}

.empty-actions {
    display: flex;
    gap: var(--spacing-sm);
    justify-content: center;
}
```

### Multiple Empty States

**1. No Directory Loaded** (above)

**2. Directory Loaded, No Files:**
```
┌─────────────────────────────────────────────┐
│              🎵                             │
│                                             │
│     No MP3 files found in this directory    │
│                                             │
│   Try selecting a different folder or      │
│   enable "Include subfolders"               │
│                                             │
│         [Choose Different Folder]          │
└─────────────────────────────────────────────┘
```

**3. Preview Modal, No Changes:**
```
┌─────────────────────────────────────────────┐
│              ℹ️                              │
│                                             │
│          All files will keep their          │
│              current names                  │
│                                             │
│   The template produced the same results.  │
│   Try adjusting your template.              │
│                                             │
│              [Close]                        │
└─────────────────────────────────────────────┘
```

---

## Improvement #5: Real-Time Template Validation

**Priority**: **HIGH**
**Impact**: MEDIUM - Prevents errors before they happen
**Effort**: MEDIUM - ~2 hours
**Risk**: LOW - Frontend validation only

### Current Behavior (Problem)

User types template → No feedback until preview → Errors shown in modal

**Issues:**
- User doesn't know if syntax is valid
- No live preview of what filename will look like
- Errors discovered late in process

### Proposed Behavior (Solution)

**Live Validation as User Types:**
```
┌─────────────────────────────────────────────┐
│ Template:                                   │
│ ┌─────────────────────────────────────────┐ │
│ │ {artist} - {title} [{bpm} {key}]        │ │ ✅ Valid
│ └─────────────────────────────────────────┘ │
│                                             │
│ Preview:                                    │
│ John Doe - Song Name [128 Am]              │ ← Live preview
│                                             │
│ Available tokens: {artist}, {title}, ...   │
└─────────────────────────────────────────────┘
```

**If Invalid Syntax:**
```
┌─────────────────────────────────────────────┐
│ Template:                                   │
│ ┌─────────────────────────────────────────┐ │
│ │ {artist} - {title} [{bpm {key}]         │ │ ❌ Error
│ └─────────────────────────────────────────┘ │
│     ⚠️ Unclosed bracket at position 28     │ ← Error message
│                                             │
│ Preview:                                    │
│ (Cannot preview - invalid template)        │
└─────────────────────────────────────────────┘
```

### Implementation

**JavaScript:**
```javascript
setupTemplateValidation() {
    const templateInput = document.getElementById('template-input');
    const previewDiv = document.getElementById('template-preview');
    const errorDiv = document.getElementById('template-error');

    templateInput.addEventListener('input', (e) => {
        const template = e.target.value;
        this.validateAndPreviewTemplate(template);
    });
}

validateAndPreviewTemplate(template) {
    // Validate syntax
    const validation = this.validateTemplateSyntax(template);

    if (!validation.valid) {
        // Show error
        templateInput.classList.add('input-error');
        errorDiv.textContent = validation.error;
        errorDiv.classList.remove('hidden');
        previewDiv.textContent = '(Cannot preview - invalid template)';
        return;
    }

    // Clear errors
    templateInput.classList.remove('input-error');
    errorDiv.classList.add('hidden');

    // Generate preview with example data
    const exampleMetadata = {
        artist: 'John Doe',
        title: 'Song Name',
        bpm: '128',
        key: 'Am',
        // ... other fields
    };

    const preview = this.applyTemplate(template, exampleMetadata);
    previewDiv.textContent = preview + '.mp3';
}

validateTemplateSyntax(template) {
    // Check for unclosed brackets
    let openBrackets = 0;
    for (let i = 0; i < template.length; i++) {
        if (template[i] === '{') openBrackets++;
        if (template[i] === '}') openBrackets--;

        if (openBrackets < 0) {
            return {
                valid: false,
                error: `Unexpected closing bracket at position ${i}`
            };
        }
    }

    if (openBrackets > 0) {
        return {
            valid: false,
            error: `Unclosed bracket (${openBrackets} opening brackets not closed)`
        };
    }

    // Check for unknown tokens
    const validTokens = ['artist', 'title', 'bpm', 'key', 'mix', 'year', 'album', 'track'];
    const tokenRegex = /{(\w+)}/g;
    let match;

    while ((match = tokenRegex.exec(template)) !== null) {
        const token = match[1];
        if (!validTokens.includes(token)) {
            return {
                valid: false,
                error: `Unknown token: {${token}}`
            };
        }
    }

    return { valid: true };
}
```

### CSS:**
```css
.input-error {
    border-color: var(--error) !important;
    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.2);
}

#template-error {
    margin-top: var(--spacing-xs);
    padding: var(--spacing-sm);
    background: rgba(239, 68, 68, 0.1);
    border-left: 3px solid var(--error);
    border-radius: var(--radius-sm);
    font-size: 0.875rem;
    color: var(--error);
}

#template-preview {
    margin-top: var(--spacing-sm);
    padding: var(--spacing-sm);
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid var(--success);
    border-radius: var(--radius-sm);
    font-family: var(--font-mono);
    font-size: 0.95rem;
    color: var(--success);
}

#template-preview:empty::before {
    content: "Preview will appear here...";
    color: var(--text-muted);
    font-style: italic;
}
```

---

## Improvements #6-10: Additional Enhancements

### #6: ARIA Labels for Accessibility

**Priority**: MEDIUM | **Effort**: 2 hours

- Add `aria-label` to all icon buttons
- Add `aria-live="polite"` to toast container
- Add `role="progressbar"` to progress indicators
- Add `aria-describedby` to form inputs

### #7: Hover Tooltips for Truncated Text

**Priority**: MEDIUM | **Effort**: 1 hour

- Show full filename on hover
- Use native browser `title` attribute or custom tooltip
- Works for long filenames that overflow

### #8: Better Error Messages

**Priority**: MEDIUM | **Effort**: 1-2 hours

- Replace generic "Failed to rename" with specific errors
- Example: "Permission denied - check folder permissions"
- Suggest fixes: "Try running as administrator"

### #9: Inline Preview Column (Future)

**Priority**: LOW | **Effort**: 4+ hours (architectural change)

- Add "Preview" column to file table
- Update live as template changes
- Reduces need for preview modal

### #10: Search/Filter Loaded Files

**Priority**: LOW | **Effort**: 2 hours

- Add search box above file table
- Filter by filename, artist, title, etc.
- Useful for large directories (1000+ files)

---

## Summary Table

| # | Improvement | Priority | Impact | Effort | Est. Time |
|---|-------------|----------|--------|--------|-----------|
| 1 | Undo Pattern | CRITICAL | HIGH | LOW | 2h |
| 2 | Keyboard Shortcuts | HIGH | HIGH | MEDIUM | 3h |
| 3 | Progress Indicators | HIGH | MEDIUM | MEDIUM | 2-3h |
| 4 | Empty States | HIGH | MEDIUM | LOW | 1h |
| 5 | Template Validation | HIGH | MEDIUM | MEDIUM | 2h |
| 6 | ARIA Labels | MEDIUM | MEDIUM | LOW | 2h |
| 7 | Hover Tooltips | MEDIUM | LOW | LOW | 1h |
| 8 | Better Errors | MEDIUM | MEDIUM | LOW | 1-2h |
| 9 | Inline Preview | LOW | HIGH | HIGH | 4+h |
| 10 | Search/Filter | LOW | LOW | MEDIUM | 2h |

**Total Estimated Time**: **20-22 hours** (2-3 days of focused work)

---

**Next Step**: Break down into implementation tasks with API First + TDD approach

