# Mac-Maintenance Web UI - Comprehensive Analysis

**Date**: 2026-01-28
**Purpose**: Extract lessons learned, patterns, libraries, and implementation details for DJ MP3 Renamer web UI conversion
**Source**: `~/Documents/CODE/PYTHON/DJ/batch_rename/.backup/mac-maintenance/`

---

## EXECUTIVE SUMMARY

Mac-maintenance is a **production-quality web-based macOS maintenance tool** with excellent UX. It demonstrates:
- ✅ **API-First Architecture** (FastAPI backend, vanilla JS frontend)
- ✅ **Modern Progress Dialogs** with real-time updates, cancel buttons, and time estimates
- ✅ **Professional UI/UX** with dark/light mode, toast notifications, keyboard shortcuts
- ✅ **Single-page HTML** (no build tools, ~2,500 lines)
- ✅ **Polling-based progress** (not WebSockets, simpler to implement)

**KEY INSIGHT**: This is the EXACT architecture we should use for DJ MP3 Renamer web UI.

---

## 1. TECHNOLOGY STACK

### Backend
- **FastAPI** - Modern Python web framework (async, type-hinted)
- **Pydantic** - Data validation using Python type annotations
- **psutil** - System metrics (CPU, memory, disk)
- **CORS Middleware** - Localhost-only for security

### Frontend
- **Vanilla JavaScript** - No frameworks (React/Vue/etc.)
- **Single HTML file** - ~2,500 lines with embedded CSS/JS
- **Fetch API** - For REST API calls
- **Polling** - For progress updates (every 500ms)

### Styling
- **CSS Variables** - For theme support (dark/light)
- **Flexbox/Grid** - For responsive layouts
- **Apple-style Design** - Clean, modern, professional
- **Custom Components** - Progress bars, cards, metrics, toasts

---

## 2. PROGRESS DIALOG IMPLEMENTATION

### 2.1 HTML Structure (lines 1113-1150)

```html
<div class="progress-overlay" id="progress-overlay">
    <div class="progress-modal">
        <h3 id="progress-title">Processing...</h3>

        <!-- Progress Stats -->
        <div class="progress-stats">
            <div class="progress-stat">
                <div class="progress-stat-value" id="progress-current">0</div>
                <div class="progress-stat-label">Processed</div>
            </div>
            <div class="progress-stat">
                <div class="progress-stat-value" id="progress-total">0</div>
                <div class="progress-stat-label">Total</div>
            </div>
            <div class="progress-stat">
                <div class="progress-stat-value" id="progress-time">--</div>
                <div class="progress-stat-label">Time Remaining</div>
            </div>
        </div>

        <!-- Progress Bar -->
        <div class="progress-bar-wrapper">
            <div class="progress-bar">
                <div class="progress-bar-fill-animated" id="progress-bar-fill"></div>
            </div>
            <div class="progress-percent" id="progress-percent">0%</div>
        </div>

        <!-- Current File -->
        <div class="progress-current-file">
            <strong>Current:</strong> <span id="progress-current-file">--</span>
        </div>

        <!-- Cancel Button -->
        <div class="progress-actions">
            <button class="danger" onclick="cancelProgress()" id="progress-cancel-btn">
                Cancel Operation
            </button>
        </div>
    </div>
</div>
```

**Key Components:**
1. **Overlay** - Full-screen semi-transparent background
2. **Modal** - Centered dialog box
3. **Stats Grid** - Processed count, total, time remaining
4. **Progress Bar** - Animated width transition
5. **Current File Display** - Shows what's being processed
6. **Cancel Button** - Calls cancel callback

---

### 2.2 CSS Styling (lines 842-940)

```css
.progress-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    backdrop-filter: blur(8px);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s;
}

.progress-overlay.active {
    opacity: 1;
    pointer-events: auto;
}

.progress-modal {
    background: var(--bg-secondary);
    padding: 2.5rem;
    border-radius: 16px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    min-width: 500px;
    max-width: 600px;
}

.progress-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.5rem;
    margin: 2rem 0;
}

.progress-stat-value {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--accent-color);
}

.progress-bar-fill-animated {
    height: 100%;
    background: linear-gradient(90deg, var(--accent-color), #00d4ff);
    transition: width 0.3s ease-out;
    border-radius: 8px;
}
```

