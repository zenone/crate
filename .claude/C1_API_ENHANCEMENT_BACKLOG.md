# API Enhancement Backlog

**Date**: 2026-01-28
**Based On**: C1 API Architecture Review
**Purpose**: Track API improvements needed for web UI

---

## BACKLOG OVERVIEW

**Total Enhancements**: 8
**High Priority**: 2 (blocking web UI)
**Medium Priority**: 2 (important for UX)
**Low Priority**: 2 (nice to have)
**Future**: 2 (post web UI)

**Estimated Total Effort**: 5-7 hours for web UI readiness

---

## HIGH PRIORITY (Blocking Web UI)

### ENH-001: Add Async Operation Support

**Priority**: 🔴 **CRITICAL** (Blocks Web UI)
**Estimate**: 3-4 hours
**Complexity**: Medium
**Impact**: Critical for web UI polling pattern

**Description**:
Add support for asynchronous operations with operation IDs, enabling web UI to:
- Start operation and continue UI responsiveness
- Poll for status updates (every 500ms)
- Show progress dialog with real-time updates
- Handle long-running operations without browser timeout

**Files to Modify**:
- `dj_mp3_renamer/api/renamer.py` - Add async methods
- `dj_mp3_renamer/api/models.py` - Add OperationStatus model

**Implementation**:

```python
# models.py
@dataclass(frozen=True)
class OperationStatus:
    """Status of an async operation."""
    operation_id: str
    status: str  # "running" | "completed" | "cancelled" | "error"
    progress: int  # Files processed
    total: int  # Total files
    current_file: str  # Currently processing
    start_time: float  # Unix timestamp
    end_time: Optional[float] = None
    results: Optional[RenameStatus] = None
    error: Optional[str] = None

# renamer.py
class RenamerAPI:
    def __init__(self, workers: int = 4, logger: Optional[logging.Logger] = None):
        self.workers = max(1, workers)
        self.logger = logger or logging.getLogger("dj_mp3_renamer")
        self.config = load_config()
        self._operations = {}  # Track operations
        self._lock = threading.Lock()  # Thread safety

    def start_rename_async(self, request: RenameRequest) -> str:
        """
        Start rename operation asynchronously.

        Returns:
            operation_id: UUID for tracking
        """
        operation_id = str(uuid.uuid4())

        # Create operation state
        with self._lock:
            self._operations[operation_id] = {
                "status": "running",
                "progress": 0,
                "total": 0,
                "current_file": "",
                "start_time": time.time(),
                "end_time": None,
                "results": None,
                "error": None,
                "cancelled": False,
            }

        # Start operation in background thread
        thread = threading.Thread(
            target=self._run_operation_async,
            args=(operation_id, request),
            daemon=True,
            name=f"rename-{operation_id[:8]}"
        )
        thread.start()

        return operation_id

    def _run_operation_async(self, operation_id: str, request: RenameRequest):
        """Run operation asynchronously, updating state."""
        def progress_callback(count, filename):
            with self._lock:
                if self._operations[operation_id]["cancelled"]:
                    raise OperationCancelled("User cancelled")
                self._operations[operation_id]["progress"] = count
                self._operations[operation_id]["current_file"] = filename

        # Create modified request with our progress callback
        async_request = RenameRequest(
            path=request.path,
            recursive=request.recursive,
            dry_run=request.dry_run,
            template=request.template,
            auto_detect=request.auto_detect,
            progress_callback=progress_callback
        )

        try:
            # Run the operation
            results = self.rename_files(async_request)

            # Update state with results
            with self._lock:
                self._operations[operation_id]["status"] = "completed"
                self._operations[operation_id]["end_time"] = time.time()
                self._operations[operation_id]["results"] = results

        except OperationCancelled:
            with self._lock:
                self._operations[operation_id]["status"] = "cancelled"
                self._operations[operation_id]["end_time"] = time.time()

        except Exception as e:
            self.logger.error(f"Async operation {operation_id} failed: {e}", exc_info=True)
            with self._lock:
                self._operations[operation_id]["status"] = "error"
                self._operations[operation_id]["end_time"] = time.time()
                self._operations[operation_id]["error"] = str(e)

    def get_operation_status(self, operation_id: str) -> Optional[OperationStatus]:
        """
        Get status of operation.

        Args:
            operation_id: Operation ID from start_rename_async()

        Returns:
            OperationStatus or None if not found
        """
        with self._lock:
            if operation_id not in self._operations:
                return None

            op = self._operations[operation_id]
            return OperationStatus(
                operation_id=operation_id,
                status=op["status"],
                progress=op["progress"],
                total=op["total"],
                current_file=op["current_file"],
                start_time=op["start_time"],
                end_time=op["end_time"],
                results=op["results"],
                error=op["error"]
            )

    def cancel_operation(self, operation_id: str) -> bool:
        """
        Cancel running operation.

        Args:
            operation_id: Operation ID to cancel

        Returns:
            True if cancelled, False if not found/already complete
        """
        with self._lock:
            if operation_id not in self._operations:
                return False

            op = self._operations[operation_id]
            if op["status"] != "running":
                return False  # Already complete

            op["cancelled"] = True
            self.logger.info(f"Operation {operation_id} marked for cancellation")
            return True

    def clear_operation(self, operation_id: str) -> bool:
        """
        Remove operation from tracking (cleanup).

        Args:
            operation_id: Operation ID to remove

        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if operation_id in self._operations:
                del self._operations[operation_id]
                return True
            return False

class OperationCancelled(Exception):
    """Raised when operation is cancelled."""
    pass
```

