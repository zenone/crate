# UX Implementation Tasks

**Date**: 2026-01-30
**Status**: Ready for Implementation
**Methodology**: API First + TDD
**Reference**: UX Improvements Proposed (ux-improvements-proposed.md)

---

## Task Numbering

Previous tasks: #42-58 (11 complete, 5 pending for smart detection)
New UX tasks: **#59-73** (15 new tasks)

---

## Implementation Priority Order

### Phase 1: Critical Fixes (Tasks #59-63)
**Duration**: 1-2 days
**Focus**: Undo pattern, keyboard shortcuts, loading feedback

### Phase 2: UX Enhancements (Tasks #64-68)
**Duration**: 1-2 days
**Focus**: Empty states, validation, accessibility

### Phase 3: Polish (Tasks #69-73)
**Duration**: 0.5-1 day
**Focus**: Tooltips, error messages, search

---

## Task #59: Backend - Implement Undo/Redo System

**Category**: Backend
**Priority**: CRITICAL
**Estimated Time**: 1.5 hours
**Depends On**: None
**Blocks**: #60

### Description

Create backend API endpoint and infrastructure to support undo/redo for rename operations.

### API First Design

**New Endpoint:**
```python
@app.post("/api/rename/undo")
async def undo_rename(session_id: str):
    """
    Undo a previously executed rename operation.

    Args:
        session_id: Unique session ID from execute_rename response

    Returns:
        {
            "success": True,
            "reverted_count": 45,
            "message": "Renamed 45 files back to original names"
        }

    Raises:
        HTTPException 404: Session expired or not found
        HTTPException 400: Files no longer exist or were modified
    """
```

**Modified Endpoint:**
```python
@app.post("/api/rename/execute")
async def execute_rename(request: ExecuteRenameRequest):
    """
    Execute rename operation and store undo history.

    Returns:
        {
            "success": True,
            "renamed_count": 45,
            "session_id": "uuid-here",  # NEW
            "expires_at": "2026-01-30T12:45:00Z"  # NEW
        }
    """
```

### Implementation Steps

**1. Add session management:**
```python
# web/main.py

from datetime import datetime, timedelta
import uuid

# In-memory session store (for MVP, use Redis for production)
undo_sessions = {}  # session_id -> UndoSession

class UndoSession:
    def __init__(self, pairs: List[Tuple[str, str]], expires_in_seconds=30):
        self.session_id = str(uuid.uuid4())
        self.pairs = pairs  # [(old_path, new_path), ...]
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(seconds=expires_in_seconds)

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
```

**2. Modify execute_rename:**
```python
@app.post("/api/rename/execute")
async def execute_rename(request: ExecuteRenameRequest):
    # ... existing rename logic ...

    # Store undo session
    session = UndoSession(pairs=renamed_pairs, expires_in_seconds=30)
    undo_sessions[session.session_id] = session

    # Clean up expired sessions
    cleanup_expired_sessions()

    return {
        "success": True,
        "renamed_count": len(renamed_pairs),
        "session_id": session.session_id,
        "expires_at": session.expires_at.isoformat()
    }
```

**3. Implement undo endpoint:**
```python
@app.post("/api/rename/undo")
async def undo_rename(session_id: str):
    # Check if session exists
    if session_id not in undo_sessions:
        raise HTTPException(
            status_code=404,
            detail="Undo session not found or expired"
        )

    session = undo_sessions[session_id]

    # Check if expired
    if session.is_expired():
        del undo_sessions[session_id]
        raise HTTPException(
            status_code=404,
            detail="Undo session expired (available for 30 seconds only)"
        )

    # Revert renames
    reverted = []
    errors = []

    for old_path, new_path in session.pairs:
        try:
            if not os.path.exists(new_path):
                errors.append(f"File no longer exists: {new_path}")
                continue

            os.rename(new_path, old_path)
            reverted.append((new_path, old_path))

        except PermissionError:
            errors.append(f"Permission denied: {new_path}")
        except OSError as e:
            errors.append(f"Error reverting {new_path}: {str(e)}")

    # Clean up session
    del undo_sessions[session_id]

    return {
        "success": len(reverted) > 0,
        "reverted_count": len(reverted),
        "error_count": len(errors),
        "errors": errors
    }
```

**4. Add cleanup function:**
```python
def cleanup_expired_sessions():
    """Remove expired undo sessions from memory."""
    expired_ids = [
        sid for sid, session in undo_sessions.items()
        if session.is_expired()
    ]
    for sid in expired_ids:
        del undo_sessions[sid]
```