**Key Styling Techniques:**
1. **Backdrop Blur** - Modern glassmorphism effect
2. **CSS Variables** - Theme support (dark/light)
3. **Transitions** - Smooth animations (opacity, width)
4. **Grid Layout** - Responsive stats display
5. **Gradient** - Animated progress bar fill

---

### 2.3 JavaScript Logic (lines 1347-1450)

```javascript
// Global progress state
let progressOverlay, progressTitle, progressCurrent, progressTotal;
let progressTimeRemaining, progressPercent, progressBarFill;
let progressCurrentFile, progressStartTime, progressCancelCallback;

/**
 * Show progress overlay with title and total items
 * @param {string} title - Operation title
 * @param {number} total - Total items to process
 * @param {Function} cancelCallback - Function to call on cancel
 */
function showProgressOverlay(title, total, cancelCallback) {
    // Get DOM elements
    progressOverlay = document.getElementById('progress-overlay');
    progressTitle = document.getElementById('progress-title');
    progressCurrent = document.getElementById('progress-current');
    progressTotal = document.getElementById('progress-total');
    progressTimeRemaining = document.getElementById('progress-time');
    progressPercent = document.getElementById('progress-percent');
    progressBarFill = document.getElementById('progress-bar-fill');
    progressCurrentFile = document.getElementById('progress-current-file');

    // Set initial values
    progressTitle.textContent = title;
    progressTotal.textContent = total;
    progressCurrent.textContent = '0';
    progressPercent.textContent = '0%';
    progressBarFill.style.width = '0%';
    progressCurrentFile.textContent = '--';
    progressTimeRemaining.textContent = '--';

    // Store callback and start time
    progressCancelCallback = cancelCallback;
    progressStartTime = Date.now();

    // Show overlay
    progressOverlay.classList.add('active');
}

/**
 * Update progress with current count and optional filename
 * @param {number} current - Current processed count
 * @param {string} filename - Current file being processed
 */
function updateProgress(current, filename = '') {
    const total = parseInt(progressTotal.textContent);
    const percent = Math.round((current / total) * 100);

    // Update counters
    progressCurrent.textContent = current;
    progressPercent.textContent = `${percent}%`;
    progressBarFill.style.width = `${percent}%`;

    // Update current file
    if (filename) {
        progressCurrentFile.textContent = filename;
    }

    // Calculate time remaining
    if (current > 0) {
        const elapsed = (Date.now() - progressStartTime) / 1000; // seconds
        const rate = current / elapsed; // items per second
        const remaining = total - current;
        const eta = Math.round(remaining / rate); // seconds

        // Format ETA
        if (eta < 60) {
            progressTimeRemaining.textContent = `${eta}s`;
        } else {
            const minutes = Math.floor(eta / 60);
            const seconds = eta % 60;
            progressTimeRemaining.textContent = `${minutes}m ${seconds}s`;
        }
    }
}

/**
 * Hide progress overlay
 */
function hideProgressOverlay() {
    if (progressOverlay) {
        progressOverlay.classList.remove('active');
    }
}

/**
 * Cancel progress operation
 */
function cancelProgress() {
    if (progressCancelCallback) {
        progressCancelCallback();
    }
    hideProgressOverlay();
    showToast('Operation cancelled', 'warning');
}
```

**Key Implementation Details:**
1. **Global State** - Simple state management without frameworks
2. **Time Estimation** - Calculates ETA based on rate (items/second)
3. **Callback Pattern** - Cancel button calls user-provided callback
4. **Smooth Updates** - CSS transitions handle animation
5. **Format Helpers** - Converts seconds to human-readable format

---

### 2.4 Backend Progress API (server.py lines 200-250)

