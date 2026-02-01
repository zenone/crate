"""
Musical key conversion functions (Camelot Wheel).

These are pure functions with no side effects.
"""

import re
from typing import Dict

from .sanitization import squash_spaces


PITCH_CLASS: Dict[str, int] = {
    "C": 0, "B#": 0,
    "C#": 1, "Db": 1,
    "D": 2,
    "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4,
    "E#": 5, "F": 5,
    "F#": 6, "Gb": 6,
    "G": 7,
    "G#": 8, "Ab": 8,
    "A": 9,
    "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}


_CAMELOT_MAJOR_BY_PC = {
    0: "8B", 1: "3B", 2: "10B", 3: "5B", 4: "12B", 5: "7B",
    6: "2B", 7: "9B", 8: "4B", 9: "11B", 10: "6B", 11: "1B"
}

_CAMELOT_MINOR_BY_PC = {
    0: "5A", 1: "12A", 2: "7A", 3: "2A", 4: "9A", 5: "4A",
    6: "11A", 7: "6A", 8: "1A", 9: "8A", 10: "3A", 11: "10A"
}


def normalize_key_raw(key: str) -> str:
    """
    Normalize common key strings to standard format.

    Handles:
    - Simple keys: "C", "Am", "F#", "Bb"
    - Verbose: "C major", "A minor", "G Maj", "F#min"
    - Unicode symbols: "C♯", "D♭"
    - Camelot: "1A", "12B" (passed through)

    Args:
        key: Key string in various formats

    Returns:
        Normalized key like "C", "Am", "F#m" or "" if invalid

    Examples:
        >>> normalize_key_raw("C# minor")
        'C#m'
        >>> normalize_key_raw("D major")
        'D'
        >>> normalize_key_raw("12A")
        '12A'
    """
    if not key:
        return ""

    s = squash_spaces(key)
    s = s.replace("♭", "b").replace("♯", "#")

    # If already Camelot-like, keep it
    if re.fullmatch(r"(1[0-2]|[1-9])[AB]", s.upper()):
        return s.upper()

    m = re.match(r"^([A-Ga-g])\s*([#b]?)\s*(.*)$", s)
    if not m:
        return ""

    tonic = m.group(1).upper() + m.group(2)
    rest = m.group(3).strip().lower()

    is_minor = False
    if rest:
        if "minor" in rest or re.search(r"\bmin\b", rest) or rest.endswith("m"):
            is_minor = True
        if "major" in rest or re.search(r"\bmaj\b", rest):
            if "minor" not in rest and not re.search(r"\bmin\b", rest) and not rest.endswith("m"):
                is_minor = False
    else:
        if s.strip().lower().endswith("m") and not s.strip().lower().endswith("maj"):
            is_minor = True

    if tonic not in PITCH_CLASS:
        return ""

    return f"{tonic}{'m' if is_minor else ''}"


def to_camelot(key: str) -> str:
    """
    Convert normalized key to Camelot notation.

    Args:
        key: Key string (accepts raw or normalized)

    Returns:
        Camelot notation like "5A", "12B" or "" if invalid

    Examples:
        >>> to_camelot("Am")
        '8A'
        >>> to_camelot("C major")
        '8B'
        >>> to_camelot("F#m")
        '11A'
    """
    if not key:
        return ""

    nk = normalize_key_raw(key)
    if not nk:
        return ""

    if re.fullmatch(r"(1[0-2]|[1-9])[AB]", nk):
        return nk

    minor = nk.endswith("m")
    tonic = nk[:-1] if minor else nk
    pc = PITCH_CLASS.get(tonic)

    if pc is None:
        return ""

    return (_CAMELOT_MINOR_BY_PC if minor else _CAMELOT_MAJOR_BY_PC).get(pc, "")
