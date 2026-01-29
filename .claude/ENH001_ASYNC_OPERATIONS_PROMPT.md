# ENH-001: Async Operation Support

**Date**: 2026-01-28
**Priority**: 🔴 **CRITICAL** (Blocks Web UI)
**Estimated**: 3-4 hours
**Based On**: C1 API Architecture Review
**TWO-PHASE**: This is the improved prompt (Phase 1)

---

## ENHANCEMENT OBJECTIVE

**Goal**: Add asynchronous operation support with operation IDs, enabling web UI to:
- Start rename operations without blocking
- Poll for status updates (every 500ms)
- Show progress dialog with real-time updates
- Cancel operations via dedicated API method
- Handle long-running operations without browser timeout

**Current Problem**:
- `rename_files()` is synchronous, blocks until complete
- Web UI can't poll for intermediate status
- Cancellation via exception not web-friendly
- Browser may timeout on large batches (100+ files)

**Target Solution**:
```python
# Web UI usage pattern
operation_id = api.start_rename_async(request)  # Returns immediately

# Poll every 500ms
while True:
    status = api.get_operation_status(operation_id)
    if status.status in ["completed", "cancelled", "error"]:
        break
    update_progress_dialog(status.progress, status.total, status.current_file)
    sleep(0.5)

# User clicks cancel
api.cancel_operation(operation_id)
```

---

## DESIGN SPECIFICATION

### Operation Lifecycle

```
START → RUNNING → COMPLETED
         ↓
      CANCELLED
         ↓
       ERROR
```

**States**:
- `running`: Operation in progress
- `completed`: Successfully finished
- `cancelled`: User cancelled
- `error`: Failed with error

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ RenamerAPI                                          │
├─────────────────────────────────────────────────────┤
│ _operations: Dict[str, OperationState]             │
│ _lock: threading.Lock                               │
├─────────────────────────────────────────────────────┤
│ + start_rename_async(request) -> str                │
│ + get_operation_status(id) -> OperationStatus      │
│ + cancel_operation(id) -> bool                      │
│ + clear_operation(id) -> bool                       │
│ - _run_operation_async(id, request) -> None        │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ OperationState (internal dict)                      │
├─────────────────────────────────────────────────────┤
│ status: str                                         │
│ progress: int                                       │
│ total: int                                          │
│ current_file: str                                   │
│ start_time: float                                   │
│ end_time: Optional[float]                           │
│ results: Optional[RenameStatus]                     │
│ error: Optional[str]                                │
│ cancelled: bool                                     │
│ thread: threading.Thread                            │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ OperationStatus (public model)                      │
├─────────────────────────────────────────────────────┤
│ operation_id: str                                   │
│ status: str                                         │
│ progress: int                                       │
│ total: int                                          │
│ current_file: str                                   │
│ start_time: float                                   │
│ end_time: Optional[float]                           │
│ results: Optional[RenameStatus]                     │
│ error: Optional[str]                                │
└─────────────────────────────────────────────────────┘
```

---

## IMPLEMENTATION REQUIREMENTS

### 1. Add OperationStatus Model

**File**: `dj_mp3_renamer/api/models.py`

```python
@dataclass(frozen=True)
class OperationStatus:
    """
    Status of an asynchronous operation.

    Used for polling operation progress in web UI.
    """
    operation_id: str
    status: str  # "running" | "completed" | "cancelled" | "error"
    progress: int  # Files processed so far
    total: int  # Total files to process
    current_file: str  # Currently processing file
    start_time: float  # Unix timestamp
    end_time: Optional[float] = None  # Unix timestamp when finished
    results: Optional[RenameStatus] = None  # Final results (when completed)
    error: Optional[str] = None  # Error message (when error)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for web API."""
        return {
            "operation_id": self.operation_id,
            "status": self.status,
            "progress": self.progress,
            "total": self.total,
            "current_file": self.current_file,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "results": {
                "total": self.results.total,
                "renamed": self.results.renamed,
                "skipped": self.results.skipped,
                "errors": self.results.errors,
            } if self.results else None,
            "error": self.error,
        }
```

### 2. Add OperationCancelled Exception

**File**: `dj_mp3_renamer/api/renamer.py`

```python
class OperationCancelled(Exception):
    """Raised when operation is cancelled by user."""
    pass
