# DJ MP3 Renamer - Lessons Learned

## Project Knowledge Base

This document captures lessons learned, best practices, and important patterns discovered during development. Reference this to avoid repeating mistakes and maintain consistent code quality.

---

## Architecture & Design Patterns

### ✅ API-First Architecture
**Pattern**: Build backend API endpoints first, then connect frontend UI.

**Benefits**:
- Decouples frontend and backend development
- Enables multiple clients (web, CLI, TUI) to share same backend
- Makes testing easier (API tests are cleaner than UI tests)
- Allows parallel development of UI and business logic

**Implementation**:
- `RenamerAPI` class provides programmatic access to all functionality
- FastAPI web endpoints wrap `RenamerAPI` methods
- Frontend uses `RenamerAPI` client class for all API calls
- All request/response models use Pydantic for validation

### ✅ Progressive/Lazy Loading
**Pattern**: Load data incrementally as needed, not all at once.

**Why**: Loading all MP3 metadata upfront for large directories (1000+ files) causes:
- Long initial load times (5-10 seconds)
- High memory usage
- Poor user experience (blank screen while loading)

**Solution**:
1. Load file list immediately (fast - just filenames)
2. Load individual file metadata on demand (background requests)
3. Display file table immediately with "..." placeholders
4. Metadata populates as it loads

**Code Example** (`web/static/js/app.js:199-207`):
```javascript
async renderFileList() {
    for (const file of this.currentFiles) {
        const row = await this.createFileRow(file);
        tbody.appendChild(row);
        // Metadata loads in background via loadFileMetadata()
    }
}
```

---

## Web Development Patterns

### ✅ Metadata Source Attribution
**Pattern**: Always show WHERE metadata came from (ID3 tags vs MusicBrainz vs AI analysis).

**Why**:
- Users need to know reliability of data
- Different sources have different confidence levels
- Helps debug metadata conflicts

**Implementation**:
- Backend: `metadata["bpm_source"]`, `metadata["key_source"]`, etc.
- Frontend: Visual badges with distinct colors:
  * 🏷️ **ID3 Tags** (blue) - from file's embedded tags
  * 🎵 **MusicBrainz** (green) - from online database
  * 🤖 **AI Analysis** (orange) - from librosa audio analysis

**Code**: See `web/static/js/app.js:464-486` for badge rendering.

### ✅ Preview Before Execute Pattern
**Pattern**: Always show users EXACTLY what will happen before destructive operations.

**Why**: File renames are destructive - once done, original names are lost.

**Implementation**:
1. Preview endpoint (`/api/rename/preview`) shows old → new names
2. User reviews changes in modal
3. User selects which files to rename (checkboxes)
4. Execute endpoint only renames selected files
5. Progress overlay shows real-time status

**UX Flow**:
```
User clicks "Preview"
  → Modal shows list of renames with metadata sources
  → User reviews and selects files
  → User clicks "Rename Selected Files"
  → Progress overlay with live updates
  → Success notification + refreshed file list
```

### ✅ Async Operations with Polling
**Pattern**: Long-running operations should be async with progress updates.

**Why**:
- Keeps UI responsive
- Allows cancellation
- Shows progress to user
- Prevents timeouts

**Implementation**:
1. Backend: `start_rename_async()` returns `operation_id`
2. Frontend: Poll `/api/operation/{id}` every 500ms
3. Update progress bar, statistics, current file
4. Display terminal-style output as operations complete
5. Handle completion/cancellation/errors

**Code**: See `web/static/js/app.js:639-681` for polling loop.

---

## Server Management

### ✅ Smart Instance Management
**Lesson**: Prevent multiple server instances from running simultaneously.

**Problem Encountered**:
- User accidentally started server multiple times
- Multiple instances listening on different ports (8001, 8002, etc.)
- Confusion about which instance to use
- Port conflicts with other applications

**Solution**: PID file tracking with smart port detection.

**Implementation** (`start_web_ui.sh`):
```bash
PIDFILE=".dj_renamer_web.pid"

# Check if already running
if is_running; then
    echo "⚠️  Already running on port $RUNNING_PORT"
    exit 0
fi

# Find available port (8000-8100)
PORT=8000
while check_port $PORT; do
    PORT=$((PORT + 1))
done

# Start and save PID
python -m uvicorn web.main:app --port $PORT &
echo $! > "$PIDFILE"
```

**Key Points**:
- PID file prevents duplicate instances
- Port detection handles conflicts with OTHER apps
- User-friendly messages explain what's happening
- `stop_web_ui.sh` uses PID file for clean shutdown

