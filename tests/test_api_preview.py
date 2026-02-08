"""
Tests for file preview API.

Tests verify:
- Preview returns list of FilePreview objects
- Preview shows old → new filenames
- Preview identifies files that will be skipped
- Preview handles errors gracefully
- Preview is fast (no audio analysis)
- Preview doesn't modify files
- FilePreview model JSON serialization
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from crate.api import RenamerAPI, RenameRequest
from crate.api.models import FilePreview
from crate.core.config import DEFAULT_CONFIG


# Test Fixtures
@pytest.fixture
def api_instance():
    """Create RenamerAPI instance for testing.

    Tests must be deterministic and should not depend on any real user config on disk.
    """
    api = RenamerAPI(workers=2)
    api.config = dict(DEFAULT_CONFIG)
    return api


@pytest.fixture
def test_files(tmp_path):
    """Create test MP3 files."""
    for i in range(5):
        (tmp_path / f"test_{i:02d}.mp3").write_bytes(b"FAKE MP3 DATA")
    return tmp_path


# Test: Basic Preview
class TestPreviewBasics:
    """Test basic preview functionality."""

    def test_preview_returns_list(self, api_instance, test_files):
        """Should return list of FilePreview objects."""
        # Patch where it is used (in renamer.py), not where defined
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Test", "title": "Test", "bpm": "128", "key": "Am"},
                None
            )

            request = RenameRequest(path=test_files)
            previews = api_instance.preview_rename(request)

            assert isinstance(previews, list)
            assert len(previews) == 5
            assert all(isinstance(p, FilePreview) for p in previews)

    def test_preview_shows_old_to_new_names(self, api_instance, test_files):
        """Should show old → new filenames."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Artist", "title": "Title", "bpm": "128", "key": "Am"},
                None
            )

            request = RenameRequest(path=test_files, template="{artist} - {title}")
            previews = api_instance.preview_rename(request)

            # Should have old and new names
            # Note: collision avoidance will suffix duplicates within the batch.
            # Since all mocked metadata is identical, we expect a set like:
            #   Artist - Title.mp3, Artist - Title (2).mp3, ...
            dst_names = []
            for preview in previews:
                assert preview.src is not None
                assert preview.src.exists()
                if preview.status == "will_rename":
                    assert preview.dst is not None
                    dst_names.append(preview.dst.name)
                    assert preview.dst.name.startswith("Artist - Title")
                    assert preview.dst.suffix.lower() == ".mp3"

            assert set(dst_names) == {
                "Artist - Title.mp3",
                "Artist - Title (2).mp3",
                "Artist - Title (3).mp3",
                "Artist - Title (4).mp3",
                "Artist - Title (5).mp3",
            }

    def test_preview_with_single_file(self, api_instance, tmp_path):
        """Should work with single file."""
        file = tmp_path / "test.mp3"
        file.write_bytes(b"FAKE MP3")

        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Artist", "title": "Title", "bpm": "128", "key": "Am"},
                None
            )

            request = RenameRequest(path=file)
            previews = api_instance.preview_rename(request)

            assert len(previews) == 1
            assert previews[0].src == file

    def test_preview_with_empty_directory(self, api_instance, tmp_path):
        """Should return empty list for directory with no MP3s."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        request = RenameRequest(path=empty_dir)
        previews = api_instance.preview_rename(request)

        assert previews == []

    def test_preview_with_nonexistent_path(self, api_instance):
        """Should return empty list for nonexistent path."""
        fake_path = Path("/nonexistent/path")

        request = RenameRequest(path=fake_path)
        previews = api_instance.preview_rename(request)

        assert previews == []


class TestPreviewStatuses:
    """Test preview status values."""

    def test_preview_status_will_rename(self, api_instance, test_files):
        """Should show 'will_rename' status for files that will be renamed."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Artist", "title": "Title", "bpm": "128", "key": "Am"},
                None
            )

            request = RenameRequest(path=test_files)
            previews = api_instance.preview_rename(request)

            # All should be will_rename (different from current names)
            assert all(p.status == "will_rename" for p in previews)
            assert all(p.dst is not None for p in previews)

    def test_preview_status_will_skip(self, api_instance, tmp_path):
        """Should show 'will_skip' status for files already correctly named."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Artist", "title": "Title", "bpm": "128", "key": "Am", "camelot": "8A"},
                None
            )

            # Create file with target name already
            file = tmp_path / "Artist - Title [8A 128].mp3"
            file.write_bytes(b"FAKE MP3")

            request = RenameRequest(path=tmp_path)
            previews = api_instance.preview_rename(request)

            assert len(previews) == 1
            assert previews[0].status == "will_skip"
            assert previews[0].reason is not None
            assert "already has desired name" in previews[0].reason.lower()

    def test_preview_status_error(self, api_instance, test_files):
        """Should show 'error' status for files with errors."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            # Simulate error reading metadata
            mock_read.return_value = (None, "Metadata read error")

            request = RenameRequest(path=test_files)
            previews = api_instance.preview_rename(request)

            # All should have errors (or be skipped)
            assert all(p.status in ["error", "will_skip"] for p in previews)
            assert all(p.dst is None for p in previews)
            assert all(p.reason is not None for p in previews)