### Testing Requirements

**Unit Tests (test_api.py):**
```python
def test_rename_returns_session_id():
    response = client.post("/api/rename/execute", json={...})
    assert "session_id" in response.json()
    assert "expires_at" in response.json()

def test_undo_reverts_rename():
    # Execute rename
    rename_response = client.post("/api/rename/execute", json={...})
    session_id = rename_response.json()["session_id"]

    # Verify files renamed
    assert os.path.exists(new_filename)

    # Undo
    undo_response = client.post("/api/rename/undo", params={"session_id": session_id})
    assert undo_response.json()["success"] is True

    # Verify files reverted
    assert os.path.exists(old_filename)

def test_undo_expired_session_returns_404():
    # Create session with 0 second expiry
    session_id = "fake-expired-id"
    response = client.post("/api/rename/undo", params={"session_id": session_id})
    assert response.status_code == 404

def test_undo_nonexistent_session_returns_404():
    response = client.post("/api/rename/undo", params={"session_id": "nonexistent"})
    assert response.status_code == 404
```

### Acceptance Criteria

- [ ] execute_rename returns session_id and expires_at
- [ ] undo endpoint reverts file renames
- [ ] Sessions expire after 30 seconds
- [ ] Expired sessions return 404
- [ ] Nonexistent sessions return 404
- [ ] Undo handles missing files gracefully
- [ ] All tests pass

### Files to Modify

- `web/main.py` - Add undo endpoint and session management
- `tests/test_api.py` - Add unit tests

---

## Task #60: Frontend - Add Undo Button to Toast

**Category**: Frontend
**Priority**: CRITICAL
**Estimated Time**: 1 hour
**Depends On**: #59
**Blocks**: None

### Description

Add undo button to rename success toast, with 30-second timer and auto-dismiss.

### Implementation Steps

**1. Update UI.js:**
```javascript
// web/static/js/ui.js

showUndoToast(message, undoCallback, expiresInSeconds = 30) {
    const container = document.getElementById('toast-container');

    const toast = document.createElement('div');
    toast.className = 'toast success toast-undo';
    toast.innerHTML = `
        <div class="toast-content">
            <div class="toast-message">${message}</div>
            <button class="toast-undo-btn">
                ↶ Undo
            </button>
            <div class="toast-timer">
                <span class="toast-timer-text">Undo available for <span id="toast-timer-seconds">${expiresInSeconds}</span>s</span>
                <div class="toast-timer-bar">
                    <div class="toast-timer-fill"></div>
                </div>
            </div>
        </div>
    `;

    // Undo button handler
    const undoBtn = toast.querySelector('.toast-undo-btn');
    undoBtn.onclick = () => {
        undoCallback();
        toast.remove();
        clearInterval(timerInterval);
        clearTimeout(autoHideTimer);
    };

    // Add to DOM
    container.appendChild(toast);

    // Countdown timer
    let secondsRemaining = expiresInSeconds;
    const timerText = toast.querySelector('#toast-timer-seconds');
    const timerFill = toast.querySelector('.toast-timer-fill');

    const timerInterval = setInterval(() => {
        secondsRemaining--;
        timerText.textContent = secondsRemaining;

        const progress = (expiresInSeconds - secondsRemaining) / expiresInSeconds * 100;
        timerFill.style.width = `${progress}%`;

        if (secondsRemaining <= 0) {
            clearInterval(timerInterval);
        }
    }, 1000);

    // Auto-hide after expiry
    const autoHideTimer = setTimeout(() => {
        toast.classList.add('toast-fade-out');
        setTimeout(() => toast.remove(), 300);
    }, expiresInSeconds * 1000);
}
```

**2. Update app.js to use undo toast:**
```javascript
// web/static/js/app.js

async executeRenameNow() {
    // ... existing rename logic ...

    try {
        const result = await this.api.executeRename(this.currentPath, false, null, filePaths);

        // Close progress modal
        this.closeProgressModal();

        // Show undo toast
        this.ui.showUndoToast(
            `✅ ${result.renamed_count} files renamed successfully`,
            () => this.undoRename(result.session_id),
            30  // 30 seconds
        );

        // Store session ID for Ctrl+Z
        this.lastRenameSessionId = result.session_id;

        // Reload directory
        await this.loadDirectory();

    } catch (error) {
        this.ui.error(`Failed to rename files: ${error.message}`);
    }
}

async undoRename(sessionId) {
    try {
        const result = await this.api.undoRename(sessionId);

        if (result.success) {
            this.ui.success(`✅ Undo successful - ${result.reverted_count} files restored`);

            if (result.error_count > 0) {
                this.ui.warning(`⚠️ ${result.error_count} files could not be reverted`);
            }

            // Reload directory
            await this.loadDirectory();

            // Clear last session ID
            this.lastRenameSessionId = null;
        }
    } catch (error) {
        this.ui.error(`Failed to undo: ${error.message}`);
    }
}
```

