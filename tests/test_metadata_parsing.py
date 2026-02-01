"""
Tests for metadata parsing module (RED phase - tests written first).
"""

import pytest
from crate.core.metadata_parsing import (
    extract_year,
    extract_track_number,
    normalize_bpm,
    infer_mix,
    strip_mix_from_title,
)


class TestExtractYear:
    """Test extract_year function."""

    def test_empty_string(self):
        assert extract_year("") == ""

    def test_four_digit_year_20xx(self):
        assert extract_year("2024") == "2024"
        assert extract_year("2000") == "2000"
        assert extract_year("2099") == "2099"

    def test_four_digit_year_19xx(self):
        assert extract_year("1999") == "1999"
        assert extract_year("1900") == "1900"

    def test_year_in_middle(self):
        assert extract_year("Released in 2023 on Spotify") == "2023"

    def test_year_with_dashes(self):
        assert extract_year("2024-01-15") == "2024"

    def test_no_year(self):
        assert extract_year("no year here") == ""
        assert extract_year("123") == ""

    def test_invalid_year_1800s(self):
        """Years before 1900 should not match."""
        assert extract_year("1850") == ""

    def test_invalid_year_2100s(self):
        """Years after 2099 should not match."""
        assert extract_year("2100") == ""

    def test_first_year_wins(self):
        """If multiple years, first one wins."""
        assert extract_year("1999 2024") == "1999"


class TestExtractTrackNumber:
    """Test extract_track_number function."""

    def test_empty_string(self):
        assert extract_track_number("") == ""

    def test_single_digit(self):
        assert extract_track_number("1") == "01"
        assert extract_track_number("9") == "09"

    def test_double_digit(self):
        assert extract_track_number("10") == "10"
        assert extract_track_number("99") == "99"

    def test_triple_digit(self):
        """Three digit tracks should be preserved as-is."""
        assert extract_track_number("100") == "100"
        assert extract_track_number("123") == "123"

    def test_with_total_tracks(self):
        """Format like '5/12' should extract just the track."""
        assert extract_track_number("5/12") == "05"
        assert extract_track_number("10/12") == "10"

    def test_zero_track(self):
        """Track 0 is invalid."""
        assert extract_track_number("0") == ""

    def test_leading_spaces(self):
        assert extract_track_number("  5") == "05"

    def test_no_leading_digit(self):
        assert extract_track_number("no number") == ""

    def test_number_not_at_start(self):
        """Number must be at start."""
        assert extract_track_number("track 5") == ""


class TestNormalizeBpm:
    """Test normalize_bpm function."""

    def test_empty_string(self):
        assert normalize_bpm("") == ""

    def test_integer_bpm(self):
        assert normalize_bpm("128") == "128"
        assert normalize_bpm("140") == "140"

    def test_float_bpm_rounds(self):
        assert normalize_bpm("127.5") == "128"
        assert normalize_bpm("128.4") == "128"
        assert normalize_bpm("128.6") == "129"

    def test_bpm_with_text(self):
        """Should extract BPM from text."""
        assert normalize_bpm("128 BPM") == "128"
        assert normalize_bpm("BPM: 140.5") == "140"

    def test_negative_bpm(self):
        assert normalize_bpm("-120") == ""

    def test_zero_bpm(self):
        assert normalize_bpm("0") == ""

    def test_invalid_bpm(self):
        assert normalize_bpm("abc") == ""
        assert normalize_bpm("not a number") == ""

    def test_very_small_bpm(self):
        """Single digit BPMs are not realistic."""
        assert normalize_bpm("5") == ""

    def test_realistic_range(self):
        """Typical DJ BPMs: 60-200."""
        assert normalize_bpm("60") == "60"
        assert normalize_bpm("200") == "200"


class TestInferMix:
    """Test infer_mix function."""

    def test_empty_string(self):
        assert infer_mix("") == ""

    def test_no_mix(self):
        assert infer_mix("Regular Title") == ""

    def test_mix_in_parens(self):
        assert infer_mix("Title (Extended Mix)") == "Extended Mix"
        assert infer_mix("Title (Radio Edit)") == "Radio Edit"

    def test_mix_in_brackets(self):
        assert infer_mix("Title [Club Mix]") == "Club Mix"

    def test_mix_in_braces(self):
        assert infer_mix("Title {Dub Mix}") == "Dub Mix"

    def test_remix(self):
        assert infer_mix("Title (Artist Remix)") == "Artist Remix"

    def test_vip(self):
        assert infer_mix("Title (VIP)") == "VIP"

    def test_with_dash_separator(self):
        assert infer_mix("Title - Extended Mix") == "Extended Mix"
        assert infer_mix("Title - Artist Remix") == "Artist Remix"

    def test_not_a_mix_in_parens(self):
        """Year or label in parens should not be detected."""
        assert infer_mix("Title (2024)") == ""
        assert infer_mix("Title (Label Records)") == ""

    def test_case_insensitive(self):
        assert infer_mix("Title (EXTENDED MIX)") != ""
        assert infer_mix("Title (extended mix)") != ""

    def test_multiple_markers(self):
        """Should detect if any marker is present."""
        assert infer_mix("Title (Acapella)") == "Acapella"
        assert infer_mix("Title (Instrumental)") == "Instrumental"

    def test_preserves_spacing(self):
        result = infer_mix("Title (  Extended   Mix  )")
        assert result == "Extended Mix"  # Spaces should be squashed


class TestStripMixFromTitle:
    """Test strip_mix_from_title function."""

    def test_empty_title(self):
        assert strip_mix_from_title("", "Extended Mix") == ""

    def test_empty_mix(self):
        assert strip_mix_from_title("Title", "") == "Title"

    def test_strip_parens(self):
        title = "Title (Extended Mix)"
        mix = "Extended Mix"
        assert strip_mix_from_title(title, mix) == "Title"

    def test_strip_brackets(self):
        title = "Title [Club Mix]"
        mix = "Club Mix"
        assert strip_mix_from_title(title, mix) == "Title"

    def test_strip_dash(self):
        title = "Title - Artist Remix"
        mix = "Artist Remix"
        assert strip_mix_from_title(title, mix) == "Title"

    def test_mix_not_present(self):
        """If mix not in title, return unchanged."""
        assert strip_mix_from_title("Title", "Extended Mix") == "Title"

    def test_whitespace_handling(self):
        """Trailing whitespace should be cleaned."""
        title = "Title  (Extended Mix)"
        mix = "Extended Mix"
        result = strip_mix_from_title(title, mix)
        assert result == "Title"
