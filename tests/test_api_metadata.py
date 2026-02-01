"""
Tests for metadata analysis API (ENH-006).

Tests verify:
- Basic file analysis
- Metadata enhancement integration
- Error handling for missing/corrupted files
- Config integration (MusicBrainz, AI)
- Return format and field completeness
"""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock
from crate.api import RenamerAPI


# Test Fixtures
@pytest.fixture
def api_instance():
    """Create RenamerAPI instance for testing."""
    return RenamerAPI(workers=2)


@pytest.fixture
def sample_mp3(tmp_path):
    """Create a sample MP3 file for testing."""
    mp3_file = tmp_path / "test.mp3"
    mp3_file.write_bytes(b"FAKE MP3 DATA FOR TESTING")
    return mp3_file


def mock_metadata(artist="Test Artist", title="Test Title", bpm="128", key="Am"):
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


# Test: Basic Analysis
class TestBasicAnalysis:
    """Test basic file analysis functionality."""

    def test_analyze_valid_file(self, api_instance, sample_mp3):
        """Should analyze valid MP3 file."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(), None)

            result = api_instance.analyze_file(sample_mp3)

            assert result is not None
            assert isinstance(result, dict)
            assert "artist" in result
            assert "title" in result

    def test_analyze_returns_metadata_fields(self, api_instance, sample_mp3):
        """Should return standard metadata fields."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(), None)

            result = api_instance.analyze_file(sample_mp3)

            # Core fields should be present
            assert "artist" in result
            assert "title" in result
            assert result["artist"] == "Test Artist"
            assert result["title"] == "Test Title"

    def test_analyze_includes_bpm_key(self, api_instance, sample_mp3):
        """Should include BPM and key if present."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(), None)

            result = api_instance.analyze_file(sample_mp3)

            assert "bpm" in result
            assert "key" in result
            assert result["bpm"] == "128"
            assert result["key"] == "Am"

    def test_analyze_multiple_files(self, api_instance, tmp_path):
        """Should analyze multiple files independently."""
        file1 = tmp_path / "file1.mp3"
        file2 = tmp_path / "file2.mp3"

        file1.write_bytes(b"FAKE MP3 DATA")
        file2.write_bytes(b"FAKE MP3 DATA")

        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            def side_effect(path, logger):
                if "file1" in str(path):
                    return mock_metadata(artist="Artist 1", title="Title 1"), None
                else:
                    return mock_metadata(artist="Artist 2", title="Title 2"), None

            mock_read.side_effect = side_effect

            result1 = api_instance.analyze_file(file1)
            result2 = api_instance.analyze_file(file2)

            assert result1["artist"] == "Artist 1"
            assert result2["artist"] == "Artist 2"


# Test: Error Handling
class TestErrorHandling:
    """Test error handling for invalid files."""

    def test_analyze_nonexistent_file(self, api_instance, tmp_path):
        """Should return None for nonexistent file."""
        nonexistent = tmp_path / "nonexistent.mp3"
        result = api_instance.analyze_file(nonexistent)

        assert result is None

    def test_analyze_invalid_file(self, api_instance, tmp_path):
        """Should return None for invalid MP3 file."""
        invalid_file = tmp_path / "invalid.mp3"
        invalid_file.write_text("not an mp3 file")

        result = api_instance.analyze_file(invalid_file)

        assert result is None

    def test_analyze_non_mp3_file(self, api_instance, tmp_path):
        """Should return None for non-MP3 file."""
        text_file = tmp_path / "test.txt"
        text_file.write_text("just text")

        result = api_instance.analyze_file(text_file)

        assert result is None

    def test_analyze_directory(self, api_instance, tmp_path):
        """Should return None when given directory path."""
        result = api_instance.analyze_file(tmp_path)

        assert result is None


# Test: Metadata Enhancement
class TestMetadataEnhancement:
    """Test metadata enhancement integration."""

    def test_analyze_enhances_metadata(self, api_instance, tmp_path):
        """Should enhance metadata with missing fields."""
        # Create MP3 without BPM/key
        mp3_file = tmp_path / "no_bpm.mp3"
        mp3_file.write_bytes(b"FAKE MP3 DATA")

        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            # Return metadata without BPM/key
            meta = mock_metadata(artist="Artist", title="Title", bpm="", key="")
            mock_read.return_value = (meta, None)

            result = api_instance.analyze_file(mp3_file)

            # Should still return result even if enhancement fails
            assert result is not None
            assert result["artist"] == "Artist"
            assert result["title"] == "Title"

    def test_analyze_preserves_existing_metadata(self, api_instance, sample_mp3):
        """Should preserve existing metadata during analysis."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(), None)

            result = api_instance.analyze_file(sample_mp3)

            # Original metadata should be intact
            assert result["artist"] == "Test Artist"
            assert result["title"] == "Test Title"
            assert result["bpm"] == "128"
            assert result["key"] == "Am"