```

### 3. Modify RenamerAPI.__init__()

**File**: `dj_mp3_renamer/api/renamer.py`

```python
def __init__(self, workers: int = 4, logger: Optional[logging.Logger] = None):
    """
    Initialize the Renamer API.

    Args:
        workers: Number of worker threads for concurrent processing
        logger: Optional logger instance (creates one if not provided)
    """
    self.workers = max(1, workers)
    self.logger = logger or logging.getLogger("dj_mp3_renamer")
    self.config = load_config()

    # Async operation tracking
    self._operations: dict[str, dict] = {}
    self._lock = threading.Lock()
```

### 4. Add start_rename_async() Method

**File**: `dj_mp3_renamer/api/renamer.py`

```python
def start_rename_async(self, request: RenameRequest) -> str:
    """
    Start rename operation asynchronously.

    This method returns immediately with an operation ID. Use
    get_operation_status() to poll for progress and results.

    Args:
        request: RenameRequest with path, options, and template

    Returns:
        operation_id: UUID for tracking operation

    Examples:
        >>> api = RenamerAPI()
        >>> request = RenameRequest(path=Path("/music"), dry_run=False)
        >>> operation_id = api.start_rename_async(request)
        >>>
        >>> # Poll for status
        >>> while True:
        >>>     status = api.get_operation_status(operation_id)
        >>>     if status.status != "running":
        >>>         break
        >>>     print(f"Progress: {status.progress}/{status.total}")
        >>>     time.sleep(0.5)
    """
    import uuid

    operation_id = str(uuid.uuid4())

    # Initialize operation state
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

    self.logger.info(f"Started async operation {operation_id}")
    return operation_id
```

### 5. Add _run_operation_async() Method (Internal)

**File**: `dj_mp3_renamer/api/renamer.py`

```python
def _run_operation_async(self, operation_id: str, request: RenameRequest) -> None:
    """
    Run operation asynchronously in background thread.

    Updates operation state as it progresses. Called by start_rename_async().

    Args:
        operation_id: Operation ID
        request: RenameRequest
    """
    # Find files to get total count
    target = request.path.expanduser().resolve()
    if not target.exists():
        with self._lock:
            self._operations[operation_id]["status"] = "error"
            self._operations[operation_id]["error"] = f"Path does not exist: {target}"
            self._operations[operation_id]["end_time"] = time.time()
        return

    if target.is_file():
        mp3s = [target] if target.suffix.lower() == ".mp3" else []
    else:
        mp3s = find_mp3s(target, recursive=request.recursive)

    # Update total count
    with self._lock:
        self._operations[operation_id]["total"] = len(mp3s)

    if not mp3s:
        with self._lock:
            self._operations[operation_id]["status"] = "completed"
            self._operations[operation_id]["end_time"] = time.time()
            self._operations[operation_id]["results"] = RenameStatus(
                total=0, renamed=0, skipped=0, errors=0, results=[]
            )
        return

    # Define progress callback that updates state and checks cancellation
    def progress_callback(count: int, filename: str):
        with self._lock:
            if self._operations[operation_id]["cancelled"]:
                raise OperationCancelled("Operation cancelled by user")
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
        # Run the operation (this blocks until complete)
        results = self.rename_files(async_request)

        # Update state with results
        with self._lock:
            self._operations[operation_id]["status"] = "completed"
            self._operations[operation_id]["end_time"] = time.time()
            self._operations[operation_id]["results"] = results

        self.logger.info(f"Operation {operation_id} completed: {results.renamed} renamed")

    except OperationCancelled:
        with self._lock:
            self._operations[operation_id]["status"] = "cancelled"
            self._operations[operation_id]["end_time"] = time.time()
        self.logger.info(f"Operation {operation_id} cancelled by user")

    except Exception as e:
        self.logger.error(f"Operation {operation_id} failed: {e}", exc_info=True)
        with self._lock:
            self._operations[operation_id]["status"] = "error"
            self._operations[operation_id]["end_time"] = time.time()
            self._operations[operation_id]["error"] = str(e)
