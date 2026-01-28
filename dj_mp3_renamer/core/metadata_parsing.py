"""
Metadata parsing and normalization functions.

These are pure functions with no side effects.
"""

import math
import re

from .sanitization import squash_spaces


def extract_year(s: str) -> str:
    """
    Extract a 4-digit year (1900-2099) from a string.

    Args:
        s: Input string

    Returns:
        Year as string, or "" if not found

    Examples:
        >>> extract_year("2024-01-15")
        '2024'
        >>> extract_year("no year")
        ''
    """
    if not s:
        return ""
    m = re.search(r"\b(19\d{2}|20\d{2})\b", s)
    return m.group(1) if m else ""


def extract_track_number(s: str) -> str:
    """
    Extract and zero-pad track number from string.

    Args:
        s: Track number string (e.g., "5", "10", "5/12")

    Returns:
        Zero-padded track (e.g., "05") or "" if invalid

    Examples:
        >>> extract_track_number("5")
        '05'
        >>> extract_track_number("10/12")
        '10'
    """
    if not s:
        return ""
    m = re.match(r"^\s*(\d{1,3})", s)
    if not m:
        return ""
    n = int(m.group(1))
    if n == 0:
        return ""
    return f"{n:02d}" if 1 <= n <= 99 else str(n)


def normalize_bpm(s: str) -> str:
    """
    Normalize BPM to rounded integer.

    Args:
        s: BPM string (e.g., "128", "127.5 BPM")

    Returns:
        Rounded BPM as string, or "" if invalid

    Examples:
        >>> normalize_bpm("128")
        '128'
        >>> normalize_bpm("127.5")
        '128'
    """
    if not s:
        return ""
    try:
        v = float(str(s).strip())
        if math.isnan(v) or v <= 0 or v < 10:
            return ""
        return str(int(round(v)))
    except Exception:
        m = re.search(r"(\d{2,3}(?:\.\d+)?)", str(s))
        if not m:
            return ""
        try:
            val = float(m.group(1))
            if val < 10:
                return ""
            return str(int(round(val)))
        except Exception:
            return ""


_MIX_MARKERS = [
    "mix", "remix", "rework", "edit", "vip", "version", "bootleg", "dub",
    "extended", "radio", "club", "instrumental", "acapella",
]


def infer_mix(title: str) -> str:
    """
    Infer mix/remix/version from title string.

    Detects patterns like:
    - "(Extended Mix)"
    - "[Artist Remix]"
    - "- VIP"

    Args:
        title: Song title

    Returns:
        Mix name without brackets, or "" if not found

    Examples:
        >>> infer_mix("Title (Extended Mix)")
        'Extended Mix'
        >>> infer_mix("Title - Artist Remix")
        'Artist Remix'
    """
    if not title:
        return ""
    t = title.strip()

    m = re.search(r"[\(\[\{]\s*([^\)\]\}]{2,80})\s*[\)\]\}]\s*$", t)
    if m:
        inner = squash_spaces(m.group(1))
        if any(word in inner.lower() for word in _MIX_MARKERS):
            return inner

    m2 = re.search(r"\s[-–—]\s*([^-–—]{2,80})\s*$", t)
    if m2:
        inner = squash_spaces(m2.group(1))
        if any(word in inner.lower() for word in _MIX_MARKERS):
            return inner

    return ""


def strip_mix_from_title(title: str, mix: str) -> str:
    """
    Remove mix suffix from title.

    Args:
        title: Song title
        mix: Mix name to remove

    Returns:
        Title with mix removed

    Examples:
        >>> strip_mix_from_title("Title (Extended Mix)", "Extended Mix")
        'Title'
    """
    if not title or not mix:
        return title

    patterns = [
        rf"\s*[\(\[\{{]\s*{re.escape(mix)}\s*[\)\]\}}]\s*$",
        rf"\s[-–—]\s*{re.escape(mix)}\s*$",
    ]

    for p in patterns:
        new = re.sub(p, "", title).strip()
        if new != title:
            return new

    return title
