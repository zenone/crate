"""
Tests for API module (RED phase - tests written first).
"""

import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from crate.api.models import RenameRequest, RenameResult, RenameStatus
from crate.api.renamer import RenamerAPI


class TestRenamerAPI:
    """Test RenamerAPI class."""

    def test_rename_single_file_success(self, tmp_path):
        """Should successfully rename a single file."""
        # Create a fake MP3 file
        src = tmp_path / "test.mp3"
        src.touch()

        api = RenamerAPI()

        # Mock the metadata reading and renaming logic
        mock_meta = {
            "artist": "Test Artist",
            "title": "Test Song",
            "bpm": "128",
            "key": "Am",
            "camelot": "8A",
            "mix": "",
        }

        with patch("crate.api.renamer.read_mp3_metadata", return_value=(mock_meta, None)):
            request = RenameRequest(path=src, dry_run=True)
            status = api.rename_files(request)

            assert status.total == 1
            assert status.renamed == 1
            assert status.skipped == 0
            assert status.errors == 0

    def test_rename_directory(self, tmp_path):
        """Should rename multiple files in directory."""
        # Create fake MP3 files
        (tmp_path / "song1.mp3").touch()
        (tmp_path / "song2.mp3").touch()

        api = RenamerAPI()

        mock_meta = {
            "artist": "Test",
            "title": "Song",
            "bpm": "",
            "key": "",
            "camelot": "",
            "mix": "",
        }

        with patch("crate.api.renamer.read_mp3_metadata", return_value=(mock_meta, None)):
            request = RenameRequest(path=tmp_path, dry_run=True)
            status = api.rename_files(request)

            assert status.total == 2

    def test_rename_with_error(self, tmp_path):
        """Should handle errors gracefully."""
        src = tmp_path / "test.mp3"
        src.touch()

        api = RenamerAPI()

        # Simulate error in metadata reading (treated as "skipped")
        with patch("crate.api.renamer.read_mp3_metadata", return_value=(None, "Test error")):
            request = RenameRequest(path=src, dry_run=True)
            status = api.rename_files(request)

            assert status.skipped == 1

    def test_no_mp3_files(self, tmp_path):
        """Should handle directory with no MP3 files."""
        api = RenamerAPI()

        request = RenameRequest(path=tmp_path, dry_run=True)
        status = api.rename_files(request)

        assert status.total == 0

    def test_custom_template(self, tmp_path):
        """Should support custom templates."""
        src = tmp_path / "test.mp3"
        src.touch()

        api = RenamerAPI()

        mock_meta = {
            "artist": "Test",
            "title": "Song",
            "bpm": "128",
            "key": "",
            "camelot": "",
            "mix": "",
        }

        with patch("crate.api.renamer.read_mp3_metadata", return_value=(mock_meta, None)):
            request = RenameRequest(path=src, dry_run=True, template="{artist} - {bpm}")
            status = api.rename_files(request)

            assert status.total == 1

    def test_workers_parameter(self, tmp_path):
        """Should accept workers parameter."""
        src = tmp_path / "test.mp3"
        src.touch()

        api = RenamerAPI(workers=8)
        assert api.workers == 8


class TestModels:
    """Test data models."""

    def test_rename_request_creation(self):
        """Should create RenameRequest."""
        req = RenameRequest(path=Path("/test"))
        assert req.path == Path("/test")
        assert req.recursive is False
        assert req.dry_run is False

    def test_rename_result_creation(self):
        """Should create RenameResult."""
        result = RenameResult(
            src=Path("/old.mp3"),
            dst=Path("/new.mp3"),
            status="renamed",
        )
        assert result.status == "renamed"

    def test_rename_status_creation(self):
        """Should create RenameStatus."""
        status = RenameStatus(
            total=10,
            renamed=8,
            skipped=1,
            errors=1,
            results=[],
        )
        assert status.total == 10
        assert status.renamed == 8
