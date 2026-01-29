# API Architecture Review - DJ MP3 Renamer

**Date**: 2026-01-28
**Reviewer**: Claude Sonnet 4.5
**Review Type**: Comprehensive Architecture Analysis
**Focus**: Web UI Readiness Assessment

---

## EXECUTIVE SUMMARY

### Overall Assessment

**API Health**: ⭐⭐⭐⭐☆ **GOOD** (4/5)

The current API architecture is well-designed, follows API-First principles, and provides solid foundation for the application. The API is clean, well-typed, and properly separated from UI concerns.

### Key Findings

**Strengths** ✅
- Clean API-First architecture (UI layers don't access core modules directly)
- Well-defined data models with type hints
- Thread-safe concurrent processing with ReservationBook
- Good error handling and logging
- Proper separation of concerns
- Progress callback mechanism for real-time updates
- Cancellation support via exception pattern

**Gaps** ⚠️
- **No async operation support** (blocking synchronous calls only)
- **No status polling mechanism** (web UI needs to poll for progress)
- **No thread-safe cancel method** (exception pattern not web-friendly)
- **No file list preview API** (can't show files before renaming)
- **Config management not exposed** (web UI can't get/set config)
- **No template validation API** (web UI can't validate before running)

### Readiness for Web UI

**Status**: 🟡 **NEEDS WORK** (Moderate Gaps)

The API provides core functionality but lacks several features critical for modern web UI:
- **Async operations**: Web UI needs non-blocking calls with polling
- **Cancellation**: Need proper cancel() method, not exception-based
- **Preview**: Need to show file list before executing
- **Config access**: Web UI needs to read/write settings

**Estimated Effort to Close Gaps**: 4-6 hours

### Recommendation

**Proceed with API enhancements** before web UI implementation. The gaps are well-defined and solutions are straightforward. No major refactoring needed.

---

## CURRENT API SURFACE

### Primary API Class: `RenamerAPI`

Location: `dj_mp3_renamer/api/renamer.py`

#### Constructor

```python
def __init__(self, workers: int = 4, logger: Optional[logging.Logger] = None)
```

**Purpose**: Initialize API with thread pool and logger

**Parameters**:
- `workers`: Number of concurrent processing threads (default: 4)
- `logger`: Optional logger instance (creates one if not provided)

**State Management**:
- `self.workers`: Thread pool size
- `self.logger`: Logger instance
- `self.config`: Loaded from config file (via `load_config()`)

---

#### Public Method: `rename_files()`

```python
def rename_files(self, request: RenameRequest) -> RenameStatus
```

**Purpose**: Execute batch rename operation

**Input**: `RenameRequest`
- `path`: Path to file or directory
- `recursive`: Search subdirectories (default: False)
- `dry_run`: Preview mode without actual changes (default: False)
- `template`: Filename template (default: None, uses config default)
- `auto_detect`: Auto-detect missing BPM/Key (default: True)
- `progress_callback`: Callable for progress updates (default: None)

**Output**: `RenameStatus`
- `total`: Total files found
- `renamed`: Successfully renamed count
- `skipped`: Skipped files count
- `errors`: Error count
- `results`: List[RenameResult] with per-file details

**Behavior**:
- **Synchronous**: Blocks until operation complete
- **Thread-safe**: Uses ReservationBook for collision detection
- **Cancellable**: Via exception in progress_callback
- **Progress updates**: Via progress_callback(count, filename)
- **Error handling**: Returns errors in results, doesn't crash

**Limitations for Web UI**:
- ❌ Blocks calling thread (can't poll for status)
- ❌ Cancellation via exception not web-friendly
- ❌ No operation ID for tracking
- ❌ Can't query intermediate state

---

#### Private Method: `_rename_one()` (Internal)

```python
def _rename_one(
    self,
    src: Path,
    dry_run: bool,
    template: str,
    book: ReservationBook,
    auto_detect: bool,
) -> RenameResult
```

**Purpose**: Process single file (called by thread pool workers)

**Not Exposed**: Internal implementation detail

---

#### Private Method: `_enhance_metadata()` (Internal)

```python
def _enhance_metadata(self, src: Path, meta: dict) -> dict
```

**Purpose**: Enhance metadata using MusicBrainz + AI analysis

**Features**:
- MusicBrainz lookup via AcoustID
- AI audio analysis (BPM/Key detection)
- Conflict resolution between sources
- Write enhanced data back to ID3 tags

**Not Exposed**: Internal implementation detail

**Potential API Gap**: Web UI might want to enhance metadata separately without renaming

---

#### Private Method: `_derive_target()` (Internal)

```python
def _derive_target(
    self,
    src: Path,
    template: str,
    book: ReservationBook,
    auto_detect: bool,
) -> Tuple[Optional[Path], Optional[str], Optional[dict]]
```

**Purpose**: Calculate target filename for a source file

**Not Exposed**: Internal implementation detail

**Potential API Gap**: Web UI needs this for preview (show old → new names)

---

### Data Models

Location: `dj_mp3_renamer/api/models.py`

#### `RenameRequest` (frozen dataclass)

```python
@dataclass(frozen=True)
class RenameRequest:
    path: Path
    recursive: bool = False
    dry_run: bool = False
    template: Optional[str] = None
    auto_detect: bool = True
    progress_callback: Optional[Callable[[int, str], None]] = None
```

**Quality**: ✅ Well-defined, typed, immutable

**Serializable**: ⚠️ Not JSON-serializable (Path, Callable)
- For web API, need to convert Path → str
- progress_callback not serializable (use WebSocket/SSE instead)

---

#### `RenameResult` (frozen dataclass)

```python
@dataclass(frozen=True)
class RenameResult:
    src: Path
    dst: Optional[Path]
    status: str  # "renamed" | "skipped" | "error"
    message: Optional[str] = None
    metadata: Optional[dict[str, str]] = None
```

**Quality**: ✅ Well-defined, typed, immutable

**Serializable**: ⚠️ Not JSON-serializable (Path objects)

**Suggestion**: Add `to_dict()` method for JSON serialization

---

#### `RenameStatus` (frozen dataclass)

```python
@dataclass(frozen=True)
class RenameStatus:
    total: int
    renamed: int
    skipped: int
    errors: int
    results: list[RenameResult]
```

**Quality**: ✅ Well-defined, typed, immutable

**Serializable**: ⚠️ Not JSON-serializable (contains RenameResult with Path)

---

### Config Module (Not Exposed via API)

Location: `dj_mp3_renamer/core/config.py`

**Functions Available** (but not through RenamerAPI):
- `load_config() -> Dict[str, Any]`
- `save_config(config: Dict[str, Any]) -> bool`
- `get_config_value(key: str, default: Any) -> Any`
- `set_config_value(key: str, value: Any) -> bool`
- `clear_config_cache() -> None`

**API Gap**: Config management not accessible via RenamerAPI

**Impact**: Web UI needs to:
- Show current settings
- Allow users to change settings
- Validate settings before saving

**Recommendation**: Expose config operations via RenamerAPI

---

## GAP ANALYSIS

### GAP 1: No Async Operation Support

**Severity**: 🔴 **HIGH** (Blocking for Web UI)

**Current Behavior**:
- `rename_files()` is synchronous, blocks until complete
- Web UI can't do anything else during operation
- Can't poll for intermediate status

**Web UI Requirements**:
- Start operation, get operation ID
- Poll for status updates (every 500ms)
- Continue UI responsiveness
- Show progress dialog with cancel button

**Impact**:
- Web UI can't show progress dialog
- Browser may timeout on large batches
- Poor UX (UI frozen during operation)

**Workaround**: None (fundamental limitation)

**Recommended Solution**:

```python
class RenamerAPI:
    def __init__(self, ...):
        self._operations = {}  # Track running operations
        self._lock = threading.Lock()

    def start_rename_async(self, request: RenameRequest) -> str:
        """
        Start rename operation asynchronously.

        Returns:
            operation_id: UUID for tracking
        """
        operation_id = str(uuid.uuid4())

        # Start operation in background thread
        thread = threading.Thread(
            target=self._run_operation,
            args=(operation_id, request),
            daemon=True
        )

        with self._lock:
            self._operations[operation_id] = {
                "status": "running",
                "progress": 0,
                "total": 0,
                "current_file": "",
                "thread": thread,
                "start_time": time.time(),
                "results": None,
                "cancelled": False,
            }

        thread.start()
        return operation_id

    def get_operation_status(self, operation_id: str) -> Optional[OperationStatus]:
        """
        Get status of running/completed operation.

        Returns:
            OperationStatus or None if not found
        """
        with self._lock:
            if operation_id not in self._operations:
                return None
            return OperationStatus(**self._operations[operation_id])

    def cancel_operation(self, operation_id: str) -> bool:
        """
        Cancel running operation.

        Returns:
            True if cancelled, False if not found/already complete
        """
        with self._lock:
            if operation_id not in self._operations:
                return False
            self._operations[operation_id]["cancelled"] = True
            return True
```

**Estimated Effort**: 3-4 hours

---

### GAP 2: No Thread-Safe Cancel Method

**Severity**: 🔴 **HIGH** (Blocking for Web UI)

**Current Behavior**:
- Cancellation via exception in `progress_callback`
- Web UI would need to: start operation → wait → raise exception
- Not suitable for HTTP request/response pattern

**Web UI Requirements**:
- User clicks "Cancel" button
- Web UI sends `POST /api/operations/{id}/cancel`
- Operation stops gracefully
- Returns partial results

**Impact**:
- Can't implement cancel button in web UI
- No clean cancellation API

**Workaround**: None

**Recommended Solution**: See GAP 1 (`cancel_operation()` method)

**Estimated Effort**: Included in GAP 1 (same implementation)

---

### GAP 3: No File List Preview API

**Severity**: 🟡 **MEDIUM** (Important for UX)

**Current Behavior**:
- Must run full operation (dry_run=True) to see what would happen
- Can't just get list of files with old → new names
- No way to validate before executing

**Web UI Requirements**:
- User selects directory
- Web UI shows table: "These files will be renamed"
- Columns: Current Name | New Name | Status | Conflicts
- User reviews and clicks "Rename" to proceed

**Impact**:
- Can't show preview table before confirming
- Must run dry-run, then run again for real (slow)

**Workaround**: Run with `dry_run=True`, parse results, show UI, run again with `dry_run=False`

**Recommended Solution**:

```python
@dataclass
class FilePreview:
    """Preview of a file rename operation."""
    src: Path
    dst: Path
    status: str  # "will_rename" | "will_skip" | "error"
    reason: Optional[str] = None
    metadata: Optional[dict] = None

class RenamerAPI:
    def preview_rename(self, request: RenameRequest) -> List[FilePreview]:
        """
        Preview rename operation without executing.

        Returns:
            List of FilePreview objects showing old → new names
        """
        # Find files
        mp3s = find_mp3s(request.path, recursive=request.recursive)

        # Calculate targets for each
        previews = []
        book = ReservationBook()
        template = request.template or DEFAULT_TEMPLATE

        for src in mp3s:
            dst, reason, meta = self._derive_target(
                src, template, book, auto_detect=False  # No analysis for preview
            )
            if dst:
                previews.append(FilePreview(src, dst, "will_rename", metadata=meta))
            else:
                previews.append(FilePreview(src, src, "will_skip", reason, meta))

        return previews
```

**Estimated Effort**: 1-2 hours

---

### GAP 4: Config Management Not Exposed

**Severity**: 🟡 **MEDIUM** (Important for Settings UI)

**Current Behavior**:
- Config loaded in `__init__`, stored in `self.config`
- No methods to get/set config via API
- Web UI can't access settings

**Web UI Requirements**:
- Settings page showing all config options
- User can change settings
- Validate settings before saving
- Apply settings immediately

**Impact**:
- Can't build settings UI
- Must directly import `core.config` (bypasses API)

**Workaround**: Import `dj_mp3_renamer.core.config` directly (breaks API-First)

**Recommended Solution**:

```python
class RenamerAPI:
    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration.

        Returns:
            Config dictionary with all settings
        """
        return load_config()

    def update_config(self, updates: Dict[str, Any]) -> bool:
        """
        Update configuration values.

        Args:
            updates: Dictionary of key-value pairs to update

        Returns:
            True if successful, False otherwise
        """
        config = load_config()
        config.update(updates)
        success = save_config(config)
        if success:
            self.config = config  # Update instance config
        return success

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get single config value."""
        return self.config.get(key, default)

    def set_config_value(self, key: str, value: Any) -> bool:
        """Set single config value."""
        self.config[key] = value
        return save_config(self.config)
```

**Estimated Effort**: 1 hour

---

### GAP 5: No Template Validation API

**Severity**: 🟢 **LOW** (Nice to Have)

**Current Behavior**:
- Template validation happens during rename
- If template invalid, error occurs mid-operation
- No way to validate template before using it

**Web UI Requirements**:
- User enters custom template
- Web UI validates template in real-time
- Shows error if template invalid
- Shows example output with sample metadata

**Impact**:
- Can't provide real-time validation feedback
- User discovers errors during operation

**Workaround**: Client-side validation with regex (limited)

**Recommended Solution**:

```python
@dataclass
class TemplateValidation:
    """Result of template validation."""
    valid: bool
    errors: List[str]
    example: Optional[str] = None  # Example output with sample data

class RenamerAPI:
    def validate_template(self, template: str) -> TemplateValidation:
        """
        Validate filename template.

        Args:
            template: Template string to validate

        Returns:
            TemplateValidation with errors and example
        """
        errors = []

        # Check for invalid characters
        if any(c in template for c in r'\/:*?"<>|'):
            errors.append("Template contains invalid filename characters")

        # Try to expand with sample data
        sample_meta = {
            "artist": "Sample Artist",
            "title": "Sample Title",
            "bpm": "128",
            "key": "Am",
            "camelot": "8A",
        }

        try:
            tokens = build_default_components(sample_meta)
            example = build_filename_from_template(tokens, template)
        except Exception as e:
            errors.append(f"Template expansion error: {e}")
            example = None

        return TemplateValidation(
            valid=len(errors) == 0,
            errors=errors,
            example=example
        )
```

**Estimated Effort**: 1 hour

---

### GAP 6: No Metadata Enhancement API (Standalone)

**Severity**: 🟢 **LOW** (Nice to Have)

**Current Behavior**:
- `_enhance_metadata()` is private, only called during rename
- Can't enhance metadata without renaming file

**Web UI Requirements** (Future):
- "Analyze Metadata" button for single file
- Show BPM/Key detection results before renaming
- Let user correct metadata manually

**Impact**:
- Can't provide standalone metadata enhancement
- Limited to rename workflow only

**Workaround**: Run dry-run rename to get enhanced metadata

**Recommended Solution**:

```python
class RenamerAPI:
    def analyze_file(self, file_path: Path) -> Optional[dict]:
        """
        Analyze single file metadata.

        Returns:
            Enhanced metadata dict or None if error
        """
        meta, err = read_mp3_metadata(file_path, self.logger)
        if err:
            return None

        # Enhance with MusicBrainz + AI
        enhanced = self._enhance_metadata(file_path, meta)
        return enhanced
```

**Estimated Effort**: 30 minutes (method already exists, just expose it)

---

## API DESIGN EVALUATION

### Strengths ✅

1. **Clean Separation of Concerns**
   - API layer orchestrates core modules
   - UI layers (TUI, CLI) only use API
   - No business logic in UI

2. **Well-Typed**
   - Type hints on all public methods
   - Immutable dataclasses for models
   - Good IDE support

3. **Thread-Safe**
   - ReservationBook prevents filename collisions
   - ThreadPoolExecutor for concurrent processing
   - Proper locking where needed

4. **Error Handling**
   - Errors captured, not crashing
   - Detailed error messages
   - Proper logging throughout

5. **Extensible Design**
   - Easy to add new methods
   - Config-driven behavior
   - Plugin-friendly architecture

6. **Progress Tracking**
   - progress_callback for real-time updates
   - Responsive cancellation (100ms polling)
   - Detailed per-file results

### Weaknesses ⚠️

1. **Synchronous Only**
   - No async operation support
   - Blocks calling thread
   - Not web-friendly

2. **Limited Observability**
   - Can't query operation status mid-run
   - No operation history
   - No metrics/telemetry

3. **Exception-Based Cancellation**
   - Not suitable for HTTP APIs
   - Requires callback pattern
   - Not thread-safe from outside

4. **No Serialization Support**
   - Models use Path objects (not JSON-friendly)
   - No `to_dict()` methods
   - Must manually convert for HTTP

5. **Config Not Exposed**
   - Config management bypasses API
   - UI must import core modules directly
   - Breaks API-First principle

### Compliance with API-First Principles

**Score**: 🟢🟢🟢🟢⚪ **4/5** (Good)

✅ **Followed**:
- All business logic in API layer
- UI layers are thin wrappers
- Clean interfaces with type hints
- No direct core module access from UI

⚠️ **Needs Improvement**:
- Config management not exposed
- Some operations (preview, validate) missing
- Not optimized for HTTP/REST pattern

---

## RECOMMENDATIONS SUMMARY

### Priority 1: HIGH (Blocking Web UI)

1. **Add Async Operation Support** (3-4 hours)
   - `start_rename_async()` → operation_id
   - `get_operation_status()` → OperationStatus
   - `cancel_operation()` → bool

2. **Add Thread-Safe Cancellation** (Included in #1)

### Priority 2: MEDIUM (Important for UX)

3. **Add File List Preview API** (1-2 hours)
   - `preview_rename()` → List[FilePreview]

4. **Expose Config Management** (1 hour)
   - `get_config()` → Dict
   - `update_config()` → bool
   - `get_config_value()` → Any
   - `set_config_value()` → bool

### Priority 3: LOW (Nice to Have)

5. **Add Template Validation** (1 hour)
   - `validate_template()` → TemplateValidation

6. **Expose Metadata Enhancement** (30 min)
   - `analyze_file()` → dict

### Priority 4: FUTURE (Post Web UI)

7. **Add JSON Serialization**
   - Add `to_dict()` methods to all models
   - Support Path → str conversion
   - Enable HTTP API easily

8. **Add Operation History**
   - Track completed operations
   - Allow querying past results
   - Useful for debugging/audit

---

## CONCLUSION

The current API architecture is **solid and well-designed**, following API-First principles effectively. The gaps identified are **well-scoped and addressable** without major refactoring.

### Next Steps

1. ✅ **Accept Review**: Current API design is good
2. ⚠️ **Address High Priority Gaps**: Async operations + cancellation (3-4 hours)
3. 🟡 **Address Medium Priority Gaps**: Preview + config (2-3 hours)
4. ✅ **Proceed to Web UI**: After high+medium gaps closed

**Total Effort to Web UI Ready**: 5-7 hours

The API will be **fully ready for web UI** after addressing the high and medium priority gaps. The architecture is sound and no major redesign is needed.

---

**Review Complete**: 2026-01-28
**Reviewer**: Claude Sonnet 4.5
**Next Task**: C2 - Create API Enhancement Backlog
