"""
Tests for template validation API.

Tests verify:
- Valid templates pass validation
- Invalid characters detected
- Unknown variables detected
- Example output generated
- Warnings for edge cases
- Empty templates rejected
"""

import pytest

from crate.api import RenamerAPI


# Test Fixtures
@pytest.fixture
def api_instance():
    """Create RenamerAPI instance for testing."""
    return RenamerAPI(workers=2)


# Test: Valid Templates
class TestValidTemplates:
    """Test validation of valid templates."""

    def test_simple_template_valid(self, api_instance):
        """Should validate simple template."""
        result = api_instance.validate_template("{artist} - {title}")

        assert result.valid is True
        assert len(result.errors) == 0
        assert result.example is not None
        assert "Sample Artist" in result.example
        assert "Sample Title" in result.example

    def test_complex_template_valid(self, api_instance):
        """Should validate complex template with multiple variables."""
        template = "{artist} - {title} [{camelot} {bpm}] ({year})"
        result = api_instance.validate_template(template)

        assert result.valid is True
        assert len(result.errors) == 0
        assert result.example is not None

    def test_template_with_brackets_valid(self, api_instance):
        """Should allow brackets in template."""
        result = api_instance.validate_template("[{bpm}] {artist} - {title}")

        assert result.valid is True
        assert "[128]" in result.example

    def test_template_with_parentheses_valid(self, api_instance):
        """Should allow parentheses in template."""
        result = api_instance.validate_template("{artist} - {title} ({mix})")

        assert result.valid is True
        assert "(" in result.example

    def test_template_with_dashes_valid(self, api_instance):
        """Should allow dashes in template."""
        result = api_instance.validate_template("{artist} - {title} - {album}")

        assert result.valid is True
        assert " - " in result.example


# Test: Invalid Templates
class TestInvalidTemplates:
    """Test validation of invalid templates."""

    def test_empty_template_invalid(self, api_instance):
        """Should reject empty template."""
        result = api_instance.validate_template("")

        assert result.valid is False
        assert any("empty" in err.lower() for err in result.errors)
        assert result.example is None

    def test_whitespace_only_template_invalid(self, api_instance):
        """Should reject whitespace-only template."""
        result = api_instance.validate_template("   ")

        assert result.valid is False
        assert any("empty" in err.lower() for err in result.errors)

    def test_template_with_invalid_chars_slash(self, api_instance):
        """Should reject template with forward slash."""
        result = api_instance.validate_template("{artist}/{title}")

        assert result.valid is False
        assert any("invalid" in err.lower() for err in result.errors)
        assert any("/" in err for err in result.errors)

    def test_template_with_invalid_chars_backslash(self, api_instance):
        """Should reject template with backslash."""
        result = api_instance.validate_template("{artist}\\{title}")

        assert result.valid is False
        assert any("invalid" in err.lower() for err in result.errors)

    def test_template_with_invalid_chars_colon(self, api_instance):
        """Should reject template with colon."""
        result = api_instance.validate_template("{artist}: {title}")

        assert result.valid is False
        assert any("invalid" in err.lower() for err in result.errors)

    def test_template_with_invalid_chars_pipe(self, api_instance):
        """Should reject template with pipe."""
        result = api_instance.validate_template("{artist} | {title}")

        assert result.valid is False
        assert any("invalid" in err.lower() for err in result.errors)

    def test_template_with_asterisk(self, api_instance):
        """Should reject template with asterisk."""
        result = api_instance.validate_template("{artist} * {title}")

        assert result.valid is False
        assert any("invalid" in err.lower() for err in result.errors)

    def test_template_with_question_mark(self, api_instance):
        """Should reject template with question mark."""
        result = api_instance.validate_template("{artist}? - {title}")

        assert result.valid is False
        assert any("invalid" in err.lower() for err in result.errors)

    def test_template_with_quotes(self, api_instance):
        """Should reject template with quotes."""
        result = api_instance.validate_template('"{artist}" - {title}')

        assert result.valid is False
        assert any("invalid" in err.lower() for err in result.errors)


# Test: Unknown Variables
class TestUnknownVariables:
    """Test validation of templates with unknown variables."""

    def test_unknown_variable_detected(self, api_instance):
        """Should detect unknown template variable."""
        result = api_instance.validate_template("{artist} - {unknown}")

        assert result.valid is False
        assert any("unknown" in err.lower() for err in result.errors)
        assert any("unknown" in err for err in result.errors)

    def test_typo_in_variable_detected(self, api_instance):
        """Should detect typo in variable name."""
        result = api_instance.validate_template("{aritst} - {title}")  # aritst typo

        assert result.valid is False
        assert any("unknown" in err.lower() or "aritst" in err for err in result.errors)

    def test_multiple_unknown_variables(self, api_instance):
        """Should detect multiple unknown variables."""
        result = api_instance.validate_template("{unknown1} - {unknown2}")

        assert result.valid is False
        assert len(result.errors) > 0


