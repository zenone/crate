"""
Tests for I/O module (RED phase - tests written first).
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from dj_mp3_renamer.core.io import (
    read_mp3_metadata,
    find_mp3s,
    ReservationBook,
)


class TestReadMp3Metadata:
    """Test read_mp3_metadata function."""

    def test_mutagen_not_available(self):
        """Should return error if mutagen not installed."""
        logger = logging.getLogger("test")
        with patch("dj_mp3_renamer.core.io.MutagenFile", None):
            meta, error = read_mp3_metadata(Path("/fake/path.mp3"), logger)
            assert meta is None
            assert "mutagen" in error.lower()

    def test_no_tags(self):
        """Should return error if file has no tags."""
        logger = logging.getLogger("test")
        mock_audio = Mock()
        mock_audio.tags = None

        with patch("dj_mp3_renamer.core.io.MutagenFile", return_value=mock_audio):
            meta, error = read_mp3_metadata(Path("/fake/path.mp3"), logger)
            assert meta is None
            assert error is not None

    def test_basic_metadata(self):
        """Should extract basic ID3 tags."""
        logger = logging.getLogger("test")

        mock_tags = {
            "TPE1": Mock(text=["Test Artist"]),
            "TIT2": Mock(text=["Test Title"]),
            "TBPM": Mock(text=["128"]),
            "TKEY": Mock(text=["Am"]),
        }

        mock_audio = Mock()
        mock_audio.tags = mock_tags

        with patch("dj_mp3_renamer.core.io.MutagenFile", return_value=mock_audio):
            meta, error = read_mp3_metadata(Path("/fake/path.mp3"), logger)

            assert error is None
            assert meta is not None
            assert meta["artist"] == "Test Artist"
            assert meta["title"] == "Test Title"
            assert meta["bpm"] == "128"

    def test_camelot_conversion(self):
        """Should convert key to Camelot."""
        logger = logging.getLogger("test")

        mock_tags = {
            "TPE1": Mock(text=["Artist"]),
            "TIT2": Mock(text=["Title"]),
            "TKEY": Mock(text=["Am"]),
        }

        mock_audio = Mock()
        mock_audio.tags = mock_tags

        with patch("dj_mp3_renamer.core.io.MutagenFile", return_value=mock_audio):
            meta, error = read_mp3_metadata(Path("/fake/path.mp3"), logger)

            assert error is None
            assert meta is not None
            assert meta["key"] == "Am"
            assert meta["camelot"] == "8A"

    def test_mix_inference(self):
        """Should infer mix from title."""
        logger = logging.getLogger("test")

        mock_tags = {
            "TPE1": Mock(text=["Artist"]),
            "TIT2": Mock(text=["Title (Extended Mix)"]),
        }

        mock_audio = Mock()
        mock_audio.tags = mock_tags

        with patch("dj_mp3_renamer.core.io.MutagenFile", return_value=mock_audio):
            meta, error = read_mp3_metadata(Path("/fake/path.mp3"), logger)

            assert error is None
            assert meta is not None
            assert meta["mix"] == "Extended Mix"

    def test_exception_handling(self):
        """Should handle exceptions gracefully."""
        logger = logging.getLogger("test")

        with patch("dj_mp3_renamer.core.io.MutagenFile", side_effect=Exception("Boom")):
            meta, error = read_mp3_metadata(Path("/fake/path.mp3"), logger)

            assert meta is None
            assert error is not None
            assert "error" in error.lower()

    def test_mutagen_returns_none(self):
        """Should handle when mutagen returns None."""
        logger = logging.getLogger("test")

        with patch("dj_mp3_renamer.core.io.MutagenFile", return_value=None):
            meta, error = read_mp3_metadata(Path("/fake/path.mp3"), logger)

            assert meta is None
            assert error is not None


class TestFindMp3s:
    """Test find_mp3s function."""

    def test_recursive_glob(self, tmp_path):
        """Should find MP3s recursively."""
        # Create test structure
        (tmp_path / "test.mp3").touch()
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "test2.mp3").touch()
        (tmp_path / "other.txt").touch()

        mp3s = find_mp3s(tmp_path, recursive=True)

        assert len(mp3s) == 2
        assert all(p.suffix.lower() == ".mp3" for p in mp3s)

    def test_non_recursive_glob(self, tmp_path):
        """Should find MP3s only in top level."""
        # Create test structure
        (tmp_path / "test.mp3").touch()
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "test2.mp3").touch()

        mp3s = find_mp3s(tmp_path, recursive=False)

        assert len(mp3s) == 1
        assert mp3s[0].name == "test.mp3"

    def test_empty_directory(self, tmp_path):
        """Should return empty list for directory with no MP3s."""
        mp3s = find_mp3s(tmp_path, recursive=True)
        assert mp3s == []


class TestReservationBook:
    """Test ReservationBook class."""

    def test_reserve_unique_new_file(self, tmp_path):
        """Should reserve a file that doesn't exist."""
        book = ReservationBook()
        result = book.reserve_unique(tmp_path, "test", ".mp3")

        assert result == tmp_path / "test.mp3"

    def test_reserve_unique_existing_file(self, tmp_path):
        """Should add number if file exists."""
        (tmp_path / "test.mp3").touch()

        book = ReservationBook()
        result = book.reserve_unique(tmp_path, "test", ".mp3")

        assert result == tmp_path / "test (2).mp3"

    def test_reserve_unique_multiple_collisions(self, tmp_path):
        """Should increment number for multiple collisions."""
        (tmp_path / "test.mp3").touch()
        (tmp_path / "test (2).mp3").touch()

        book = ReservationBook()
        result = book.reserve_unique(tmp_path, "test", ".mp3")

        assert result == tmp_path / "test (3).mp3"

    def test_reserve_unique_tracks_reservations(self, tmp_path):
        """Should track reservations within same directory."""
        book = ReservationBook()

        r1 = book.reserve_unique(tmp_path, "test", ".mp3")
        r2 = book.reserve_unique(tmp_path, "test", ".mp3")

        assert r1 == tmp_path / "test.mp3"
        assert r2 == tmp_path / "test (2).mp3"

    def test_thread_safety(self, tmp_path):
        """Should be thread-safe for same directory."""
        import threading

        book = ReservationBook()
        results = []

        def reserve():
            result = book.reserve_unique(tmp_path, "test", ".mp3")
            results.append(result)

        threads = [threading.Thread(target=reserve) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All results should be unique
        assert len(results) == 10
        assert len(set(results)) == 10