**Tests to Add**:
- Test async operation starts and completes
- Test status polling during operation
- Test cancellation mid-operation
- Test error handling in async mode
- Test concurrent operations

**Acceptance Criteria**:
- [ ] `start_rename_async()` returns operation ID
- [ ] `get_operation_status()` returns current status
- [ ] `cancel_operation()` stops running operation
- [ ] Operation state tracked correctly
- [ ] Thread-safe with proper locking
- [ ] 5+ tests passing

---

### ENH-002: Add Thread-Safe Cancellation

**Priority**: 🔴 **CRITICAL** (Blocks Web UI)
**Estimate**: Included in ENH-001
**Complexity**: Low (part of ENH-001)
**Impact**: Critical for cancel button in web UI

**Description**:
Implement `cancel_operation()` method for thread-safe cancellation. Current exception-based cancellation via progress_callback is not web-friendly.

**Note**: This enhancement is **implemented as part of ENH-001**. No separate work needed.

**Acceptance Criteria**:
- [ ] `cancel_operation(operation_id)` method exists
- [ ] Cancellation is thread-safe
- [ ] Operation stops within reasonable time (<1s)
- [ ] Partial results are preserved

---

## MEDIUM PRIORITY (Important for UX)

### ENH-003: Add File List Preview API

**Priority**: 🟡 **HIGH** (Important for UX)
**Estimate**: 1-2 hours
**Complexity**: Low
**Impact**: Better UX (show files before renaming)

**Description**:
Add `preview_rename()` method to show what files would be renamed without executing. Enables web UI to:
- Show "These files will be renamed" table
- Display old → new names before confirming
- Identify potential issues before running

**Files to Modify**:
- `dj_mp3_renamer/api/renamer.py` - Add preview_rename()
- `dj_mp3_renamer/api/models.py` - Add FilePreview model

**Implementation**:

```python
# models.py
@dataclass(frozen=True)
class FilePreview:
    """Preview of a file rename operation."""
    src: Path
    dst: Optional[Path]
    status: str  # "will_rename" | "will_skip" | "error"
    reason: Optional[str] = None
    metadata: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "src": str(self.src),
            "dst": str(self.dst) if self.dst else None,
            "status": self.status,
            "reason": self.reason,
            "metadata": self.metadata
        }

# renamer.py
class RenamerAPI:
    def preview_rename(self, request: RenameRequest) -> list[FilePreview]:
        """
        Preview rename operation without executing.

        Args:
            request: RenameRequest (dry_run ignored)

        Returns:
            List of FilePreview objects showing old → new names
        """
        target = request.path.expanduser().resolve()

        if not target.exists():
            return []

        # Find MP3 files
        if target.is_file():
            mp3s = [target] if target.suffix.lower() == ".mp3" else []
        else:
            mp3s = find_mp3s(target, recursive=request.recursive)

        if not mp3s:
            return []

        # Calculate targets for each file
        previews = []
        book = ReservationBook()
        template = request.template or DEFAULT_TEMPLATE

        for src in mp3s:
            try:
                dst, reason, meta = self._derive_target(
                    src, template, book,
                    auto_detect=False  # No expensive analysis for preview
                )

                if dst:
                    previews.append(FilePreview(
                        src=src,
                        dst=dst,
                        status="will_rename",
                        metadata=meta
                    ))
                else:
                    previews.append(FilePreview(
                        src=src,
                        dst=None,
                        status="will_skip",
                        reason=reason,
                        metadata=meta
                    ))

            except Exception as e:
                previews.append(FilePreview(
                    src=src,
                    dst=None,
                    status="error",
                    reason=str(e),
                    metadata=None
                ))

        return previews
```

**Tests to Add**:
- Test preview returns correct file list
- Test preview shows old → new names
- Test preview identifies skips
- Test preview handles errors gracefully
- Test preview is fast (no analysis)

**Acceptance Criteria**:
- [ ] `preview_rename()` returns list of previews
- [ ] Preview shows src, dst, status, reason
- [ ] No actual file operations performed
- [ ] Fast execution (no audio analysis)
- [ ] 3+ tests passing

---

### ENH-004: Expose Config Management

**Priority**: 🟡 **HIGH** (Important for Settings UI)
**Estimate**: 1 hour
**Complexity**: Low
**Impact**: Enable settings page in web UI

**Description**:
Expose config management operations via RenamerAPI. Currently config functions are in `core.config` but not accessible via API, forcing UI to bypass API layer.

**Files to Modify**:
- `dj_mp3_renamer/api/renamer.py` - Add config methods

**Implementation**:

```python
class RenamerAPI:
    def get_config(self) -> dict[str, Any]:
        """
        Get current configuration.

        Returns:
            Config dictionary with all settings
        """
        return load_config()

    def update_config(self, updates: dict[str, Any]) -> bool:
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
            clear_config_cache()  # Ensure fresh load next time
        return success

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get single configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def set_config_value(self, key: str, value: Any) -> bool:
        """
        Set single configuration value.

        Args:
            key: Configuration key
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        self.config[key] = value
        success = save_config(self.config)
        if success:
            clear_config_cache()
        return success

    def get_default_config(self) -> dict[str, Any]:
        """
        Get default configuration values.

        Returns:
            Default config dictionary
        """
        from ..core.config import DEFAULT_CONFIG
        return DEFAULT_CONFIG.copy()
```

**Tests to Add**:
- Test get_config() returns current config
- Test update_config() persists changes
- Test get_config_value() returns value
- Test set_config_value() updates config
- Test config changes affect operations

**Acceptance Criteria**:
- [ ] All config operations accessible via API
- [ ] Config changes persist correctly
- [ ] No need to import `core.config` from UI
- [ ] 5+ tests passing

---

## LOW PRIORITY (Nice to Have)

### ENH-005: Add Template Validation API

**Priority**: 🟢 **MEDIUM** (Nice to Have)
**Estimate**: 1 hour
**Complexity**: Low
**Impact**: Better UX (real-time template validation)

**Description**:
Add `validate_template()` method to validate filename templates before using them. Enables web UI to:
- Show real-time validation errors
- Display example output with sample data
- Prevent errors during operation

**Files to Modify**:
- `dj_mp3_renamer/api/renamer.py` - Add validate_template()
- `dj_mp3_renamer/api/models.py` - Add TemplateValidation model

**Implementation**:

```python
# models.py
@dataclass(frozen=True)
class TemplateValidation:
    """Result of template validation."""
    valid: bool
    errors: list[str]
    warnings: list[str]
    example: Optional[str] = None

# renamer.py
class RenamerAPI:
    def validate_template(self, template: str) -> TemplateValidation:
        """
        Validate filename template.

        Args:
            template: Template string to validate

        Returns:
            TemplateValidation with errors, warnings, and example
        """
        errors = []
        warnings = []

        # Check for invalid filename characters
        invalid_chars = r'\/:*?"<>|'
        if any(c in template for c in invalid_chars):
            errors.append(f"Template contains invalid filename characters: {invalid_chars}")

        # Check for leading/trailing spaces (common mistake)
        if template.startswith(" ") or template.endswith(" "):
            warnings.append("Template has leading/trailing spaces")

        # Try to expand with sample data
        sample_meta = {
            "artist": "Sample Artist",
            "title": "Sample Title",
            "bpm": "128",
            "key": "Am",
            "camelot": "8A",
            "album": "Sample Album",
            "year": "2024",
            "label": "Sample Label",
            "mix": "Original Mix",
        }

        example = None
        try:
            tokens = build_default_components(sample_meta)
            expanded = build_filename_from_template(tokens, template)
            example = safe_filename(expanded)

            # Check if example is empty
            if not example or example.strip() == "":
                errors.append("Template produces empty filename")

        except KeyError as e:
            errors.append(f"Unknown template variable: {e}")
        except Exception as e:
            errors.append(f"Template expansion error: {e}")

        return TemplateValidation(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            example=example
        )
```

**Tests to Add**:
- Test valid template passes
- Test invalid characters detected
- Test invalid variables detected
- Test example output generated
- Test empty template handled

**Acceptance Criteria**:
- [ ] `validate_template()` detects invalid characters
- [ ] Returns helpful error messages
- [ ] Generates example output with sample data
- [ ] 3+ tests passing

---

### ENH-006: Expose Metadata Enhancement API

**Priority**: 🟢 **LOW** (Nice to Have)
**Estimate**: 30 minutes
**Complexity**: Very Low
**Impact**: Enable standalone metadata analysis

**Description**:
Expose `_enhance_metadata()` as public method `analyze_file()`. Enables web UI to:
- Show "Analyze Metadata" button for single file
- Display BPM/Key detection results
- Let user review before applying

**Files to Modify**:
- `dj_mp3_renamer/api/renamer.py` - Add analyze_file()

**Implementation**:

```python
class RenamerAPI:
    def analyze_file(self, file_path: Path) -> Optional[dict]:
        """
        Analyze single file metadata.

        Performs:
        - Read existing ID3 tags
        - MusicBrainz lookup (if enabled)
        - AI audio analysis (BPM/Key)
        - Conflict resolution

        Args:
            file_path: Path to MP3 file

        Returns:
            Enhanced metadata dict or None if error
        """
        # Read existing metadata
        meta, err = read_mp3_metadata(file_path, self.logger)
        if err:
            self.logger.error(f"Failed to read {file_path}: {err}")
            return None

        # Enhance with MusicBrainz + AI
        enhanced = self._enhance_metadata(file_path, meta)
        return enhanced
```

**Tests to Add**:
- Test analyze_file() returns enhanced metadata
- Test analyze_file() handles missing file
- Test analyze_file() handles corrupted file

**Acceptance Criteria**:
- [ ] `analyze_file()` exposes metadata enhancement
- [ ] Returns enhanced metadata dict
- [ ] Handles errors gracefully
- [ ] 2+ tests passing

---

## FUTURE (Post Web UI)

### ENH-007: Add JSON Serialization Support

**Priority**: ⚪ **LOW** (Future Enhancement)
**Estimate**: 2 hours
**Complexity**: Low
**Impact**: Easier HTTP API implementation

**Description**:
Add `to_dict()` and `from_dict()` methods to all data models for JSON serialization. Currently models use `Path` objects which aren't JSON-serializable.

**Files to Modify**:
- `dj_mp3_renamer/api/models.py` - Add serialization methods

**Implementation**:

```python
@dataclass(frozen=True)
class RenameRequest:
    # ... existing fields ...

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "path": str(self.path),
            "recursive": self.recursive,
            "dry_run": self.dry_run,
            "template": self.template,
            "auto_detect": self.auto_detect,
            # progress_callback omitted (not serializable)
        }

    @staticmethod
    def from_dict(data: dict) -> "RenameRequest":
        """Create from JSON dict."""
        return RenameRequest(
            path=Path(data["path"]),
            recursive=data.get("recursive", False),
            dry_run=data.get("dry_run", False),
            template=data.get("template"),
            auto_detect=data.get("auto_detect", True),
        )

# Similar for RenameResult, RenameStatus, etc.
```

**Acceptance Criteria**:
- [ ] All models have `to_dict()` method
- [ ] All models have `from_dict()` method
- [ ] Serialization is reversible
- [ ] 5+ tests passing

---

### ENH-008: Add Operation History

**Priority**: ⚪ **LOW** (Future Enhancement)
**Estimate**: 3 hours
**Complexity**: Medium
**Impact**: Audit trail and debugging

**Description**:
Track completed operations for history/audit trail. Useful for:
- Debugging issues ("what happened yesterday?")
- Audit trail (what files were renamed when)
- Undo/revert functionality (future)

**Files to Modify**:
- `dj_mp3_renamer/api/renamer.py` - Add history tracking
- `dj_mp3_renamer/api/models.py` - Add OperationHistory model

**Implementation**:

```python
@dataclass(frozen=True)
class OperationHistory:
    """Historical record of an operation."""
    operation_id: str
    timestamp: float
    request: RenameRequest
    status: RenameStatus
    duration: float  # seconds

class RenamerAPI:
    def __init__(self, ...):
        # ... existing ...
        self._history = []  # List of OperationHistory
        self._history_limit = 100  # Keep last 100

    def get_operation_history(
        self,
        limit: int = 10,
        offset: int = 0
    ) -> list[OperationHistory]:
        """
        Get operation history.

        Args:
            limit: Max records to return
            offset: Offset for pagination

        Returns:
            List of OperationHistory records
        """
        with self._lock:
            return self._history[offset:offset+limit]

    def get_operation_by_id(self, operation_id: str) -> Optional[OperationHistory]:
        """Get specific operation from history."""
        with self._lock:
            for op in self._history:
                if op.operation_id == operation_id:
                    return op
            return None
```

**Acceptance Criteria**:
- [ ] Completed operations stored in history
- [ ] History has reasonable limit (100 records)
- [ ] Can query history by ID
- [ ] Can paginate through history
- [ ] 3+ tests passing

---

## IMPLEMENTATION PLAN

### Phase 1: Web UI Readiness (5-7 hours)

**Critical Path**:
1. ✅ ENH-001: Async Operations (3-4 hours) - **REQUIRED**
2. ✅ ENH-003: File Preview (1-2 hours) - **HIGHLY RECOMMENDED**
3. ✅ ENH-004: Config Management (1 hour) - **HIGHLY RECOMMENDED**

**After Phase 1**: Web UI can be fully implemented

### Phase 2: UX Polish (1.5 hours)

**Nice to Have**:
4. ⚪ ENH-005: Template Validation (1 hour)
5. ⚪ ENH-006: Metadata Enhancement (30 min)

**After Phase 2**: Web UI has excellent UX

### Phase 3: Future Enhancements (5 hours)

**Future Work**:
6. ⚪ ENH-007: JSON Serialization (2 hours)
7. ⚪ ENH-008: Operation History (3 hours)

**After Phase 3**: Enterprise-grade API

---

## PROGRESS TRACKING

### Status
- **Total Enhancements**: 8
- **Completed**: 0
- **In Progress**: 0
- **Pending**: 8

### Next Steps
1. Review and approve backlog
2. Begin ENH-001 (Async Operations)
3. Test ENH-001 thoroughly
4. Proceed to ENH-003 and ENH-004
5. Web UI implementation

---

**Last Updated**: 2026-01-28
**Status**: Ready for Implementation