```

### 6. Add get_operation_status() Method

**File**: `dj_mp3_renamer/api/renamer.py`

```python
def get_operation_status(self, operation_id: str) -> Optional[OperationStatus]:
    """
    Get status of an asynchronous operation.

    Args:
        operation_id: Operation ID from start_rename_async()

    Returns:
        OperationStatus or None if operation not found

    Examples:
        >>> status = api.get_operation_status(operation_id)
        >>> if status:
        >>>     print(f"Status: {status.status}")
        >>>     print(f"Progress: {status.progress}/{status.total}")
        >>> else:
        >>>     print("Operation not found")
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
```

### 7. Add cancel_operation() Method

**File**: `dj_mp3_renamer/api/renamer.py`

```python
def cancel_operation(self, operation_id: str) -> bool:
    """
    Cancel a running operation.

    The operation will stop gracefully after processing the current file.

    Args:
        operation_id: Operation ID to cancel

    Returns:
        True if operation was cancelled, False if not found or already complete

    Examples:
        >>> success = api.cancel_operation(operation_id)
        >>> if success:
        >>>     print("Cancellation requested")
        >>> else:
        >>>     print("Operation not running or already complete")
    """
    with self._lock:
        if operation_id not in self._operations:
            return False

        op = self._operations[operation_id]
        if op["status"] != "running":
            return False  # Already complete/cancelled/error

        op["cancelled"] = True
        self.logger.info(f"Cancellation requested for operation {operation_id}")
        return True
```

### 8. Add clear_operation() Method

**File**: `dj_mp3_renamer/api/renamer.py`

```python
def clear_operation(self, operation_id: str) -> bool:
    """
    Remove operation from tracking (cleanup).

    Use this after retrieving results to free memory. Operations are
    kept indefinitely until cleared.

    Args:
        operation_id: Operation ID to remove

    Returns:
        True if removed, False if not found

    Examples:
        >>> # Get final results
        >>> status = api.get_operation_status(operation_id)
        >>> # Process results...
        >>> # Clean up
        >>> api.clear_operation(operation_id)
    """
    with self._lock:
        if operation_id in self._operations:
            del self._operations[operation_id]
            self.logger.debug(f"Cleared operation {operation_id}")
            return True
        return False
```

---

## TESTING REQUIREMENTS

### Test File: `tests/test_api_async.py` (NEW)

Create comprehensive tests for async operations:

```python
"""
Tests for asynchronous API operations.