```python
# In-memory operation state (for progress tracking)
operation_status = {
    "running": False,
    "total": 0,
    "processed": 0,
    "current_file": "",
    "cancelled": False,
}

@app.get("/api/operations/status")
async def get_operation_status():
    """Get current operation status for progress tracking."""
    return operation_status

@app.post("/api/operations/cancel")
async def cancel_operation():
    """Cancel current operation."""
    operation_status["cancelled"] = True
    return {"status": "cancelled"}

@app.post("/api/operations/run")
async def run_operations(request: RunOperationsRequest):
    """Run maintenance operations (async, updates progress)."""
    operation_status["running"] = True
    operation_status["total"] = len(request.operation_ids)
    operation_status["processed"] = 0
    operation_status["cancelled"] = False

    for i, op_id in enumerate(request.operation_ids):
        # Check for cancellation
        if operation_status["cancelled"]:
            break

        # Update progress
        operation_status["processed"] = i
        operation_status["current_file"] = op_id

        # Do actual work here...
        await do_operation(op_id)

    operation_status["running"] = False
    return {"status": "completed"}
```

**Key Backend Patterns:**
1. **In-Memory State** - Simple dict for progress tracking
2. **Polling-Friendly** - GET endpoint returns current status
3. **Cancel Flag** - Check `cancelled` flag in processing loop
4. **Async Operations** - Uses `async def` for non-blocking I/O

---

### 2.5 Frontend Polling Loop (lines 2000-2100)

```javascript
/**
 * Run maintenance operations with progress tracking
 */
async function runMaintenanceOperations() {
    const selectedOps = getSelectedOperations();
    if (selectedOps.length === 0) {
        showToast('Please select at least one operation', 'warning');
        return;
    }

    // Show progress dialog
    showProgressOverlay(
        'Running Maintenance Operations',
        selectedOps.length,
        () => fetch('/api/operations/cancel', { method: 'POST' })
    );

    // Start operations
    const startResponse = await fetch('/api/operations/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operation_ids: selectedOps })
    });

    // Poll for progress
    const pollInterval = setInterval(async () => {
        const statusResponse = await fetch('/api/operations/status');
        const status = await statusResponse.json();

        // Update progress UI
        updateProgress(status.processed, status.current_file);

        // Check if done
        if (!status.running) {
            clearInterval(pollInterval);
            hideProgressOverlay();
            showToast('Operations completed!', 'success');
        }
    }, 500); // Poll every 500ms
}
```

**Key Polling Patterns:**
1. **setInterval** - Poll every 500ms (reasonable tradeoff)
2. **Async/Await** - Clean async code
3. **Cleanup** - Clear interval when done
4. **Error Handling** - Try/catch wraps (not shown for brevity)

---

## 3. TOAST NOTIFICATIONS

### 3.1 HTML Structure (lines 1150-1155)

```html
<!-- Toast container (bottom-right) -->
<div id="toast-container"></div>
```

### 3.2 CSS Styling (lines 720-780)

```css
#toast-container {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    z-index: 2000;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    max-width: 400px;
}

.toast {
    background: var(--bg-secondary);
    padding: 1rem 1.5rem;
    border-radius: 12px;
    box-shadow: 0 8px 24px var(--shadow);
    display: flex;
    align-items: center;
    gap: 1rem;
    border-left: 4px solid var(--accent-color);
    animation: slideIn 0.3s ease-out;
}

.toast.success { border-left-color: var(--success-color); }
.toast.error { border-left-color: var(--danger-color); }
.toast.warning { border-left-color: #ff9500; }

@keyframes slideIn {
    from {
        transform: translateX(400px);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

@keyframes slideOut {
    from {
        transform: translateX(0);
        opacity: 1;
    }
    to {
        transform: translateX(400px);
        opacity: 0;
    }
}
```

### 3.3 JavaScript Implementation (lines 1300-1340)

