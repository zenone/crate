"""Tests for greeter module - TDD style."""

import pytest
from src.core.greeter import greet


class TestGreet:
    """Test the greet function."""

    def test_greet_returns_hello_with_name(self):
        """Basic greeting includes name."""
        assert greet("Alice") == "Hello, Alice!"

    def test_greet_formal_uses_formal_greeting(self):
        """Formal mode uses different greeting."""
        result = greet("Alice", formal=True)
        assert "Good day" in result
        assert "Alice" in result

    def test_greet_strips_whitespace(self):
        """Names are trimmed."""
        assert greet("  Bob  ") == "Hello, Bob!"

    def test_greet_empty_name_raises_error(self):
        """Empty names are rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            greet("")

    def test_greet_whitespace_only_raises_error(self):
        """Whitespace-only names are rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            greet("   ")
