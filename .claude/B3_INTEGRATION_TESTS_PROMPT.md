# TASK B3: Add Integration Tests

**Date**: 2026-01-28
**Priority**: MEDIUM
**Estimated**: 6 hours
**TWO-PHASE**: This is the improved prompt (Phase 1)

---

## IMPROVED PROMPT - B3: Integration Tests

**Role**: Senior QA Engineer + Python Testing Expert

**Objective**: Add comprehensive integration tests to verify end-to-end workflows work correctly. Current suite has 162 unit tests (~90% coverage) but NO integration tests that verify complete user workflows.

**Scope**:
- **Files to Create**: `tests/test_integration.py` (new file)
- **Test Types**: End-to-end workflow tests using real (or realistic mock) scenarios
- **Coverage Goals**:
  - Full rename workflow (find → read → process → rename)
  - Preview workflow (dry-run mode)
  - Cancellation workflow (progress callback exception)
  - Error handling workflows (missing files, corrupted MP3s)
  - Concurrent operations (thread safety)

**Current State**:
```bash
$ ls tests/
test_api.py                    # 9 tests - API unit tests
test_conflict_resolution.py    # 17 tests - conflict logic
test_io.py                     # 19 tests - I/O operations
test_key_conversion.py         # 23 tests - key conversion
test_metadata_parsing.py       # 35 tests - metadata parsing
test_sanitization.py           # 21 tests - filename sanitization
test_template.py               # 14 tests - template expansion
test_validation.py             # 12 tests - validation

# MISSING: test_integration.py - End-to-end workflow tests
```

**Gap Analysis**:
- ✅ Unit tests verify individual functions work
- ❌ No tests verify the FULL WORKFLOW works together
- ❌ No tests for cancellation during processing
- ❌ No tests for concurrent operations (thread safety)
- ❌ No tests for error recovery
- ❌ No tests for first-run setup

---

## IMPLEMENTATION REQUIREMENTS

### Test Infrastructure

#### Setup: Create Test Fixtures
```python
# tests/test_integration.py

import pytest
from pathlib import Path
from unittest.mock import Mock
from dj_mp3_renamer.api import RenamerAPI, RenameRequest

@pytest.fixture
def test_mp3_files(tmp_path):
    """Create realistic test MP3 files with metadata."""
    # Create 10 test files with embedded ID3 tags
    files = []
    for i in range(10):
        file = tmp_path / f"test_{i}.mp3"
        # Create minimal valid MP3 with tags
        create_test_mp3(file, artist=f"Artist {i}", title=f"Title {i}", bpm="128")
        files.append(file)
    return tmp_path, files

@pytest.fixture
def api_instance():
    """Create RenamerAPI instance for testing."""
    return RenamerAPI(workers=2)
```

---

### Test 1: Full Rename Workflow (CRITICAL)

**Scenario**: User has 10 MP3 files, wants to rename them all

```python
def test_full_rename_workflow_success(test_mp3_files, api_instance):
    """
    Integration test: Full rename workflow from start to finish.

    Steps:
    1. Create test files with metadata
    2. Create RenameRequest
    3. Call api.rename_files()
    4. Verify all files renamed correctly
    5. Verify original files no longer exist
    6. Verify new files have correct names
    """
    tmp_path, files = test_mp3_files

    # Execute rename
    request = RenameRequest(
        path=tmp_path,
        recursive=False,
        dry_run=False,
        template="{artist} - {title} [{bpm}]"
    )
    status = api_instance.rename_files(request)

    # Verify results
    assert status.total == 10
    assert status.renamed == 10
    assert status.skipped == 0
    assert status.errors == 0

    # Verify files exist with new names
    renamed_files = list(tmp_path.glob("Artist * - Title * [128].mp3"))
    assert len(renamed_files) == 10

    # Verify original files no longer exist
    original_files = list(tmp_path.glob("test_*.mp3"))
    assert len(original_files) == 0
```

**Acceptance Criteria**:
- ✅ Creates 10 test MP3 files
- ✅ Renames all 10 files successfully
- ✅ Verifies new filenames match template
- ✅ Verifies original files removed

---

### Test 2: Preview Workflow (Dry-Run)

**Scenario**: User wants to preview changes before applying

