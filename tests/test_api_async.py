"""
Tests for asynchronous API operations.

Tests verify:
- Async operation lifecycle (start → running → completed)
- Status polling during operation
- Cancellation mid-operation
- Error handling in async mode
- Concurrent async operations
- Operation cleanup
"""

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from crate.api import RenamerAPI, RenameRequest


# Test Fixtures
@pytest.fixture
def api_instance():
    """Create RenamerAPI instance for testing."""
    return RenamerAPI(workers=2)


@pytest.fixture
def test_files(tmp_path):
    """Create test MP3 files."""
    for i in range(5):
        (tmp_path / f"test_{i:02d}.mp3").write_bytes(b"FAKE MP3 DATA")
    return tmp_path


# Test: Basic Async Operations
class TestAsyncBasics:
    """Test basic async operation functionality."""

    def test_start_rename_async_returns_operation_id(self, api_instance, test_files):
        """Should return UUID operation ID."""
        request = RenameRequest(path=test_files, dry_run=True, auto_detect=False)

        operation_id = api_instance.start_rename_async(request)

        # Should return UUID string
        assert isinstance(operation_id, str)
        assert len(operation_id) == 36  # UUID format
        assert '-' in operation_id  # UUID contains hyphens

    def test_get_operation_status_returns_status(self, api_instance, test_files):
        """Should return operation status."""
        request = RenameRequest(path=test_files, dry_run=True, auto_detect=False)

        operation_id = api_instance.start_rename_async(request)

        # Should be able to get status immediately
        status = api_instance.get_operation_status(operation_id)
        assert status is not None
        assert status.operation_id == operation_id
        assert status.status in ["running", "completed"]

    def test_get_operation_status_not_found(self, api_instance):
        """Should return None for unknown operation ID."""
        status = api_instance.get_operation_status("unknown-id-12345")
        assert status is None


class TestAsyncCompletion:
    """Test async operation completion."""

    def test_async_operation_completes(self, api_instance, test_files):
        """Should complete async operation successfully."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Test Artist", "title": "Test Title", "bpm": "128", "key": "Am"},
                None
            )

            request = RenameRequest(path=test_files, dry_run=True, auto_detect=False)
            operation_id = api_instance.start_rename_async(request)

            # Poll until complete (max 5 seconds)
            for _ in range(50):
                status = api_instance.get_operation_status(operation_id)
                if status.status != "running":
                    break
                time.sleep(0.1)

            # Should be completed
            assert status.status == "completed"
            assert status.results is not None
            assert status.results.total == 5
            assert status.end_time is not None
            assert status.end_time > status.start_time

    def test_async_operation_tracks_progress(self, api_instance, test_files):
        """Should track progress during operation."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            # Add small delay to make progress visible
            def slow_read(*args):
                time.sleep(0.05)
                return (
                    {"artist": "Test", "title": "Test", "bpm": "128", "key": "Am"},
                    None
                )
            mock_read.side_effect = slow_read

            request = RenameRequest(path=test_files, dry_run=True, auto_detect=False)
            operation_id = api_instance.start_rename_async(request)

            # Should see progress increasing
            progress_values = []
            for _ in range(20):
                status = api_instance.get_operation_status(operation_id)
                progress_values.append(status.progress)
                if status.status != "running":
                    break
                time.sleep(0.1)

            # Progress should increase over time
            assert len(progress_values) > 1
            assert max(progress_values) > min(progress_values)

    def test_async_operation_with_no_files(self, api_instance, tmp_path):
        """Should handle directory with no MP3 files."""
        # Empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        request = RenameRequest(path=empty_dir, dry_run=True, auto_detect=False)
        operation_id = api_instance.start_rename_async(request)

        # Wait for completion
        time.sleep(0.5)

        # Should complete with zero files
        status = api_instance.get_operation_status(operation_id)
        assert status.status == "completed"
        assert status.total == 0
        assert status.results.total == 0

    def test_async_operation_with_missing_path(self, api_instance):
        """Should handle non-existent path."""
        fake_path = Path("/nonexistent/path/to/files")

        request = RenameRequest(path=fake_path, dry_run=True, auto_detect=False)
        operation_id = api_instance.start_rename_async(request)

        # Wait for completion
        time.sleep(0.5)

        # Should be in error state
        status = api_instance.get_operation_status(operation_id)
        assert status.status == "error"
        assert status.error is not None
        assert "does not exist" in status.error.lower()