```javascript
/**
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type: success, error, warning, info
 * @param {number} duration - Duration in ms (default 4000)
 */
function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    // Add icon
    const icon = document.createElement('span');
    icon.textContent = getToastIcon(type);
    icon.style.fontSize = '1.5rem';

    // Add message
    const text = document.createElement('span');
    text.textContent = message;

    toast.appendChild(icon);
    toast.appendChild(text);
    container.appendChild(toast);

    // Auto-dismiss
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

function getToastIcon(type) {
    switch (type) {
        case 'success': return '✅';
        case 'error': return '❌';
        case 'warning': return '⚠️';
        default: return 'ℹ️';
    }
}
```

**Key Toast Patterns:**
1. **Non-Blocking** - Doesn't interrupt user workflow
2. **Auto-Dismiss** - Removes after 4 seconds
3. **Stacking** - Multiple toasts stack vertically
4. **Animated** - Slide in/out animations
5. **Color-Coded** - Visual distinction by type

---

## 4. KEYBOARD SHORTCUTS

### 4.1 Implementation (lines 2500-2600)

```javascript
// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Cmd+Enter / Ctrl+Enter - Run operations
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        const activeTab = document.querySelector('.tab-content.active');
        if (activeTab.id === 'maintenance-tab') {
            runMaintenanceOperations();
        } else if (activeTab.id === 'storage-tab') {
            analyzeStorage();
        }
    }

    // Cmd+F / Ctrl+F - Focus search
    if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
        e.preventDefault();
        const searchBox = document.getElementById('operation-search');
        if (searchBox) {
            searchBox.focus();
        }
    }

    // Cmd+L / Ctrl+L - Focus path input
    if ((e.metaKey || e.ctrlKey) && e.key === 'l') {
        e.preventDefault();
        const pathInput = document.getElementById('path-input');
        if (pathInput) {
            pathInput.focus();
        }
    }

    // Escape - Clear search / close dialogs
    if (e.key === 'Escape') {
        const searchBox = document.getElementById('operation-search');
        if (searchBox && document.activeElement === searchBox) {
            searchBox.value = '';
            filterOperations();
        }
        hideProgressOverlay();
    }
});
```

**Key Shortcut Patterns:**
1. **Standard Conventions** - Cmd+Enter, Cmd+F, Escape
2. **Cross-Platform** - Checks both Cmd (Mac) and Ctrl (Windows/Linux)
3. **Context-Aware** - Different actions per active tab
4. **Prevent Default** - Blocks browser shortcuts

---

## 5. DARK/LIGHT MODE

### 5.1 Implementation (lines 2700-2750)

```javascript
// Theme management
function initTheme() {
    // Check saved preference or system preference
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    const theme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
    setTheme(theme);
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);

    // Update toggle button icon
    const toggleBtn = document.getElementById('theme-toggle');
    toggleBtn.textContent = theme === 'dark' ? '☀️' : '🌙';
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    setTheme(next);
}

// Initialize on page load
initTheme();

// Listen for system theme changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!localStorage.getItem('theme')) {
        setTheme(e.matches ? 'dark' : 'light');
    }
});
```

**Key Theme Patterns:**
1. **localStorage** - Persists user preference
2. **System Preference** - Respects OS setting
3. **CSS Variables** - All colors defined at root
4. **Smooth Transitions** - CSS transitions on theme change
5. **Icon Toggle** - Sun/moon icon feedback

---

## 6. DIRECTORY BROWSER

### 6.1 HTML Structure (lines 1600-1700)

```html
<!-- Quick path buttons -->
<div class="quick-paths">
    <button onclick="setPath('/Users/username')">👤 Users</button>
    <button onclick="setPath('/Users/username')">🏠 Home</button>
    <button onclick="setPath('/Users/username/Downloads')">⬇️ Downloads</button>
    <button onclick="setPath('/Users/username/Documents')">📄 Documents</button>
    <button onclick="setPath('/Users/username/Desktop')">🖥️ Desktop</button>
    <button onclick="setPath('/Applications')">📦 Applications</button>
    <button onclick="setPath('/Library')">📚 Library</button>
</div>

<!-- Breadcrumb navigation -->
<div class="breadcrumbs" id="breadcrumbs"></div>

<!-- Path input -->
<input type="text" id="path-input" placeholder="/Users/username">
```