class TestPreviewPerformance:
    """Test preview performance characteristics."""

    def test_preview_is_fast(self, api_instance, tmp_path):
        """Should be fast (no audio analysis)."""
        import time

        # Create many files
        for i in range(50):
            (tmp_path / f"test_{i:03d}.mp3").write_bytes(b"FAKE MP3")

        # Mock the metadata reader to be instant
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Artist", "title": "Title", "bpm": "128", "key": "Am"},
                None
            )

            request = RenameRequest(path=tmp_path)

            start = time.time()
            previews = api_instance.preview_rename(request)
            elapsed = time.time() - start

            # Should complete quickly (<1 second for 50 files)
            assert elapsed < 1.0
            assert len(previews) == 50

    def test_preview_doesnt_modify_files(self, api_instance, test_files):
        """Should not modify any files."""
        # Get original file states
        original_mtimes = {f: f.stat().st_mtime for f in test_files.iterdir()}

        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Artist", "title": "Title", "bpm": "128", "key": "Am"},
                None
            )

            request = RenameRequest(path=test_files)
            previews = api_instance.preview_rename(request)

            # Verify files unchanged
            assert len(previews) > 0  # Preview worked
            for file in test_files.iterdir():
                assert file.stat().st_mtime == original_mtimes[file]


class TestPreviewCollisionDetection:
    """Test preview collision detection."""

    def test_preview_detects_collisions(self, api_instance, tmp_path):
        """Should detect filename collisions."""
        # Create files that would collide
        (tmp_path / "file1.mp3").write_bytes(b"FAKE MP3")
        (tmp_path / "file2.mp3").write_bytes(b"FAKE MP3")

        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            # Both files have same metadata (would create same name)
            mock_read.return_value = (
                {"artist": "Artist", "title": "Title", "bpm": "128", "key": "Am"},
                None
            )

            request = RenameRequest(path=tmp_path, template="{artist} - {title}")
            previews = api_instance.preview_rename(request)

            assert len(previews) == 2

            # First should be normal, second should have collision suffix
            dst_names = [p.dst.name for p in previews if p.dst]
            # Order might vary, but set should match
            expected = {"Artist - Title.mp3", "Artist - Title (2).mp3"}
            assert set(dst_names) == expected


class TestPreviewRecursive:
    """Test preview with recursive option."""

    def test_preview_recursive_finds_subdirectories(self, api_instance, tmp_path):
        """Should find files in subdirectories with recursive=True."""
        # Create files in root and subdirs
        (tmp_path / "root.mp3").write_bytes(b"FAKE MP3")

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "sub.mp3").write_bytes(b"FAKE MP3")

        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Artist", "title": "Title", "bpm": "128", "key": "Am"},
                None
            )

            # Without recursive
            request = RenameRequest(path=tmp_path, recursive=False)
            previews = api_instance.preview_rename(request)
            assert len(previews) == 1  # Only root file

            # With recursive
            request = RenameRequest(path=tmp_path, recursive=True)
            previews = api_instance.preview_rename(request)
            assert len(previews) == 2  # Root + subdirectory file


class TestFilePreviewModel:
    """Test FilePreview model."""

    def test_file_preview_to_dict(self, api_instance, test_files):
        """Should convert FilePreview to JSON-serializable dict."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Artist", "title": "Title", "bpm": "128", "key": "Am"},
                None
            )

            request = RenameRequest(path=test_files)
            previews = api_instance.preview_rename(request)

            # Convert first preview to dict
            preview_dict = previews[0].to_dict()

            # Should have all expected fields
            assert "src" in preview_dict
            assert "dst" in preview_dict
            assert "status" in preview_dict
            assert "reason" in preview_dict
            assert "metadata" in preview_dict

            # All values should be JSON-serializable
            assert isinstance(preview_dict["src"], str)
            if preview_dict["dst"]:
                assert isinstance(preview_dict["dst"], str)
            assert isinstance(preview_dict["status"], str)

    def test_file_preview_metadata_included(self, api_instance, test_files):
        """Should include metadata in preview."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "TestArtist", "title": "TestTitle", "bpm": "130", "key": "Cm"},
                None
            )

            request = RenameRequest(path=test_files)
            previews = api_instance.preview_rename(request)

            # Should have metadata
            assert previews[0].metadata is not None
            assert previews[0].metadata["artist"] == "TestArtist"
            assert previews[0].metadata["title"] == "TestTitle"
            assert previews[0].metadata["bpm"] == "130"


class TestPreviewTemplates:
    """Test preview with different templates."""

    def test_preview_with_custom_template(self, api_instance, test_files):
        """Should respect custom template."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Artist", "title": "Title", "bpm": "128", "key": "Am", "camelot": "8A"},
                None
            )

            # Custom template
            request = RenameRequest(
                path=test_files,
                template="[{camelot}] {bpm} - {artist} - {title}"
            )
            previews = api_instance.preview_rename(request)

            # Should follow custom template (with collision suffixes)
            dst_names = [p.dst.name for p in previews if p.status == "will_rename" and p.dst]
            assert set(dst_names) == {
                "[8A] 128 - Artist - Title.mp3",
                "[8A] 128 - Artist - Title (2).mp3",
                "[8A] 128 - Artist - Title (3).mp3",
                "[8A] 128 - Artist - Title (4).mp3",
                "[8A] 128 - Artist - Title (5).mp3",
            }

    def test_preview_with_default_template(self, api_instance, test_files):
        """Should use default template if none specified."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Artist", "title": "Title", "bpm": "128", "key": "Am", "camelot": "8A"},
                None
            )

            # No template specified
            request = RenameRequest(path=test_files)
            previews = api_instance.preview_rename(request)

            # Should use default template format
            # Default: {artist} - {title} [{camelot} {bpm}]
            for preview in previews:
                if preview.status == "will_rename":
                    assert "Artist" in preview.dst.name
                    assert "Title" in preview.dst.name
                    assert "8A" in preview.dst.name
                    assert "128" in preview.dst.name
