"""
Tests for metadata validation functions.
"""

import pytest
from crate.core.validation import (
    is_valid_bpm,
    is_valid_key,
    validate_and_clean_bpm,
    validate_and_clean_key,
)


class TestBPMValidation:
    """Test BPM validation logic."""

    def test_valid_bpm_in_range(self):
        """Valid BPM values should pass."""
        assert is_valid_bpm("120") is True
        assert is_valid_bpm("128") is True
        assert is_valid_bpm("140") is True
        assert is_valid_bpm("174") is True  # DnB

    def test_valid_bpm_edge_cases(self):
        """Edge cases should be handled correctly."""
        assert is_valid_bpm("60") is True   # Lower bound
        assert is_valid_bpm("200") is True  # Upper bound
        assert is_valid_bpm("59") is False  # Below range
        assert is_valid_bpm("201") is False # Above range

    def test_invalid_bpm_out_of_range(self):
        """Out-of-range BPM values should fail."""
        assert is_valid_bpm("999") is False
        assert is_valid_bpm("0") is False
        assert is_valid_bpm("-10") is False

    def test_invalid_bpm_format(self):
        """Invalid formats should fail."""
        assert is_valid_bpm("") is False
        assert is_valid_bpm("   ") is False
        assert is_valid_bpm("abc") is False
        assert is_valid_bpm("12.5.3") is False

    def test_clean_bpm_rounds_decimals(self):
        """Decimal BPM values should be rounded."""
        assert validate_and_clean_bpm("127.5") == "128"
        assert validate_and_clean_bpm("127.4") == "127"
        assert validate_and_clean_bpm("128.0") == "128"

    def test_clean_bpm_rejects_invalid(self):
        """Invalid BPM should return None."""
        assert validate_and_clean_bpm("999") is None
        assert validate_and_clean_bpm("abc") is None
        assert validate_and_clean_bpm("") is None


class TestKeyValidation:
    """Test musical key validation logic."""

    def test_valid_keys_major(self):
        """Valid major keys should pass."""
        assert is_valid_key("C maj") is True
        assert is_valid_key("F# maj") is True
        assert is_valid_key("Bb major") is True

    def test_valid_keys_minor(self):
        """Valid minor keys should pass."""
        assert is_valid_key("A min") is True
        assert is_valid_key("F# min") is True
        assert is_valid_key("Eb minor") is True

    def test_valid_keys_all_pitches(self):
        """All 12 pitch classes should be valid."""
        pitches = ["C", "C#", "D", "D#", "E", "F",
                   "F#", "G", "G#", "A", "A#", "B"]
        for pitch in pitches:
            assert is_valid_key(f"{pitch} maj") is True
            assert is_valid_key(f"{pitch} min") is True

    def test_invalid_keys(self):
        """Invalid key formats should fail."""
        assert is_valid_key("XYZ") is False
        assert is_valid_key("") is False
        assert is_valid_key("   ") is False
        assert is_valid_key("H major") is False  # H not in English notation
        assert is_valid_key("C super") is False  # Invalid modifier

    def test_clean_key_normalizes_format(self):
        """Key cleaning should normalize format."""
        assert validate_and_clean_key("c major") == "C maj"
        assert validate_and_clean_key("f# minor") == "F# min"
        assert validate_and_clean_key("Bb maj") == "Bb maj"

    def test_clean_key_rejects_invalid(self):
        """Invalid keys should return None."""
        assert validate_and_clean_key("XYZ") is None
        assert validate_and_clean_key("") is None
        assert validate_and_clean_key("H major") is None