### 6.2 JavaScript Implementation (lines 1900-2000)

```javascript
function setPath(path) {
    document.getElementById('path-input').value = path;
    updateBreadcrumbs(path);
}

function updateBreadcrumbs(path) {
    const breadcrumbs = document.getElementById('breadcrumbs');
    breadcrumbs.innerHTML = '';

    const parts = path.split('/').filter(p => p);
    let currentPath = '';

    // Root
    const root = document.createElement('span');
    root.textContent = '/';
    root.className = 'breadcrumb';
    root.onclick = () => setPath('/');
    breadcrumbs.appendChild(root);

    // Path parts
    parts.forEach((part, i) => {
        currentPath += '/' + part;
        const pathCopy = currentPath; // Capture for closure

        const separator = document.createElement('span');
        separator.textContent = ' / ';
        separator.className = 'breadcrumb-separator';
        breadcrumbs.appendChild(separator);

        const crumb = document.createElement('span');
        crumb.textContent = part;
        crumb.className = 'breadcrumb' + (i === parts.length - 1 ? ' active' : '');
        crumb.onclick = () => setPath(pathCopy);
        breadcrumbs.appendChild(crumb);
    });
}

// Detect username automatically
async function detectUsername() {
    const response = await fetch('/api/system/info');
    const data = await response.json();
    const username = data.system.username;

    // Update quick path buttons
    document.querySelectorAll('.quick-paths button').forEach(btn => {
        const path = btn.getAttribute('onclick').match(/setPath\('(.+)'\)/)[1];
        const updatedPath = path.replace('/Users/username', `/Users/${username}`);
        btn.setAttribute('onclick', `setPath('${updatedPath}')`);
    });
}
```

**Key Directory Browser Patterns:**
1. **Quick Paths** - Common locations as buttons
2. **Breadcrumbs** - Click any part to navigate
3. **Auto-Detection** - Fetches username from API
4. **Event Delegation** - Dynamic click handlers

---

## 7. ARCHITECTURE PATTERNS

### 7.1 API-First Design

```
┌──────────────────────────────────────────────┐
│           Frontend (index.html)               │
│  • Vanilla JS (no build tools)               │
│  • Fetch API for REST calls                  │
│  • Polling for progress updates              │
│  • Event-driven UI updates                   │
└────────────────┬─────────────────────────────┘
                 │
                 │ HTTP REST API
                 ↓
┌──────────────────────────────────────────────┐
│         Backend (FastAPI server.py)           │
│  • REST endpoints (/api/...)                 │
│  • In-memory state for progress              │
│  • Pydantic models for validation            │
│  • CORS middleware (localhost only)          │
└────────────────┬─────────────────────────────┘
                 │
                 │ Calls
                 ↓
┌──────────────────────────────────────────────┐
│         Business Logic (api/)                 │
│  • StorageAPI, MaintenanceAPI                │
│  • Core modules (pure functions)             │
│  • No UI dependencies                        │
└──────────────────────────────────────────────┘
```

**Key Separation:**
- **Frontend**: UI only, no business logic
- **Backend**: Thin REST layer, orchestrates API
- **Business Logic**: Pure functions, testable

---

### 7.2 State Management Pattern

```javascript
// Global state (simple, no frameworks needed)
const appState = {
    theme: 'light',
    activeTab: 'dashboard',
    operations: [],
    selectedOperations: [],
    systemMetrics: {},
};

// Update functions
function updateState(key, value) {
    appState[key] = value;
    render();  // Re-render UI
}

// Persistence
function saveState() {
    localStorage.setItem('appState', JSON.stringify(appState));
}

function loadState() {
    const saved = localStorage.getItem('appState');
    if (saved) {
        Object.assign(appState, JSON.parse(saved));
    }
}
```