```python
def test_preview_workflow_no_changes(test_mp3_files, api_instance):
    """
    Integration test: Dry-run mode doesn't change files.

    Steps:
    1. Create test files
    2. Run with dry_run=True
    3. Verify status shows what WOULD happen
    4. Verify NO files actually changed
    """
    tmp_path, files = test_mp3_files

    request = RenameRequest(
        path=tmp_path,
        recursive=False,
        dry_run=True,  # Dry-run mode
        template="{artist} - {title}"
    )
    status = api_instance.rename_files(request)

    # Verify status
    assert status.total == 10
    assert status.renamed == 10  # Would rename

    # Verify NO files changed
    original_files = list(tmp_path.glob("test_*.mp3"))
    assert len(original_files) == 10  # Still there

    renamed_files = list(tmp_path.glob("Artist * - Title *.mp3"))
    assert len(renamed_files) == 0  # None renamed
```

**Acceptance Criteria**:
- ✅ Reports what would be renamed
- ✅ Doesn't actually rename any files
- ✅ Original files remain unchanged

---

### Test 3: Cancellation Workflow

**Scenario**: User starts operation, then cancels mid-way

```python
def test_cancellation_workflow(test_mp3_files, api_instance):
    """
    Integration test: Cancellation during processing.

    Steps:
    1. Create 100 test files
    2. Start rename operation
    3. Cancel after 50 files via progress_callback
    4. Verify operation stopped
    5. Verify partial completion
    """
    tmp_path, files = create_many_test_files(tmp_path, count=100)

    processed_count = 0
    cancel_after = 50

    class OperationCancelled(Exception):
        pass

    def progress_callback(count, filename):
        nonlocal processed_count
        processed_count = count
        if count >= cancel_after:
            raise OperationCancelled("User cancelled")

    request = RenameRequest(
        path=tmp_path,
        recursive=False,
        dry_run=False,
        progress_callback=progress_callback
    )

    # Should raise cancellation exception
    with pytest.raises(OperationCancelled):
        api_instance.rename_files(request)

    # Verify partial completion
    assert 40 <= processed_count <= 60  # Approximately stopped at 50

    # Verify some files renamed, some not
    renamed = list(tmp_path.glob("Artist * - Title *.mp3"))
    original = list(tmp_path.glob("test_*.mp3"))
    assert len(renamed) > 0  # Some renamed
    assert len(original) > 0  # Some not renamed
    assert len(renamed) + len(original) == 100  # All accounted for
```

**Acceptance Criteria**:
- ✅ Operation stops when exception raised
- ✅ Partial files are renamed
- ✅ No data loss (all files accounted for)
- ✅ Exception propagates correctly

---

### Test 4: Error Handling Workflow

**Scenario**: Some files have errors, operation continues

```python
def test_error_handling_workflow(tmp_path, api_instance):
    """
    Integration test: Handles errors gracefully.

    Steps:
    1. Create mix of valid and invalid files
    2. Run rename operation
    3. Verify valid files renamed
    4. Verify invalid files reported as errors
    5. Verify no crashes
    """
    # Create 5 valid MP3 files
    valid_files = []
    for i in range(5):
        file = tmp_path / f"valid_{i}.mp3"
        create_test_mp3(file, artist="Artist", title=f"Title {i}")
        valid_files.append(file)

    # Create 3 corrupted files
    for i in range(3):
        file = tmp_path / f"corrupted_{i}.mp3"
        file.write_text("NOT A VALID MP3")  # Corrupted

    request = RenameRequest(path=tmp_path, dry_run=False)
    status = api_instance.rename_files(request)

    # Verify results
    assert status.total == 8
    assert status.renamed == 5  # Valid ones renamed
    assert status.errors == 3    # Corrupted ones errored
    assert status.skipped == 0

    # Verify valid files renamed
    renamed = list(tmp_path.glob("Artist - Title *.mp3"))
    assert len(renamed) == 5
```

**Acceptance Criteria**:
- ✅ Valid files process successfully
- ✅ Invalid files reported as errors
- ✅ Operation doesn't crash
- ✅ Status accurately reports errors

---

### Test 5: Concurrent Operations (Thread Safety)

**Scenario**: Multiple threads renaming files simultaneously