**3. Update api.js:**
```javascript
// web/static/js/api.js

async undoRename(sessionId) {
    const response = await fetch(`${this.baseURL}/api/rename/undo?session_id=${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to undo rename');
    }

    return await response.json();
}
```

**4. Add CSS:**
```css
/* styles.css */

.toast-undo {
    min-width: 350px;
}

.toast-content {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
}

.toast-undo-btn {
    padding: 0.625rem 1.25rem;
    background: var(--accent-primary);
    color: white;
    border: none;
    border-radius: var(--radius-sm);
    font-weight: 600;
    font-size: 0.95rem;
    cursor: pointer;
    transition: all 0.2s;
    align-self: flex-start;
}

.toast-undo-btn:hover {
    background: var(--accent-hover);
    transform: translateY(-1px);
}

.toast-undo-btn:active {
    transform: translateY(0);
}

.toast-timer {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
}

.toast-timer-text {
    font-size: 0.75rem;
    color: var(--text-muted);
    font-style: italic;
}

.toast-timer-bar {
    height: 4px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 2px;
    overflow: hidden;
}

.toast-timer-fill {
    height: 100%;
    width: 0%;
    background: var(--accent-primary);
    transition: width 1s linear;
}

.toast-fade-out {
    animation: fadeOut 0.3s ease-out forwards;
}

@keyframes fadeOut {
    to {
        opacity: 0;
        transform: translateX(100%);
    }
}
```

### Testing Requirements

**Manual Tests:**
1. Rename files → Toast appears with undo button → Click undo → Files revert
2. Rename files → Wait 30 seconds → Toast disappears
3. Rename files → Reload page → Session expired (undo unavailable)
4. Rename files → Click undo → See countdown timer (30, 29, 28...)

### Acceptance Criteria

- [ ] Toast shows undo button after rename
- [ ] Clicking undo reverts files
- [ ] Timer counts down from 30 to 0
- [ ] Progress bar animates
- [ ] Toast auto-dismisses after 30s
- [ ] Undo button removes toast immediately
- [ ] Error handling for expired sessions

### Files to Modify

- `web/static/js/ui.js` - Add showUndoToast method
- `web/static/js/app.js` - Use undo toast, add undoRename method
- `web/static/js/api.js` - Add undoRename API call
- `web/static/css/styles.css` - Add toast undo styles

---

## Task #61: Frontend - Implement Keyboard Shortcuts

**Category**: Frontend
**Priority**: HIGH
**Estimated Time**: 2.5 hours
**Depends On**: None
**Blocks**: None

### Description

Add essential keyboard shortcuts for power users and create shortcuts help modal.

### Implementation Steps

**1. Add keyboard event listener (app.js):**
```javascript
// web/static/js/app.js

setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ignore if user is typing in input/textarea
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            // Exception: Allow Escape to blur input
            if (e.key === 'Escape') {
                e.target.blur();
            }
            return;
        }

        const ctrl = e.ctrlKey || e.metaKey;

        // Ctrl+A: Select all files
        if (ctrl && e.key === 'a') {
            e.preventDefault();
            if (this.currentFiles.length > 0) {
                document.getElementById('select-all').checked = true;
                this.toggleSelectAll(true);
            }
        }

        // Ctrl+D: Deselect all files
        if (ctrl && e.key === 'd') {
            e.preventDefault();
            if (this.currentFiles.length > 0) {
                document.getElementById('select-all').checked = false;
                this.toggleSelectAll(false);
            }
        }

        // Ctrl+P: Preview
        if (ctrl && e.key === 'p') {
            e.preventDefault();
            const previewBtn = document.getElementById('preview-btn');
            if (!previewBtn.disabled) {
                this.showPreview();
            }
        }

        // Ctrl+Enter: Execute rename (only in preview modal)
        if (ctrl && e.key === 'Enter') {
            const previewModal = document.getElementById('preview-modal');
            if (!previewModal.classList.contains('hidden')) {
                e.preventDefault();
                const executeBtn = document.getElementById('preview-execute-btn');
                if (!executeBtn.disabled) {
                    this.executeRename();
                }
            }
        }

        // Ctrl+Z: Undo last rename
        if (ctrl && e.key === 'z') {
            e.preventDefault();
            if (this.lastRenameSessionId) {
                this.undoRename(this.lastRenameSessionId);
            }
        }

        // ?: Show shortcuts help
        if (e.key === '?' && !e.shiftKey) {
            e.preventDefault();
            this.showKeyboardShortcutsHelp();
        }

        // Escape: Close any open modal
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal:not(.hidden)');
            modals.forEach(modal => {
                const closeBtn = modal.querySelector('.modal-close');
                if (closeBtn) closeBtn.click();
            });
        }
    });

    // Call in init()
    this.setupKeyboardShortcuts();
}
```

**2. Create shortcuts help modal (HTML):**
```html
<!-- web/templates/index.html - Add before </body> -->

<div id="shortcuts-modal" class="modal hidden">
    <div class="modal-overlay"></div>
    <div class="modal-content">
        <div class="modal-header">
            <h2>⌨️ Keyboard Shortcuts</h2>
            <button class="modal-close">×</button>
        </div>
        <div class="modal-body">
            <table class="shortcuts-table">
                <thead>
                    <tr>
                        <th>Shortcut</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
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
                        <td><kbd>Ctrl</kbd> + <kbd>Enter</kbd></td>
                        <td>Execute rename (in preview modal)</td>
                    </tr>
                    <tr>
                        <td><kbd>Ctrl</kbd> + <kbd>Z</kbd></td>
                        <td>Undo last rename</td>
                    </tr>
                    <tr>
                        <td><kbd>Escape</kbd></td>
                        <td>Close modal or blur input</td>
                    </tr>
                    <tr>
                        <td><kbd>?</kbd></td>
                        <td>Show this help</td>
                    </tr>
                </tbody>
            </table>
            <p class="shortcuts-note">
                💡 <strong>Tip:</strong> On Mac, use <kbd>Cmd</kbd> instead of <kbd>Ctrl</kbd>
            </p>
        </div>
        <div class="modal-footer">
            <button class="btn btn-secondary modal-close">Close</button>
        </div>
    </div>
</div>
```

**3. Add showKeyboardShortcutsHelp method:**
```javascript
// web/static/js/app.js

showKeyboardShortcutsHelp() {
    const modal = document.getElementById('shortcuts-modal');
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    // Setup close handlers
    const closeButtons = modal.querySelectorAll('.modal-close');
    closeButtons.forEach(btn => {
        btn.onclick = () => {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        };
    });

    const overlay = modal.querySelector('.modal-overlay');
    overlay.onclick = () => {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    };
}
```

**4. Add CSS:**
```css
/* styles.css */

.shortcuts-table {
    width: 100%;
    border-collapse: collapse;
}

.shortcuts-table th {
    text-align: left;
    padding: var(--spacing-sm);
    border-bottom: 2px solid var(--border);
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
}

.shortcuts-table td {
    padding: var(--spacing-sm);
    border-bottom: 1px solid var(--border);
}

.shortcuts-table tbody tr:last-child td {
    border-bottom: none;
}

kbd {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 0.875rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    margin: 0 0.125rem;
}

.shortcuts-note {
    margin-top: var(--spacing-md);
    padding: var(--spacing-sm);
    background: rgba(99, 102, 241, 0.1);
    border-left: 3px solid var(--accent-primary);
    border-radius: var(--radius-sm);
    font-size: 0.875rem;
}
```

**5. Add shortcut hint to header:**
```html
<!-- Add to header or footer -->
<div class="keyboard-shortcut-hint">
    Press <kbd>?</kbd> for keyboard shortcuts