**Key State Patterns:**
1. **Single Source of Truth** - One global state object
2. **Immutable Updates** - New values, not mutations
3. **localStorage** - Persist across sessions
4. **Simple Render** - Re-render on state change

---

## 8. LESSONS LEARNED

### 8.1 What Works Well ✅

1. **Single HTML File** - No build tools, easier to deploy
2. **Polling for Progress** - Simpler than WebSockets, sufficient for most use cases
3. **CSS Variables** - Theme support without duplicating CSS
4. **Toast Notifications** - Non-blocking, professional UX
5. **Vanilla JS** - No framework overhead, faster load times
6. **FastAPI** - Clean, modern, type-safe Python backend
7. **In-Memory State** - Simple progress tracking without database
8. **Polling Interval 500ms** - Good balance between responsiveness and server load

### 8.2 What Could Be Improved ⚠️

1. **Large HTML File** - 2,500 lines gets unwieldy (but acceptable)
2. **No TypeScript** - Vanilla JS lacks type safety
3. **Manual DOM Manipulation** - More verbose than frameworks
4. **No Testing** - Frontend has no unit tests
5. **Polling Inefficiency** - Constant requests even when idle

---

## 9. REUSABLE PATTERNS FOR DJ MP3 RENAMER

### 9.1 Progress Dialog

**Exact pattern to reuse:**
```html
<div class="progress-overlay">
    <div class="progress-modal">
        <h3>Renaming MP3 Files...</h3>
        <div class="progress-stats">
            <div class="progress-stat">
                <div class="progress-stat-value">45</div>
                <div class="progress-stat-label">Processed</div>
            </div>
            <div class="progress-stat">
                <div class="progress-stat-value">100</div>
                <div class="progress-stat-label">Total</div>
            </div>
            <div class="progress-stat">
                <div class="progress-stat-value">32s</div>
                <div class="progress-stat-label">Remaining</div>
            </div>
        </div>
        <div class="progress-bar-wrapper">
            <div class="progress-bar">
                <div class="progress-bar-fill-animated"></div>
            </div>
            <div class="progress-percent">45%</div>
        </div>
        <div class="progress-current-file">
            <strong>Current:</strong> Artist - Title (Extended Mix).mp3
        </div>
        <div class="progress-actions">
            <button class="danger" onclick="cancelProgress()">Cancel</button>
        </div>
    </div>
</div>
```

**Backend endpoint:**
```python
@app.get("/api/rename/status")
async def get_rename_status():
    return {
        "running": True,
        "total": 100,
        "processed": 45,
        "current_file": "Artist - Title (Extended Mix).mp3",
        "cancelled": False
    }

@app.post("/api/rename/cancel")
async def cancel_rename():
    operation_status["cancelled"] = True
    return {"status": "cancelled"}
```

---

## 10. IMPLEMENTATION CHECKLIST FOR DJ MP3 RENAMER

### Phase A1: Backend (FastAPI)
- [ ] Install FastAPI, uvicorn
- [ ] Create `web/server.py` with REST endpoints:
  - [ ] GET `/api/health` - Health check
  - [ ] POST `/api/rename/start` - Start rename operation
  - [ ] GET `/api/rename/status` - Get progress
  - [ ] POST `/api/rename/cancel` - Cancel operation
  - [ ] GET `/api/templates` - Get available templates
- [ ] Add in-memory state for progress tracking
- [ ] Add CORS middleware (localhost only)
- [ ] Integrate with existing RenamerAPI

### Phase A2: Frontend (HTML/CSS/JS)
- [ ] Create `web/static/index.html` (single file)
- [ ] Implement progress dialog (copy pattern from mac-maintenance)
- [ ] Implement toast notifications
- [ ] Implement dark/light mode toggle
- [ ] Implement keyboard shortcuts (Cmd+Enter, Escape)
- [ ] Add directory browser with quick paths
- [ ] Add template selector
- [ ] Style with Apple-inspired design (CSS variables)