```python
def test_concurrent_operations_thread_safe(test_mp3_files, api_instance):
    """
    Integration test: Thread safety with concurrent operations.

    Steps:
    1. Create 100 test files
    2. Use 8 worker threads
    3. Verify no race conditions
    4. Verify all files renamed exactly once
    """
    tmp_path, files = create_many_test_files(tmp_path, count=100)

    api = RenamerAPI(workers=8)  # 8 concurrent threads
    request = RenameRequest(path=tmp_path, dry_run=False)

    status = api.rename_files(request)

    # Verify results
    assert status.total == 100
    assert status.renamed == 100
    assert status.errors == 0

    # Verify no duplicate names (race condition check)
    renamed = list(tmp_path.glob("*.mp3"))
    assert len(renamed) == 100

    # Verify all names unique (no collisions)
    names = [f.name for f in renamed]
    assert len(names) == len(set(names))  # All unique
```

**Acceptance Criteria**:
- ✅ No race conditions
- ✅ All files renamed exactly once
- ✅ No filename collisions
- ✅ Thread-safe operation verified

---

## TEST HELPERS

### Helper: Create Test MP3
```python
def create_test_mp3(
    path: Path,
    artist: str = "Test Artist",
    title: str = "Test Title",
    bpm: str = "128",
    key: str = "Am"
) -> None:
    """
    Create a minimal valid MP3 file with ID3 tags for testing.

    Uses mutagen to create proper MP3 structure.
    """
    try:
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3, TPE1, TIT2, TBPM, TKEY

        # Create minimal MP3 file (silent audio)
        # This is a minimal MP3 header + frame
        mp3_header = bytes([
            0xFF, 0xFB, 0x90, 0x00,  # MP3 sync + header
            # ... minimal valid MP3 data
        ])
        path.write_bytes(mp3_header)

        # Add ID3 tags
        audio = MP3(str(path))
        audio.tags = ID3()
        audio.tags.add(TPE1(encoding=3, text=artist))
        audio.tags.add(TIT2(encoding=3, text=title))
        audio.tags.add(TBPM(encoding=3, text=bpm))
        audio.tags.add(TKEY(encoding=3, text=key))
        audio.save()
    except ImportError:
        # Fallback: Create fake file (tests may need to mock)
        path.write_bytes(b"FAKE MP3 FOR TESTING")
```

---

## DEFINITION OF DONE

- [ ] `tests/test_integration.py` created with 5+ integration tests
- [ ] Test 1: Full rename workflow - PASSING
- [ ] Test 2: Preview workflow - PASSING
- [ ] Test 3: Cancellation workflow - PASSING
- [ ] Test 4: Error handling workflow - PASSING
- [ ] Test 5: Concurrent operations - PASSING
- [ ] All existing tests still pass (162 + new tests)
- [ ] Tests run in <30 seconds total
- [ ] Documentation added to test file
- [ ] Changes committed with message: `test: Add comprehensive integration tests for end-to-end workflows`

---

## VERIFICATION COMMANDS

```bash
# Run new integration tests only
pytest tests/test_integration.py -v

# Run all tests
pytest tests/ -v

# Check coverage
pytest tests/ --cov=dj_mp3_renamer --cov-report=term

# Run tests with timing
pytest tests/ -v --durations=10
```

---

## ACCEPTANCE CRITERIA

1. ✅ 5 integration tests added
2. ✅ All tests pass
3. ✅ Tests cover critical workflows
4. ✅ Tests are fast (<5s each)
5. ✅ Tests are reliable (no flaky tests)
6. ✅ Tests document expected behavior
7. ✅ Existing 162 tests still pass

---

## CONSTRAINTS

1. **No Breaking Changes**: Tests verify existing behavior
2. **Fast Execution**: Each test <5 seconds
3. **Isolation**: Tests don't depend on each other
4. **Cleanup**: Tests clean up temp files
5. **Realistic**: Tests use realistic scenarios

---

## BEST PRACTICES (2025-2026)

- Use pytest fixtures for setup/teardown
- Use tmp_path for temporary files (auto-cleanup)
- Use descriptive test names (test_what_when_then)
- Add docstrings explaining test scenario
- Use assertions with clear messages
- Mock external dependencies (network, etc.)
- Test both happy path and error cases

---

## ASSUMPTIONS

1. Tests will use tmp_path fixture (auto-cleanup)
2. mutagen is available for creating test MP3s
3. Tests should be deterministic (no random behavior)
4. Tests verify behavior, not implementation
5. Integration tests complement (not replace) unit tests

---

## PHASE 2: EXECUTION READY

This improved prompt is ready for execution. Proceed with implementation.