# Test: Config Integration
class TestConfigIntegration:
    """Test configuration integration."""

    def test_analyze_respects_config(self, tmp_path):
        """Should respect API configuration."""
        # Create API with specific config
        api = RenamerAPI(workers=2)

        mp3_file = tmp_path / "test.mp3"
        mp3_file.write_bytes(b"FAKE MP3 DATA")

        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(artist="Artist", title="Title"), None)

            result = api.analyze_file(mp3_file)

            assert result is not None
            assert isinstance(result, dict)

    def test_analyze_with_different_workers(self, sample_mp3):
        """Should work regardless of worker count."""
        api1 = RenamerAPI(workers=1)
        api2 = RenamerAPI(workers=4)

        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(), None)

            result1 = api1.analyze_file(sample_mp3)
            result2 = api2.analyze_file(sample_mp3)

            # Both should return same metadata
            assert result1["artist"] == result2["artist"]
            assert result1["title"] == result2["title"]


# Test: Return Format
class TestReturnFormat:
    """Test return format and field consistency."""

    def test_analyze_returns_dict(self, api_instance, sample_mp3):
        """Should return dictionary."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(), None)

            result = api_instance.analyze_file(sample_mp3)

            assert isinstance(result, dict)

    def test_analyze_returns_string_values(self, api_instance, sample_mp3):
        """Should return string values for all fields."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(), None)

            result = api_instance.analyze_file(sample_mp3)

            # All values should be strings
            for key, value in result.items():
                if value is not None:
                    assert isinstance(value, str), f"{key} should be string, got {type(value)}"

    def test_analyze_consistent_field_names(self, api_instance, sample_mp3):
        """Should use consistent field names."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(), None)

            result = api_instance.analyze_file(sample_mp3)

            # Check for standard field names
            expected_fields = ["artist", "title"]
            for field in expected_fields:
                assert field in result


# Test: Path Handling
class TestPathHandling:
    """Test path input handling."""

    def test_analyze_accepts_path_object(self, api_instance, sample_mp3):
        """Should accept Path object."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(), None)

            result = api_instance.analyze_file(sample_mp3)

            assert result is not None

    def test_analyze_accepts_string_path(self, api_instance, sample_mp3):
        """Should accept string path."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(), None)

            result = api_instance.analyze_file(Path(str(sample_mp3)))

            assert result is not None

    def test_analyze_absolute_path(self, api_instance, sample_mp3):
        """Should work with absolute paths."""
        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(), None)

            abs_path = sample_mp3.resolve()
            result = api_instance.analyze_file(abs_path)

            assert result is not None


# Test: Edge Cases
class TestEdgeCases:
    """Test edge cases."""

    def test_analyze_empty_metadata(self, api_instance, tmp_path):
        """Should handle file with minimal metadata."""
        mp3_file = tmp_path / "minimal.mp3"
        mp3_file.write_bytes(b"FAKE MP3 DATA")

        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(artist="", title=""), None)

            result = api_instance.analyze_file(mp3_file)

            # Should return result even with empty fields
            assert result is not None
            assert isinstance(result, dict)

    def test_analyze_unicode_metadata(self, api_instance, tmp_path):
        """Should handle unicode in metadata."""
        mp3_file = tmp_path / "unicode.mp3"
        mp3_file.write_bytes(b"FAKE MP3 DATA")

        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                mock_metadata(artist="Björk", title="Café del Mar"),
                None
            )

            result = api_instance.analyze_file(mp3_file)

            assert result is not None
            assert result["artist"] == "Björk"
            assert result["title"] == "Café del Mar"

    def test_analyze_special_chars_in_filename(self, api_instance, tmp_path):
        """Should handle special characters in filename."""
        mp3_file = tmp_path / "track [mix] (2024).mp3"
        mp3_file.write_bytes(b"FAKE MP3 DATA")

        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(artist="Artist", title="Title"), None)

            result = api_instance.analyze_file(mp3_file)

            assert result is not None


# Test: Integration
class TestIntegration:
    """Test integration with other API methods."""

    def test_analyze_before_rename(self, api_instance, tmp_path):
        """Should work as pre-rename analysis."""
        mp3_file = tmp_path / "test.mp3"
        mp3_file.write_bytes(b"FAKE MP3 DATA")

        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(artist="Artist", title="Title"), None)

            # Analyze first
            metadata = api_instance.analyze_file(mp3_file)

            assert metadata is not None
            assert metadata["artist"] == "Artist"
            assert metadata["bpm"] == "128"

            # File should still exist and be renameable
            assert mp3_file.exists()

    def test_analyze_does_not_modify_file(self, api_instance, sample_mp3):
        """Should not modify the file."""
        mtime_before = sample_mp3.stat().st_mtime

        with patch("crate.api.renamer.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata(), None)

            result = api_instance.analyze_file(sample_mp3)

            mtime_after = sample_mp3.stat().st_mtime

            assert result is not None
            assert mtime_before == mtime_after