### Phase A3: Integration
- [ ] Connect frontend polling to backend status endpoint
- [ ] Test progress updates (45/100, time remaining, etc.)
- [ ] Test cancel button functionality
- [ ] Test error handling (show errors as toasts)
- [ ] Test keyboard shortcuts
- [ ] Test dark/light mode persistence

### Phase A4: Testing
- [ ] Manual testing checklist
- [ ] Browser compatibility (Chrome, Firefox, Safari, Edge)
- [ ] Responsive design testing (desktop, tablet)
- [ ] Accessibility testing (keyboard navigation, screen readers)
- [ ] Performance testing (1000+ files)

---

## 11. LIBRARIES & DEPENDENCIES

### Python Backend
```txt
fastapi==0.104.0
uvicorn==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
```

### Frontend (None!)
- **Vanilla JavaScript** - No dependencies
- **CSS3** - Modern features (variables, grid, flexbox)
- **HTML5** - Semantic elements

---

## 12. FILE STRUCTURE

```
mac-maintenance/
├── src/
│   └── mac_maintenance/
│       ├── api/           # Business logic (API-first)
│       ├── core/          # Pure functions
│       └── web/
│           ├── server.py  # FastAPI backend
│           └── static/
│               └── index.html  # Single-page app (~2,500 lines)
├── tests/                 # pytest tests
├── run-web.sh            # Launch script
└── README.md
```

**Recommended for DJ MP3 Renamer:**
```
dj-mp3-renamer/
├── dj_mp3_renamer/
│   ├── api/              # Existing API (no changes)
│   ├── core/             # Existing core (no changes)
│   └── web/              # NEW
│       ├── __init__.py
│       ├── server.py     # FastAPI backend
│       └── static/
│           └── index.html # Single-page app
├── tests/
│   └── test_web.py       # NEW
└── run_web.py            # Launch script
```

---

## 13. SECURITY CONSIDERATIONS

### What Mac-Maintenance Does Right ✅
1. **CORS Localhost Only** - Prevents cross-origin attacks
2. **No Password Handling** - Uses launchd daemon for privileges
3. **Input Validation** - Pydantic models validate all inputs
4. **No Shell Execution** - Uses Python libraries instead

### What to Apply to DJ MP3 Renamer
1. **Path Validation** - Fix path traversal vulnerability (Option B task)
2. **CORS Configuration** - Localhost only
3. **Input Sanitization** - Validate all file paths
4. **Rate Limiting** - Prevent DOS attacks (optional)

---

## 14. PERFORMANCE OPTIMIZATION

### Techniques Used in Mac-Maintenance
1. **Polling Interval** - 500ms (not too frequent)
2. **Circular Buffer** - Store last 60 metrics only
3. **CSS Transitions** - Hardware-accelerated animations
4. **Lazy Loading** - Load data on demand
5. **Debouncing** - Search input debounced 300ms

### Recommended for DJ MP3 Renamer
1. **Polling** - 500ms for progress updates
2. **Batch Updates** - Update UI every N files, not every file
3. **Virtual Scrolling** - If showing 1000+ results
4. **Web Workers** - For heavy computation (optional)

---

## 15. CONCLUSION

Mac-maintenance provides an **excellent blueprint** for DJ MP3 Renamer web UI:

**Key Takeaways:**
1. ✅ **API-First** - Frontend calls REST API only
2. ✅ **Simple Stack** - Vanilla JS + FastAPI (no build tools)
3. ✅ **Progress Pattern** - Polling with cancel support
4. ✅ **Professional UX** - Toast notifications, dark mode, keyboard shortcuts
5. ✅ **Single HTML** - Easier to deploy and maintain

**Next Steps:**
1. Implement Option B (security fixes) first
2. Implement Option C (API improvements)
3. Implement Option A (web UI using these patterns)

---

**END OF ANALYSIS**

**Files to Reference:**
- This document: `.claude/MAC_MAINTENANCE_ANALYSIS.md`
- Source code: `.backup/mac-maintenance/src/mac_maintenance/web/`
- Task tracking: `.claude/TASKS.md`
