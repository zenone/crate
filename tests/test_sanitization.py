"""
Tests for sanitization module (RED phase - tests written first).
"""

from crate.core.sanitization import safe_filename, squash_spaces


class TestSafeFilename:
    """Test safe_filename function."""

    def test_basic_ascii(self):
        assert safe_filename("hello world") == "hello world"

    def test_illegal_chars_replaced(self):
        """Windows illegal chars: \\ / : * ? " < > |"""
        assert safe_filename('test\\file') == "test file"
        assert safe_filename('test/file') == "test file"
        assert safe_filename('test:file') == "test file"
        assert safe_filename('test*file') == "test file"
        assert safe_filename('test?file') == "test file"
        assert safe_filename('test"file') == "test file"
        assert safe_filename('test<file') == "test file"
        assert safe_filename('test>file') == "test file"
        assert safe_filename('test|file') == "test file"

    def test_control_chars_removed(self):
        """Control characters (0x00-0x1f) should be removed."""
        assert safe_filename("test\x00file") == "testfile"
        assert safe_filename("test\nfile") == "testfile"
        assert safe_filename("test\rfile") == "testfile"
        assert safe_filename("test\tfile") == "testfile"

    def test_unicode_normalization(self):
        """Unicode should be normalized to NFKC."""
        # Combining characters should be normalized
        assert safe_filename("café") == "café"  # Should normalize
        assert safe_filename("ﬁle") == "file"  # Ligature fi -> f i

    def test_whitespace_collapse(self):
        """Multiple spaces should collapse to single space."""
        assert safe_filename("test    file") == "test file"
        assert safe_filename("test  \t  file") == "test file"

    def test_trailing_dots_stripped(self):
        """Windows doesn't allow trailing dots."""
        assert safe_filename("test.") == "test"
        assert safe_filename("test...") == "test"

    def test_trailing_spaces_stripped(self):
        """Trailing and leading spaces should be stripped."""
        assert safe_filename("  test  ") == "test"
        assert safe_filename("test ") == "test"

    def test_empty_string_returns_untitled(self):
        """Empty string should return 'untitled'."""
        assert safe_filename("") == "untitled"
        assert safe_filename("   ") == "untitled"
        assert safe_filename("...") == "untitled"

    def test_max_length_default(self):
        """Default max length is 140 characters."""
        long_name = "a" * 200
        result = safe_filename(long_name)
        assert len(result) == 140
        assert result == "a" * 140

    def test_max_length_custom(self):
        """Custom max length should be respected."""
        long_name = "a" * 100
        result = safe_filename(long_name, max_len=50)
        assert len(result) == 50
        assert result == "a" * 50

    def test_none_input(self):
        """None input should be treated as empty string."""
        assert safe_filename(None) == "untitled"  # type: ignore

    def test_mixed_illegal_chars(self):
        """Multiple illegal chars should all be replaced."""
        assert safe_filename('a\\b/c:d*e?f"g<h>i|j') == "a b c d e f g h i j"

    def test_real_world_example(self):
        """Test a realistic DJ filename with problematic chars."""
        input_name = 'Artist - Title (Remix) [12A 128] "2024"'
        expected = 'Artist - Title (Remix) [12A 128] 2024'
        assert safe_filename(input_name) == expected

    def test_only_illegal_chars(self):
        """If input is only illegal chars, should return untitled."""
        assert safe_filename('\\/:*?"<>|') == "untitled"

    def test_trailing_dot_and_space_combo(self):
        """Both trailing dots and spaces should be stripped."""
        assert safe_filename("test. . ") == "test"


class TestSquashSpaces:
    """Test squash_spaces function."""

    def test_basic_squash(self):
        assert squash_spaces("hello  world") == "hello world"

    def test_multiple_spaces(self):
        assert squash_spaces("a    b    c") == "a b c"

    def test_tabs_and_spaces(self):
        assert squash_spaces("a\t\tb\t c") == "a b c"

    def test_leading_trailing_spaces(self):
        assert squash_spaces("  hello  ") == "hello"

    def test_empty_string(self):
        assert squash_spaces("") == ""

    def test_none_input(self):
        """None input should be treated as empty string."""
        assert squash_spaces(None) == ""  # type: ignore