---

## Error Handling

### ✅ Graceful Async Cancellation
**Pattern**: Allow users to cancel long-running operations gracefully.

**Implementation**:
1. Backend: Check `operation["cancelled"]` flag in progress callback
2. Raise `OperationCancelled` exception when cancelled
3. Catch exception and mark operation as "cancelled"
4. Frontend: Show cancel button during operation
5. Poll until status changes to "cancelled"

**Code** (`dj_mp3_renamer/api/renamer.py:530-536`):
```python
def progress_callback(count: int, filename: str):
    with self._lock:
        if self._operations[operation_id]["cancelled"]:
            raise OperationCancelled("Operation cancelled by user")
        self._operations[operation_id]["progress"] = count
```

### ✅ Proper Error Messages
**Pattern**: Always provide ACTIONABLE error messages to users.

**Bad**: "Error"
**Good**: "Failed to read metadata from track.mp3: File is corrupted or not a valid MP3"

**Bad**: "Operation failed"
**Good**: "Rename operation failed: Directory is read-only. Check permissions."

---

## UI/UX Best Practices

### ✅ Terminal-Style Output for Technical Users
**Pattern**: Show detailed command output in monospace font with color coding.

**Why**:
- DJ users (technical audience) appreciate seeing what's happening
- Easier to debug issues
- Feels more trustworthy/transparent

**Implementation**: See mac-maintenance backup analysis - they use:
- Black background with green text (terminal colors)
- Monospace font (`var(--font-mono)`)
- Color-coded output (green=success, red=error, gray=info)

**Code** (`web/static/css/styles.css:1055-1075`):
```css
.progress-output {
    background: #1a1a2e;
    color: var(--success);
    font-family: var(--font-mono);
    white-space: pre-wrap;
}
```

### ✅ Statistics Dashboard Pattern
**Pattern**: Show key metrics in grid layout with large numbers.

**Implementation**:
- 2rem font size for numbers
- Color-coded (blue for neutral, green for success, red for errors)
- Grid layout (4 columns on desktop, 2 on mobile)
- Clear labels with uppercase + letter-spacing

**Example**: Preview modal statistics (total files, will rename, will skip, errors)

### ✅ Semantic Button Colors
**Pattern**: Use consistent color scheme for button actions.

**Colors**:
- **Primary** (blue `#6366f1`) - Main positive actions (Rename, Execute, Save)
- **Secondary** (gray) - Auxiliary actions (Cancel, Back, Browse)
- **Danger** (red `#ef4444`) - Destructive actions (Delete, Force, Cancel Operation)
- **Warning** (orange `#f59e0b`) - Caution actions (Skip, Override)
- **Success** (green `#10b981`) - Confirmation actions (Done, Confirm)

---

## Testing Strategy

### ✅ TDD Approach
**Pattern**: Write tests BEFORE implementing features.

**Process**:
1. Write failing test that describes desired behavior
2. Implement minimum code to make test pass
3. Refactor while keeping tests green
4. Repeat

**Benefits**:
- Forces clear thinking about API design
- Prevents over-engineering
- Catches regressions immediately
- Makes refactoring safe

**Status**: 285 tests passing (100% coverage)

### ⚠️ TODO: Web UI Testing
**Gap**: No automated tests for JavaScript frontend yet.

**Recommendation**: Add integration tests with:
- Playwright or Cypress for E2E testing
- Mock API responses for isolated testing
- Test critical flows: file loading, preview, rename execution
- Test error handling and edge cases

---

## Common Pitfalls & Solutions

### ❌ Don't Block Event Loop
**Problem**: Using `await worker.wait()` in Textual TUI blocked asyncio event loop.

**Solution**: Use `run_worker(thread=True)` or `run_in_thread()` for blocking operations.

**Context**: Textual runs on asyncio. Blocking operations (like file I/O) must run in threads.

### ❌ Don't Use Relative Paths in Web API
**Problem**: Frontend might send `~/Music` which backend can't resolve.

**Solution**: Always `expanduser()` and `resolve()` paths on backend:
```python
path = Path(request.path).expanduser().resolve()
```

### ❌ Don't Forget CORS for Development
**Problem**: Frontend can't call API due to CORS errors during development.

**Solution**: Add CORS middleware to FastAPI:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### ❌ Don't Serialize Path Objects Directly
**Problem**: `json.dumps()` can't serialize `pathlib.Path` objects.

**Solution**: Convert to strings in `to_dict()` methods:
```python
def to_dict(self) -> dict:
    return {
        "src": str(self.src),  # Convert Path to string
        "dst": str(self.dst) if self.dst else None,
    }
```

