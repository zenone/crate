"""
Tests for key conversion module (RED phase - tests written first).
"""

import pytest
from crate.core.key_conversion import normalize_key_raw, to_camelot, PITCH_CLASS


class TestNormalizeKeyRaw:
    """Test normalize_key_raw function."""

    def test_empty_string(self):
        assert normalize_key_raw("") == ""

    def test_major_keys_simple(self):
        assert normalize_key_raw("C") == "C"
        assert normalize_key_raw("D") == "D"
        assert normalize_key_raw("E") == "E"
        assert normalize_key_raw("F") == "F"
        assert normalize_key_raw("G") == "G"
        assert normalize_key_raw("A") == "A"
        assert normalize_key_raw("B") == "B"

    def test_minor_keys_simple(self):
        assert normalize_key_raw("Cm") == "Cm"
        assert normalize_key_raw("Dm") == "Dm"
        assert normalize_key_raw("Am") == "Am"

    def test_sharps(self):
        assert normalize_key_raw("C#") == "C#"
        assert normalize_key_raw("F#") == "F#"
        assert normalize_key_raw("G#") == "G#"

    def test_flats(self):
        assert normalize_key_raw("Db") == "Db"
        assert normalize_key_raw("Eb") == "Eb"
        assert normalize_key_raw("Bb") == "Bb"

    def test_minor_with_sharps_flats(self):
        assert normalize_key_raw("C#m") == "C#m"
        assert normalize_key_raw("Bbm") == "Bbm"

    def test_verbose_minor(self):
        assert normalize_key_raw("C minor") == "Cm"
        assert normalize_key_raw("D minor") == "Dm"
        assert normalize_key_raw("A minor") == "Am"

    def test_verbose_major(self):
        assert normalize_key_raw("C major") == "C"
        assert normalize_key_raw("D major") == "D"
        assert normalize_key_raw("G Maj") == "G"

    def test_min_abbreviation(self):
        assert normalize_key_raw("Cmin") == "Cm"
        assert normalize_key_raw("F#min") == "F#m"

    def test_whitespace_handling(self):
        assert normalize_key_raw("C  major") == "C"
        assert normalize_key_raw("  Am  ") == "Am"
        assert normalize_key_raw("C # m") == "C#m"

    def test_unicode_symbols(self):
        """Test musical symbols (sharp ♯, flat ♭)."""
        assert normalize_key_raw("C♯") == "C#"
        assert normalize_key_raw("D♭") == "Db"
        assert normalize_key_raw("F♯m") == "F#m"

    def test_already_camelot(self):
        """Camelot notation should be preserved."""
        assert normalize_key_raw("1A") == "1A"
        assert normalize_key_raw("12B") == "12B"
        assert normalize_key_raw("5a") == "5A"

    def test_invalid_key(self):
        assert normalize_key_raw("X") == ""
        assert normalize_key_raw("123") == ""
        assert normalize_key_raw("random") == ""


class TestToCamelot:
    """Test to_camelot function."""

    def test_empty_string(self):
        assert to_camelot("") == ""

    def test_major_keys_camelot(self):
        """Test all 12 major keys."""
        assert to_camelot("C") == "8B"
        assert to_camelot("Db") == "3B"
        assert to_camelot("D") == "10B"
        assert to_camelot("Eb") == "5B"
        assert to_camelot("E") == "12B"
        assert to_camelot("F") == "7B"
        assert to_camelot("F#") == "2B"
        assert to_camelot("G") == "9B"
        assert to_camelot("Ab") == "4B"
        assert to_camelot("A") == "11B"
        assert to_camelot("Bb") == "6B"
        assert to_camelot("B") == "1B"

    def test_minor_keys_camelot(self):
        """Test all 12 minor keys."""
        assert to_camelot("Cm") == "5A"
        assert to_camelot("C#m") == "12A"
        assert to_camelot("Dm") == "7A"
        assert to_camelot("Ebm") == "2A"
        assert to_camelot("Em") == "9A"
        assert to_camelot("Fm") == "4A"
        assert to_camelot("F#m") == "11A"
        assert to_camelot("Gm") == "6A"
        assert to_camelot("G#m") == "1A"
        assert to_camelot("Am") == "8A"
        assert to_camelot("Bbm") == "3A"
        assert to_camelot("Bm") == "10A"

    def test_enharmonic_equivalents(self):
        """C# and Db should map to same Camelot."""
        assert to_camelot("C#") == to_camelot("Db")
        assert to_camelot("F#") == to_camelot("Gb")

    def test_verbose_notation(self):
        """Should work with verbose key names."""
        assert to_camelot("C minor") == "5A"
        assert to_camelot("D major") == "10B"

    def test_already_camelot(self):
        """Already Camelot notation should pass through."""
        assert to_camelot("1A") == "1A"
        assert to_camelot("12B") == "12B"

    def test_invalid_key(self):
        assert to_camelot("X") == ""
        assert to_camelot("invalid") == ""


class TestPitchClass:
    """Test PITCH_CLASS constant."""

    def test_pitch_class_exists(self):
        """PITCH_CLASS should be a dict."""
        assert isinstance(PITCH_CLASS, dict)

    def test_pitch_class_has_12_unique_values(self):
        """Should have 12 unique pitch classes (0-11)."""
        values = set(PITCH_CLASS.values())
        assert values == set(range(12))

    def test_pitch_class_enharmonics(self):
        """Enharmonic equivalents should have same pitch class."""
        assert PITCH_CLASS["C#"] == PITCH_CLASS["Db"]
        assert PITCH_CLASS["F#"] == PITCH_CLASS["Gb"]
        assert PITCH_CLASS["B#"] == PITCH_CLASS["C"]