</div>
```

### Testing Requirements

**Manual Tests:**
1. Press Ctrl+A → All files selected
2. Press Ctrl+D → All files deselected
3. Press Ctrl+P → Preview modal opens (if files selected)
4. Press Ctrl+Enter in preview → Rename executes
5. Press Ctrl+Z after rename → Files revert
6. Press ? → Shortcuts help opens
7. Press Escape → Modal closes

### Acceptance Criteria

- [ ] All shortcuts work as specified
- [ ] Shortcuts don't interfere with typing in inputs
- [ ] Escape blurs inputs
- [ ] ? key opens help modal
- [ ] Help modal shows all shortcuts
- [ ] Shortcuts work on both Windows (Ctrl) and Mac (Cmd)

### Files to Modify

- `web/static/js/app.js` - Add setupKeyboardShortcuts method
- `web/templates/index.html` - Add shortcuts modal
- `web/static/css/styles.css` - Add styles

---

## Task #62: Frontend - Add Skeleton Screens for Loading

**Priority**: HIGH | **Time**: 2 hours | **Depends On**: None

### Description

Replace full-screen spinner with skeleton screens during metadata loading.

### Implementation

(Abbreviated - see ux-improvements-proposed.md for full details)

**Key Changes:**
- Add skeleton row HTML template
- Add shimmer animation CSS
- Show skeleton while loading metadata
- Hide skeleton when real data loaded

### Acceptance Criteria

- [ ] Skeleton screens show during metadata load
- [ ] Shimmer animation works
- [ ] Real table replaces skeleton smoothly
- [ ] Progress percentage shown: "Loading: 45/100 (45%)"

---

## Task #63: Frontend - Add Progress Indicators with ETA

**Priority**: HIGH | **Time**: 1 hour | **Depends On**: #62

### Description

Show detailed progress during metadata loading with percentage, ETA, and current file.

### Implementation

**Display:**
- "Loading metadata: 45/100 (45%)"
- "Estimated time remaining: 12 seconds"
- "Processing: Artist - Song Title.mp3"

### Acceptance Criteria

- [ ] Progress percentage displayed
- [ ] ETA calculated and shown
- [ ] Current file name shown
- [ ] Progress bar fills from 0% to 100%

---

## Task #64: Frontend - Add Empty States

**Priority**: HIGH | **Time**: 1 hour | **Depends On**: None

### Description

Add empty state UI for file list when no directory loaded.

### Implementation

(See ux-improvements-proposed.md for full HTML/CSS)

**Key Elements:**
- Large icon (📁)
- Explanation text
- CTA button ([Browse Files])
- Helper text

### Acceptance Criteria

- [ ] Empty state shows when no directory loaded
- [ ] CTA button works (opens directory browser)
- [ ] Helper text guides user

---

## Task #65: Frontend - Real-Time Template Validation

**Priority**: HIGH | **Time**: 2 hours | **Depends On**: None

### Description

Add live validation and preview for template input field.

### Implementation

**Features:**
- Check syntax as user types
- Show live preview with example metadata
- Highlight errors in red
- Show error message below input

### Acceptance Criteria

- [ ] Syntax validation works (unclosed brackets, unknown tokens)
- [ ] Live preview updates as user types
- [ ] Errors highlighted and explained
- [ ] Valid templates show green preview

---

## Tasks #66-73: Remaining Improvements

| # | Task | Priority | Time | Description |
|---|------|----------|------|-------------|
| 66 | Add ARIA Labels | MEDIUM | 2h | Accessibility improvements |
| 67 | Add Hover Tooltips | MEDIUM | 1h | Truncated filename tooltips |
| 68 | Better Error Messages | MEDIUM | 1-2h | Clearer, actionable errors |
| 69 | Settings: Remember Template | LOW | 1h | LocalStorage persistence |
| 70 | Settings: Remember Directory | LOW | 0.5h | LocalStorage persistence |
| 71 | Add Search/Filter Files | LOW | 2h | Search loaded files |
| 72 | Inline Preview Column | LOW | 4+h | Add preview column to table |
| 73 | Testing & Documentation | HIGH | 2h | Full testing of all changes |

---

## Summary

**Total Tasks**: 15 new tasks (#59-73)
**Total Estimated Time**: 22-25 hours (~3 days)

**Critical Path:**
1. Task #59 (Undo backend) → #60 (Undo frontend)
2. Task #61 (Keyboard shortcuts)
3. Task #62 (Skeleton screens) → #63 (Progress indicators)
4. Task #64 (Empty states)
5. Task #65 (Template validation)
6. Task #73 (Testing all changes)

**Completion Order:**
- **Week 1**: Tasks #59-65 (critical and high priority)
- **Week 2**: Tasks #66-68 (medium priority)
- **Future**: Tasks #69-72 (low priority, nice-to-have)

---

**Next Step**: Create tasks in task system and begin implementation