---

## File Organization

### Project Structure
```
batch_rename/
├── dj_mp3_renamer/          # Core Python package
│   ├── api/                 # API layer (RenamerAPI)
│   ├── core/                # Business logic
│   ├── tui/                 # Textual TUI
│   └── cli/                 # Click CLI
├── web/                     # FastAPI web application
│   ├── main.py             # API endpoints
│   └── static/             # Frontend files
│       ├── index.html      # Main HTML
│       ├── css/styles.css  # Styling
│       └── js/             # JavaScript
│           ├── api.js      # API client
│           ├── ui.js       # UI utilities
│           └── app.js      # Main app logic
├── tests/                   # Test suite
├── claude/                  # Knowledge base (this file!)
└── scripts/                 # Utility scripts
```

### Naming Conventions
- **Python**: `snake_case` for everything (functions, variables, files)
- **JavaScript**: `camelCase` for functions/variables, `PascalCase` for classes
- **CSS**: `kebab-case` for class names, `--kebab-case` for CSS variables
- **HTML**: `kebab-case` for IDs and attributes

---

## Dependencies & Versions

### Critical Dependencies
- **FastAPI**: Web framework for Python APIs
- **Pydantic**: Data validation and serialization
- **Textual**: Terminal UI framework
- **Click**: CLI framework
- **mutagen**: MP3 tag reading/writing
- **librosa**: Audio analysis (BPM/key detection)
- **acoustid**: MusicBrainz fingerprinting

### Version Pinning
**Lesson**: Pin major versions in `pyproject.toml` to prevent breaking changes.

Example:
```toml
[tool.poetry.dependencies]
python = "^3.10"
fastapi = "^0.109.0"
textual = "^0.48.0"
```

---

## Development Workflow

### Quick Reference Commands

**Start Web UI**:
```bash
./start_web_ui.sh  # Auto-finds available port, prevents duplicates
```

**Stop Web UI**:
```bash
./stop_web_ui.sh  # Uses PID file for clean shutdown
```

**Run Tests**:
```bash
pytest tests/ -v --cov=dj_mp3_renamer --cov-report=html
```

**Start TUI**:
```bash
python -m dj_mp3_renamer.tui
```

**CLI Usage**:
```bash
dj-rename --help
dj-rename /path/to/music --preview
dj-rename /path/to/music --auto-detect --recursive
```

---

## Performance Considerations

### Metadata Loading
- **Fast**: Read ID3 tags (~5ms per file)
- **Medium**: MusicBrainz lookup (~500ms per file, network I/O)
- **Slow**: AI audio analysis (~2-5 seconds per file, CPU intensive)

**Recommendation**:
- Use ID3 tags for preview (instant)
- Use MusicBrainz + AI only for final rename
- Show progress bar for long operations

### Concurrent Processing
- Use ThreadPoolExecutor for I/O-bound operations (file reading, network requests)
- Current setting: 2 workers (web), 4 workers (CLI/TUI)
- More workers = faster but more memory/CPU

---

## Future Improvements

### TODO List
1. **Add E2E tests for web UI** (Playwright/Cypress)
2. **Implement template editor in web UI** (live preview, validation)
3. **Add batch template testing** (test template on multiple files)
4. **Implement undo functionality** (save rename history, allow rollback)
5. **Add file filtering** (by artist, BPM range, key, etc.)
6. **Implement drag-and-drop** for file selection
7. **Add keyboard shortcuts** (Ctrl+A select all, Enter to confirm, etc.)
8. **Implement settings persistence** (save user preferences to config file)

---

## Commit Message Standards

### Format
```
<type>: <subject>

<body>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **refactor**: Code restructuring without behavior change
- **docs**: Documentation changes
- **test**: Adding or updating tests
- **chore**: Maintenance tasks (dependencies, scripts, etc.)
- **style**: Code style changes (formatting, naming)

### Example
```
feat: Add preview modal with metadata source indicators

- Created preview modal UI with statistics display
- Added metadata source badges (ID3/MusicBrainz/AI)
- Implemented async rename with progress tracking
- Added terminal-style output for technical users

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## Contact & Resources

- **Project Repository**: (Add GitHub URL here)
- **Documentation**: `./docs/`
- **API Reference**: Run server and visit `/docs` (FastAPI auto-generated)
- **Issue Tracker**: (Add issue tracker URL here)

---

**Last Updated**: 2026-01-29
**Maintainer**: szenone + Claude Sonnet 4.5
**Version**: 1.0.0 (Checkpoint 2 Complete)