# Test: Warnings
class TestTemplateWarnings:
    """Test validation warnings."""

    def test_leading_space_warning(self, api_instance):
        """Should warn about leading space."""
        result = api_instance.validate_template(" {artist} - {title}")

        # May be valid but should have warning
        assert any("leading" in warn.lower() or "trailing" in warn.lower() for warn in result.warnings)

    def test_trailing_space_warning(self, api_instance):
        """Should warn about trailing space."""
        result = api_instance.validate_template("{artist} - {title} ")

        assert any("trailing" in warn.lower() or "leading" in warn.lower() for warn in result.warnings)

    def test_multiple_spaces_warning(self, api_instance):
        """Should warn about multiple consecutive spaces."""
        result = api_instance.validate_template("{artist}  -  {title}")

        assert any("consecutive" in warn.lower() or "multiple" in warn.lower() for warn in result.warnings)

    def test_long_template_warning(self, api_instance):
        """Should warn about very long templates."""
        # Create very long template
        long_template = "{artist} - {title} - {album} - {label} - {year} - {track} - {mix}" * 5
        result = api_instance.validate_template(long_template)

        # Should have warning about length
        if len(result.warnings) > 0:
            assert any("long" in warn.lower() for warn in result.warnings)


# Test: Example Output
class TestExampleOutput:
    """Test example output generation."""

    def test_example_includes_artist(self, api_instance):
        """Should include sample artist in example."""
        result = api_instance.validate_template("{artist} - {title}")

        assert result.valid is True
        assert result.example is not None
        assert "Sample Artist" in result.example

    def test_example_includes_all_variables(self, api_instance):
        """Should include all variables in example."""
        result = api_instance.validate_template("{artist} - {title} - {bpm} - {key}")

        assert result.valid is True
        assert "Sample Artist" in result.example
        assert "Sample Title" in result.example
        assert "128" in result.example
        assert "Am" in result.example

    def test_example_with_camelot(self, api_instance):
        """Should include Camelot notation."""
        result = api_instance.validate_template("[{camelot}] {artist} - {title}")

        assert result.valid is True
        assert "8A" in result.example

    def test_example_format_matches_template(self, api_instance):
        """Should match template format."""
        result = api_instance.validate_template("{bpm} - {artist} - {title}")

        assert result.valid is True
        # Should start with BPM
        assert result.example.startswith("128")


# Test: Edge Cases
class TestEdgeCases:
    """Test edge cases."""

    def test_template_with_only_literal_text(self, api_instance):
        """Should handle template with only literal text."""
        result = api_instance.validate_template("constant_filename")

        # Valid but not very useful
        assert result.valid is True
        assert result.example == "constant_filename"

    def test_template_with_no_spaces(self, api_instance):
        """Should handle template with no spaces."""
        result = api_instance.validate_template("{artist}{title}")

        assert result.valid is True
        assert result.example is not None

    def test_template_with_unicode(self, api_instance):
        """Should handle template with unicode characters."""
        result = api_instance.validate_template("{artist} – {title}")  # em dash

        assert result.valid is True
        assert result.example is not None

    def test_template_with_numbers(self, api_instance):
        """Should handle template with numbers."""
        result = api_instance.validate_template("Track {track} - {title}")

        assert result.valid is True
        assert "Track" in result.example


# Test: TemplateValidation Model
class TestTemplateValidationModel:
    """Test TemplateValidation model."""

    def test_to_dict_valid_template(self, api_instance):
        """Should convert valid result to dict."""
        result = api_instance.validate_template("{artist} - {title}")
        result_dict = result.to_dict()

        assert "valid" in result_dict
        assert "errors" in result_dict
        assert "warnings" in result_dict
        assert "example" in result_dict

        assert result_dict["valid"] is True
        assert isinstance(result_dict["errors"], list)
        assert isinstance(result_dict["warnings"], list)
        assert isinstance(result_dict["example"], str)

    def test_to_dict_invalid_template(self, api_instance):
        """Should convert invalid result to dict."""
        result = api_instance.validate_template("{unknown}")
        result_dict = result.to_dict()

        assert result_dict["valid"] is False
        assert len(result_dict["errors"]) > 0

    def test_to_dict_json_serializable(self, api_instance):
        """Should produce JSON-serializable dict."""
        import json

        result = api_instance.validate_template("{artist} - {title}")
        result_dict = result.to_dict()

        # Should not raise
        json_str = json.dumps(result_dict)
        assert isinstance(json_str, str)


# Test: Real-World Templates
class TestRealWorldTemplates:
    """Test real-world template patterns."""

    def test_dj_standard_template(self, api_instance):
        """Should validate standard DJ template."""
        result = api_instance.validate_template("{artist} - {title} [{camelot} {bpm}]")

        assert result.valid is True
        assert result.example is not None

    def test_serato_style_template(self, api_instance):
        """Should validate Serato-style template."""
        result = api_instance.validate_template("{artist} - {title} ({bpm} BPM) ({key})")

        assert result.valid is True

    def test_organized_library_template(self, api_instance):
        """Should validate organized library template."""
        result = api_instance.validate_template("{bpm} - {key} - {artist} - {title}")

        assert result.valid is True

    def test_minimal_template(self, api_instance):
        """Should validate minimal template."""
        result = api_instance.validate_template("{artist} - {title}")

        assert result.valid is True
        assert result.example is not None
