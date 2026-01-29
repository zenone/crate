"""
Integration tests for end-to-end workflows.

These tests verify that the full system works together correctly,
complementing the unit tests that verify individual components.

Requirements:
- mutagen: Install with `pip install mutagen` to run these tests
- These tests use real MP3 file operations (mocked for speed)
"""

import logging
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from dj_mp3_renamer.api import RenamerAPI, RenameRequest

# Check if mutagen is available
try:
    import mutagen
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

# Skip all integration tests if mutagen not installed
pytestmark = pytest.mark.skipif(
    not MUTAGEN_AVAILABLE,
    reason="Integration tests require mutagen (pip install mutagen)"
)


# Test Fixtures
@pytest.fixture
def logger():
    """Create logger for tests."""
    return logging.getLogger("test_integration")


@pytest.fixture
def api_instance():
    """Create RenamerAPI instance with 2 workers for testing."""
    return RenamerAPI(workers=2)


@pytest.fixture
def test_mp3_files(tmp_path):
    """
    Create realistic test MP3 files with metadata.

    Returns:
        Tuple of (directory, list_of_files)
    """
    # Mock mutagen to create test files without actual MP3 data
    files = []
    for i in range(10):
        file = tmp_path / f"test_{i:02d}.mp3"
        file.write_bytes(b"FAKE MP3 DATA FOR TESTING")
        files.append(file)

    return tmp_path, files


# Helper Functions
def mock_mp3_metadata(artist="Test Artist", title="Test Title", bpm="128", key="Am"):
    """Create mock metadata for testing."""
    return {
        "artist": artist,
        "title": title,
        "bpm": bpm,
        "key": key,
        "camelot": "8A",
        "album": "",
        "label": "",
        "year": "",
        "track": "",
        "mix": "",
        "bpm_valid": "true",
        "key_valid": "true",
    }