Tests verify:
- Async operation lifecycle (start → running → completed)
- Status polling during operation
- Cancellation mid-operation
- Error handling in async mode
- Concurrent async operations
"""

import time
import threading
from pathlib import Path
import pytest
from unittest.mock import Mock, patch

from dj_mp3_renamer.api import RenamerAPI, RenameRequest
from dj_mp3_renamer.api.renamer import OperationCancelled


class TestAsyncOperations:
    """Test async operation support."""

    def test_start_rename_async_returns_operation_id(self, tmp_path):
        """Should return UUID operation ID."""
        # Create test file
        (tmp_path / "test.mp3").write_bytes(b"FAKE MP3")

        api = RenamerAPI()
        request = RenameRequest(path=tmp_path, dry_run=True)

        operation_id = api.start_rename_async(request)

        # Should return UUID string
        assert isinstance(operation_id, str)
        assert len(operation_id) == 36  # UUID format

    def test_get_operation_status_returns_status(self, tmp_path):
        """Should return operation status."""
        (tmp_path / "test.mp3").write_bytes(b"FAKE MP3")

        api = RenamerAPI()
        request = RenameRequest(path=tmp_path, dry_run=True)

        operation_id = api.start_rename_async(request)

        # Should be able to get status
        status = api.get_operation_status(operation_id)
        assert status is not None
        assert status.operation_id == operation_id
        assert status.status in ["running", "completed"]

    def test_async_operation_completes(self, tmp_path):
        """Should complete async operation successfully."""
        # Create test files
        for i in range(5):
            (tmp_path / f"test_{i}.mp3").write_bytes(b"FAKE MP3")

        api = RenamerAPI()

        with patch("dj_mp3_renamer.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Test", "title": "Test", "bpm": "128"},
                None
            )

            request = RenameRequest(path=tmp_path, dry_run=True)
            operation_id = api.start_rename_async(request)

            # Poll until complete (max 5 seconds)
            for _ in range(50):
                status = api.get_operation_status(operation_id)
                if status.status != "running":
                    break
                time.sleep(0.1)

            # Should be completed
            assert status.status == "completed"
            assert status.results is not None
            assert status.results.total == 5

    def test_cancel_operation_stops_operation(self, tmp_path):
        """Should cancel running operation."""
        # Create many files to ensure operation runs long enough to cancel
        for i in range(100):
            (tmp_path / f"test_{i}.mp3").write_bytes(b"FAKE MP3")

        api = RenamerAPI()

        with patch("dj_mp3_renamer.core.io.read_mp3_metadata") as mock_read:
            # Add small delay to make operation slower
            def slow_read(*args):
                time.sleep(0.01)
                return (
                    {"artist": "Test", "title": "Test", "bpm": "128"},
                    None
                )
            mock_read.side_effect = slow_read

            request = RenameRequest(path=tmp_path, dry_run=True)
            operation_id = api.start_rename_async(request)

            # Wait a bit for operation to start
            time.sleep(0.2)

            # Cancel operation
            cancelled = api.cancel_operation(operation_id)
            assert cancelled is True

            # Wait for cancellation to take effect
            time.sleep(0.5)

            # Should be cancelled
            status = api.get_operation_status(operation_id)
            assert status.status == "cancelled"
            assert status.progress < 100  # Didn't complete all files

    def test_operation_status_not_found(self, tmp_path):
        """Should return None for unknown operation ID."""
        api = RenamerAPI()

        status = api.get_operation_status("unknown-id")
        assert status is None

    def test_cancel_unknown_operation_returns_false(self, tmp_path):
        """Should return False for unknown operation ID."""
        api = RenamerAPI()

        cancelled = api.cancel_operation("unknown-id")
        assert cancelled is False

    def test_clear_operation_removes_from_tracking(self, tmp_path):
        """Should remove operation from tracking."""
        (tmp_path / "test.mp3").write_bytes(b"FAKE MP3")

        api = RenamerAPI()

        with patch("dj_mp3_renamer.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Test", "title": "Test", "bpm": "128"},
                None
            )

            request = RenameRequest(path=tmp_path, dry_run=True)
            operation_id = api.start_rename_async(request)

            # Wait for completion
            time.sleep(0.5)

            # Clear operation
            cleared = api.clear_operation(operation_id)
            assert cleared is True

            # Should no longer be able to get status
            status = api.get_operation_status(operation_id)
            assert status is None

    def test_concurrent_async_operations(self, tmp_path):
        """Should handle multiple concurrent operations."""
        # Create separate directories
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        for i in range(5):
            (dir1 / f"test_{i}.mp3").write_bytes(b"FAKE MP3")
            (dir2 / f"test_{i}.mp3").write_bytes(b"FAKE MP3")

        api = RenamerAPI()

        with patch("dj_mp3_renamer.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Test", "title": "Test", "bpm": "128"},
                None
            )

            # Start two operations
            request1 = RenameRequest(path=dir1, dry_run=True)
            request2 = RenameRequest(path=dir2, dry_run=True)

            op_id1 = api.start_rename_async(request1)
            op_id2 = api.start_rename_async(request2)

            # Wait for both to complete
            time.sleep(1.0)

            # Both should complete successfully
            status1 = api.get_operation_status(op_id1)
            status2 = api.get_operation_status(op_id2)

            assert status1.status == "completed"
            assert status2.status == "completed"
```

---

## ACCEPTANCE CRITERIA

- [ ] `OperationStatus` model added to `models.py`
- [ ] `OperationCancelled` exception added
- [ ] `RenamerAPI.__init__()` initializes operation tracking
- [ ] `start_rename_async()` returns operation ID
- [ ] `get_operation_status()` returns current status
- [ ] `cancel_operation()` stops running operation
- [ ] `clear_operation()` removes completed operation
- [ ] `_run_operation_async()` updates state correctly
- [ ] Thread-safe with proper locking
- [ ] 8+ comprehensive tests passing
- [ ] All existing tests still pass (178 tests)
- [ ] No breaking changes to existing API

---

## VERIFICATION COMMANDS

```bash
# Run new async tests
pytest tests/test_api_async.py -v

# Run all tests
pytest tests/ -v

# Check test coverage
pytest tests/test_api_async.py --cov=dj_mp3_renamer.api --cov-report=term
```

---

## PHASE 2: EXECUTION READY

This improved prompt is ready for execution. Proceed with implementation.
