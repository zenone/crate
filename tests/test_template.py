"""
Tests for template module (RED phase - tests written first).
"""

import pytest
from dj_mp3_renamer.core.template import (
    build_filename_from_template,
    build_default_components,
    DEFAULT_TEMPLATE,
)


class TestBuildFilenameFromTemplate:
    """Test build_filename_from_template function."""

    def test_simple_expansion(self):
        meta = {"artist": "DJ Test", "title": "Song"}
        template = "{artist} - {title}"
        assert build_filename_from_template(meta, template) == "DJ Test - Song"

    def test_missing_token_left_intact(self):
        """Unknown tokens should remain unchanged."""
        meta = {"artist": "DJ Test"}
        template = "{artist} - {unknown}"
        assert build_filename_from_template(meta, template) == "DJ Test - {unknown}"

    def test_empty_token_replaced(self):
        """Tokens with empty values should be replaced with empty string."""
        meta = {"artist": "DJ Test", "title": ""}
        template = "{artist} - {title}"
        assert build_filename_from_template(meta, template) == "DJ Test - "

    def test_multiple_same_token(self):
        """Same token can appear multiple times."""
        meta = {"artist": "DJ Test"}
        template = "{artist} by {artist}"
        assert build_filename_from_template(meta, template) == "DJ Test by DJ Test"

    def test_no_tokens(self):
        """Template with no tokens should be unchanged."""
        meta = {"artist": "DJ Test"}
        template = "static filename"
        assert build_filename_from_template(meta, template) == "static filename"


class TestBuildDefaultComponents:
    """Test build_default_components function."""

    def test_full_metadata(self):
        """Test with all metadata present."""
        meta = {
            "artist": "DJ Test",
            "title": "Song Title",
            "mix": "Extended Mix",
            "bpm": "128",
            "key": "Am",
            "camelot": "8A",
            "year": "2024",
            "label": "Test Records",
            "track": "01",
            "album": "Test Album",
        }
        result = build_default_components(meta)

        assert result["artist"] == "DJ Test"
        assert result["title"] == "Song Title"
        assert result["mix"] == "Extended Mix"
        assert result["mix_paren"] == " (Extended Mix)"
        assert result["kb"] == " [8A 128]"
        assert result["bpm"] == "128"
        assert result["camelot"] == "8A"

    def test_missing_artist_gets_default(self):
        """Missing artist should default to 'Unknown Artist'."""
        meta = {"title": "Song"}
        result = build_default_components(meta)
        assert result["artist"] == "Unknown Artist"

    def test_missing_title_gets_default(self):
        """Missing title should default to 'Unknown Title'."""
        meta = {"artist": "DJ Test"}
        result = build_default_components(meta)
        assert result["title"] == "Unknown Title"

    def test_no_mix_no_paren(self):
        """No mix should result in empty mix_paren."""
        meta = {"artist": "DJ Test", "title": "Song"}
        result = build_default_components(meta)
        assert result["mix"] == ""
        assert result["mix_paren"] == ""

    def test_no_key_bpm_no_kb(self):
        """No key/BPM should result in empty kb."""
        meta = {"artist": "DJ Test", "title": "Song"}
        result = build_default_components(meta)
        assert result["kb"] == ""

    def test_only_key_in_kb(self):
        """Only key should appear in kb."""
        meta = {"artist": "DJ Test", "title": "Song", "key": "Cm"}
        result = build_default_components(meta)
        assert result["kb"] == " [Cm]"

    def test_only_bpm_in_kb(self):
        """Only BPM should appear in kb."""
        meta = {"artist": "DJ Test", "title": "Song", "bpm": "140"}
        result = build_default_components(meta)
        assert result["kb"] == " [140]"

    def test_camelot_preferred_over_key(self):
        """Camelot should be preferred over raw key."""
        meta = {
            "artist": "DJ Test",
            "title": "Song",
            "key": "Am",
            "camelot": "8A",
            "bpm": "128"
        }
        result = build_default_components(meta)
        assert "8A" in result["kb"]
        assert "Am" not in result["kb"]

    def test_mix_stripped_from_title(self):
        """Mix should be removed from title."""
        meta = {
            "artist": "DJ Test",
            "title": "Song (Extended Mix)",
            "mix": "Extended Mix"
        }
        result = build_default_components(meta)
        assert result["title"] == "Song"
        assert result["mix"] == "Extended Mix"


class TestDefaultTemplate:
    """Test DEFAULT_TEMPLATE constant."""

    def test_default_template_defined(self):
        """DEFAULT_TEMPLATE should be defined."""
        assert DEFAULT_TEMPLATE is not None
        assert isinstance(DEFAULT_TEMPLATE, str)
        assert len(DEFAULT_TEMPLATE) > 0