# Integration Tests
class TestFullRenameWorkflow:
    """Test complete rename workflow from start to finish."""

    def test_full_rename_workflow_success(self, test_mp3_files, api_instance):
        """
        Integration test: Full rename workflow succeeds.

        Scenario:
        - User has 10 MP3 files with metadata
        - User runs rename operation with custom template
        - All files are renamed successfully
        - Original files no longer exist
        - New files have correct names

        Expected:
        - 10 files renamed
        - 0 errors
        - Files have correct new names
        """
        tmp_path, files = test_mp3_files

        # Mock MutagenFile availability and MP3 reading
        with patch("dj_mp3_renamer.core.io.MutagenFile", create=True) as mock_mutagen, \
             patch("dj_mp3_renamer.core.io.read_mp3_metadata") as mock_read:

            # Make MutagenFile appear available
            mock_mutagen.return_value = Mock()

            # Return different metadata for each file
            def side_effect(path, logger):
                # Extract index from filename (test_00.mp3 -> 0)
                index = int(path.stem.split("_")[1])
                return mock_mp3_metadata(
                    artist=f"Artist {index}",
                    title=f"Title {index}",
                    bpm="128"
                ), None

            mock_read.side_effect = side_effect

            # Execute rename
            request = RenameRequest(
                path=tmp_path,
                recursive=False,
                dry_run=False,
                template="{artist} - {title} [{bpm}]",
                auto_detect=False  # Disable auto-detection for speed
            )
            status = api_instance.rename_files(request)

        # Verify results
        assert status.total == 10, f"Expected 10 files, got {status.total}"
        assert status.renamed == 10, f"Expected 10 renamed, got {status.renamed}"
        assert status.skipped == 0, f"Expected 0 skipped, got {status.skipped}"
        assert status.errors == 0, f"Expected 0 errors, got {status.errors}"

        # Verify new files exist
        renamed_files = list(tmp_path.glob("Artist * - Title * [128].mp3"))
        assert len(renamed_files) == 10, f"Expected 10 renamed files, found {len(renamed_files)}"

        # Verify original files no longer exist
        original_files = list(tmp_path.glob("test_*.mp3"))
        assert len(original_files) == 0, f"Expected 0 original files, found {len(original_files)}"

    def test_full_rename_workflow_with_recursive(self, tmp_path, api_instance):
        """
        Integration test: Recursive rename finds files in subdirectories.

        Scenario:
        - Files exist in nested directories
        - User runs with recursive=True
        - All files in all subdirectories are renamed

        Expected:
        - Files in root and subdirs are renamed
        - Directory structure preserved
        """
        # Create files in multiple directories
        (tmp_path / "subdir1").mkdir()
        (tmp_path / "subdir2").mkdir()

        for i in range(5):
            (tmp_path / f"root_{i}.mp3").write_bytes(b"FAKE MP3")
            (tmp_path / "subdir1" / f"sub1_{i}.mp3").write_bytes(b"FAKE MP3")
            (tmp_path / "subdir2" / f"sub2_{i}.mp3").write_bytes(b"FAKE MP3")

        # Mock metadata
        with patch("dj_mp3_renamer.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = mock_mp3_metadata(), None

            # Execute recursive rename
            request = RenameRequest(
                path=tmp_path,
                recursive=True,
                dry_run=False,
                auto_detect=False
            )
            status = api_instance.rename_files(request)

        # Verify all 15 files renamed
        assert status.total == 15
        assert status.renamed == 15
        assert status.errors == 0


class TestPreviewWorkflow:
    """Test dry-run/preview workflow."""

    def test_preview_workflow_no_changes(self, test_mp3_files, api_instance):
        """
        Integration test: Dry-run mode doesn't change files.

        Scenario:
        - User wants to preview changes before applying
        - User runs with dry_run=True
        - Status shows what WOULD happen
        - NO files actually changed

        Expected:
        - Status shows 10 would be renamed
        - Original files still exist
        - No new files created
        """
        tmp_path, files = test_mp3_files

        # Mock metadata
        with patch("dj_mp3_renamer.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = mock_mp3_metadata(), None

            # Execute dry-run
            request = RenameRequest(
                path=tmp_path,
                recursive=False,
                dry_run=True,  # Dry-run mode
                template="{artist} - {title}",
                auto_detect=False
            )
            status = api_instance.rename_files(request)

        # Verify status reports what WOULD happen
        assert status.total == 10
        assert status.renamed == 10  # Would rename

        # Verify NO files actually changed
        original_files = list(tmp_path.glob("test_*.mp3"))
        assert len(original_files) == 10, "Original files should still exist"

        renamed_files = list(tmp_path.glob("Test Artist - Test Title.mp3"))
        assert len(renamed_files) == 0, "No files should be renamed in dry-run mode"


class TestCancellationWorkflow:
    """Test operation cancellation during processing."""

    def test_cancellation_via_progress_callback(self, tmp_path, api_instance):
        """
        Integration test: User cancels operation mid-way.

        Scenario:
        - User starts rename of 50 files
        - User cancels after 25 files processed
        - Operation stops immediately
        - Partial files are renamed

        Expected:
        - OperationCancelled exception raised
        - ~25 files renamed (approximately)
        - Remaining files not touched
        """
        # Create 50 test files
        for i in range(50):
            (tmp_path / f"test_{i:03d}.mp3").write_bytes(b"FAKE MP3")

        # Set up cancellation
        processed_count = 0
        cancel_after = 25

        class OperationCancelled(Exception):
            pass

        def progress_callback(count, filename):
            nonlocal processed_count
            processed_count = count
            if count >= cancel_after:
                raise OperationCancelled("User cancelled")

        # Mock metadata
        with patch("dj_mp3_renamer.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = mock_mp3_metadata(), None

            request = RenameRequest(
                path=tmp_path,
                recursive=False,
                dry_run=False,
                progress_callback=progress_callback,
                auto_detect=False
            )

            # Should raise cancellation exception
            with pytest.raises(OperationCancelled):
                api_instance.rename_files(request)

        # Verify partial completion
        assert 20 <= processed_count <= 30, f"Expected ~25 processed, got {processed_count}"

        # Verify some files renamed, some not
        renamed = list(tmp_path.glob("Test Artist - Test Title*.mp3"))
        original = list(tmp_path.glob("test_*.mp3"))

        assert len(renamed) > 0, "Some files should be renamed"
        assert len(original) > 0, "Some files should remain original"
        assert len(renamed) + len(original) == 50, "All files accounted for"


class TestErrorHandlingWorkflow:
    """Test error handling and recovery."""

    def test_error_handling_mixed_files(self, tmp_path, api_instance):
        """
        Integration test: Operation continues despite errors.

        Scenario:
        - 5 valid MP3 files
        - 3 corrupted files (will error)
        - User runs rename
        - Valid files process successfully
        - Corrupted files reported as errors
        - Operation doesn't crash

        Expected:
        - 5 files renamed successfully
        - 3 errors reported
        - No crash
        """
        # Create 5 valid files
        valid_files = []
        for i in range(5):
            file = tmp_path / f"valid_{i}.mp3"
            file.write_bytes(b"FAKE MP3")
            valid_files.append(file)

        # Create 3 corrupted files
        for i in range(3):
            file = tmp_path / f"corrupted_{i}.mp3"
            file.write_bytes(b"CORRUPTED")

        # Mock metadata: valid files succeed, corrupted fail
        def mock_read_side_effect(path, logger):
            if "corrupted" in path.name:
                return None, "Metadata read error: corrupted file"
            return mock_mp3_metadata(), None

        with patch("dj_mp3_renamer.core.io.read_mp3_metadata") as mock_read:
            mock_read.side_effect = mock_read_side_effect

            request = RenameRequest(
                path=tmp_path,
                dry_run=False,
                auto_detect=False
            )
            status = api_instance.rename_files(request)

        # Verify results
        assert status.total == 8
        assert status.renamed == 5, f"Expected 5 renamed, got {status.renamed}"
        assert status.errors == 3, f"Expected 3 errors, got {status.errors}"
        assert status.skipped == 0

        # Verify valid files renamed
        renamed = list(tmp_path.glob("Test Artist - Test Title*.mp3"))
        assert len(renamed) == 5, f"Expected 5 renamed files, got {len(renamed)}"

    def test_error_handling_missing_directory(self, api_instance):
        """
        Integration test: Handles missing directory gracefully.

        Scenario:
        - User provides path to non-existent directory
        - Operation should fail gracefully
        - No crash

        Expected:
        - Returns empty status
        - No errors or crashes
        """
        fake_path = Path("/this/does/not/exist")

        request = RenameRequest(path=fake_path, dry_run=False)
        status = api_instance.rename_files(request)

        # Should return empty status, not crash
        assert status.total == 0
        assert status.renamed == 0
        assert status.errors == 0


class TestConcurrentOperations:
    """Test thread safety with concurrent operations."""

    def test_concurrent_operations_thread_safe(self, tmp_path, api_instance):
        """
        Integration test: Multiple threads process files safely.

        Scenario:
        - 50 files to process
        - 4 worker threads
        - All files renamed successfully
        - No race conditions
        - No duplicate filenames

        Expected:
        - All 50 files renamed
        - All filenames unique (no collisions)
        - Thread-safe operation
        """
        # Create 50 test files
        for i in range(50):
            (tmp_path / f"test_{i:03d}.mp3").write_bytes(b"FAKE MP3")

        # Use 4 workers for concurrent processing
        api = RenamerAPI(workers=4)

        # Mock metadata - return unique data for each file
        def mock_read_side_effect(path, logger):
            # Extract index from filename
            index = path.stem.split("_")[1]
            return mock_mp3_metadata(
                artist=f"Artist {index}",
                title=f"Title {index}"
            ), None

        with patch("dj_mp3_renamer.core.io.read_mp3_metadata") as mock_read:
            mock_read.side_effect = mock_read_side_effect

            request = RenameRequest(
                path=tmp_path,
                dry_run=False,
                auto_detect=False
            )
            status = api.rename_files(request)

        # Verify all files processed
        assert status.total == 50
        assert status.renamed == 50
        assert status.errors == 0

        # Verify no duplicates (race condition check)
        renamed = list(tmp_path.glob("*.mp3"))
        assert len(renamed) == 50

        # Verify all filenames are unique
        names = [f.name for f in renamed]
        assert len(names) == len(set(names)), "All filenames should be unique (no collisions)"


class TestSkipWorkflow:
    """Test files that should be skipped."""

    def test_skip_files_already_named_correctly(self, tmp_path, api_instance):
        """
        Integration test: Files already named correctly are skipped.

        Scenario:
        - Files already have the desired name
        - User runs rename
        - Files are skipped (not renamed to same name)

        Expected:
        - Files reported as skipped
        - No file operations performed
        """
        # Create file with target name already
        file = tmp_path / "Test Artist - Test Title [128].mp3"
        file.write_bytes(b"FAKE MP3")

        with patch("dj_mp3_renamer.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = mock_mp3_metadata(), None

            request = RenameRequest(
                path=tmp_path,
                dry_run=False,
                template="{artist} - {title} [{bpm}]",
                auto_detect=False
            )
            status = api_instance.rename_files(request)

        # Verify file skipped (already has desired name)
        assert status.total == 1
        assert status.skipped == 1
        assert status.renamed == 0