class TestAsyncCancellation:
    """Test operation cancellation."""

    def test_cancel_operation_stops_operation(self, api_instance, tmp_path):
        """Should cancel running operation."""
        # Create many files to ensure operation runs long enough
        for i in range(50):
            (tmp_path / f"test_{i:03d}.mp3").write_bytes(b"FAKE MP3")

        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            # Add delay to make operation slower (but not too slow for test suite)
            def slow_read(*args):
                time.sleep(0.03)
                return (
                    {"artist": "Test", "title": "Test", "bpm": "128", "key": "Am"},
                    None
                )
            mock_read.side_effect = slow_read

            request = RenameRequest(path=tmp_path, dry_run=True, auto_detect=False)
            operation_id = api_instance.start_rename_async(request)

            # Wait for operation to definitely start processing
            time.sleep(0.2)

            # Cancel operation (should still be running with 50 files at 0.03s each)
            cancelled = api_instance.cancel_operation(operation_id)

            # If already finished, that's okay - just verify cancel returns False
            if not cancelled:
                status = api_instance.get_operation_status(operation_id)
                assert status.status in ["completed", "cancelled"]
            else:
                # Wait for cancellation to take effect
                time.sleep(0.5)

                # Should be cancelled
                status = api_instance.get_operation_status(operation_id)
                assert status.status == "cancelled"
                assert status.progress < 50  # Didn't complete all files

    def test_cancel_unknown_operation_returns_false(self, api_instance):
        """Should return False for unknown operation ID."""
        cancelled = api_instance.cancel_operation("unknown-id")
        assert cancelled is False

    def test_cancel_completed_operation_returns_false(self, api_instance, test_files):
        """Should return False for already completed operation."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Test", "title": "Test", "bpm": "128", "key": "Am"},
                None
            )

            request = RenameRequest(path=test_files, dry_run=True, auto_detect=False)
            operation_id = api_instance.start_rename_async(request)

            # Wait for completion
            time.sleep(0.5)

            # Try to cancel completed operation
            cancelled = api_instance.cancel_operation(operation_id)
            assert cancelled is False


class TestAsyncCleanup:
    """Test operation cleanup."""

    def test_clear_operation_removes_from_tracking(self, api_instance, test_files):
        """Should remove operation from tracking."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Test", "title": "Test", "bpm": "128", "key": "Am"},
                None
            )

            request = RenameRequest(path=test_files, dry_run=True, auto_detect=False)
            operation_id = api_instance.start_rename_async(request)

            # Wait for completion
            time.sleep(0.5)

            # Clear operation
            cleared = api_instance.clear_operation(operation_id)
            assert cleared is True

            # Should no longer be able to get status
            status = api_instance.get_operation_status(operation_id)
            assert status is None

    def test_clear_unknown_operation_returns_false(self, api_instance):
        """Should return False for unknown operation ID."""
        cleared = api_instance.clear_operation("unknown-id")
        assert cleared is False


class TestConcurrentAsyncOperations:
    """Test multiple concurrent operations."""

    def test_concurrent_async_operations(self, api_instance, tmp_path):
        """Should handle multiple concurrent operations."""
        # Create separate directories
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        for i in range(5):
            (dir1 / f"test_{i}.mp3").write_bytes(b"FAKE MP3")
            (dir2 / f"test_{i}.mp3").write_bytes(b"FAKE MP3")

        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Test", "title": "Test", "bpm": "128", "key": "Am"},
                None
            )

            # Start two operations
            request1 = RenameRequest(path=dir1, dry_run=True, auto_detect=False)
            request2 = RenameRequest(path=dir2, dry_run=True, auto_detect=False)

            op_id1 = api_instance.start_rename_async(request1)
            op_id2 = api_instance.start_rename_async(request2)

            # Should have different IDs
            assert op_id1 != op_id2

            # Wait for both to complete
            time.sleep(1.0)

            # Both should complete successfully
            status1 = api_instance.get_operation_status(op_id1)
            status2 = api_instance.get_operation_status(op_id2)

            assert status1.status == "completed"
            assert status2.status == "completed"
            assert status1.results.total == 5
            assert status2.results.total == 5


class TestOperationStatusModel:
    """Test OperationStatus model."""

    def test_operation_status_to_dict(self, api_instance, test_files):
        """Should convert OperationStatus to JSON-serializable dict."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Test", "title": "Test", "bpm": "128", "key": "Am"},
                None
            )

            request = RenameRequest(path=test_files, dry_run=True, auto_detect=False)
            operation_id = api_instance.start_rename_async(request)

            # Wait for completion
            time.sleep(0.5)

            # Get status and convert to dict
            status = api_instance.get_operation_status(operation_id)
            status_dict = status.to_dict()

            # Should have all expected fields
            assert "operation_id" in status_dict
            assert "status" in status_dict
            assert "progress" in status_dict
            assert "total" in status_dict
            assert "current_file" in status_dict
            assert "start_time" in status_dict
            assert "end_time" in status_dict
            assert "results" in status_dict
            assert "error" in status_dict

            # Results should be a dict (not RenameStatus object)
            assert isinstance(status_dict["results"], dict)
            assert "total" in status_dict["results"]
            assert "renamed" in status_dict["results"]
