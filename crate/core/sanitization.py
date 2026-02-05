"""
String sanitization functions for safe cross-platform filenames.

These are pure functions with no side effects.
"""

import re
import unicodedata

_ILLEGAL_CHARS = r'[\\/:"*?<>|]'  # Windows + common POSIX troublemakers


def safe_filename(text: str, max_len: int = 140) -> str:
    """
    Normalize and sanitize arbitrary text for safe cross-platform filenames.

    - Removes control chars (0x00-0x1f)
    - Replaces illegal filename chars with spaces
    - Collapses whitespace
    - Strips trailing dots/spaces (Windows compatibility)
    - Returns "untitled" for empty/invalid input

    Args:
        text: Input string to sanitize
        max_len: Maximum length of output (default: 140)

    Returns:
        Sanitized filename string

    Examples:
        >>> safe_filename("Artist - Title.mp3")
        'Artist - Title.mp3'
        >>> safe_filename('test/file*name')
        'test file name'
        >>> safe_filename("")
        'untitled'
    """
    t = unicodedata.normalize("NFKC", (text or "")).strip()
    t = re.sub(r"[\x00-\x1f]", "", t)
    t = re.sub(_ILLEGAL_CHARS, " ", t)
    t = re.sub(r"\s+", " ", t).strip(". ").strip()
    if not t:
        t = "untitled"
    return t[:max_len]


def squash_spaces(s: str) -> str:
    """
    Collapse multiple whitespace characters into single spaces.

    Args:
        s: Input string

    Returns:
        String with whitespace normalized

    Examples:
        >>> squash_spaces("hello    world")
        'hello world'
        >>> squash_spaces("  test  ")
        'test'
    """
    return re.sub(r"\s+", " ", (s or "").strip())
