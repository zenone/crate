"""
Validation functions for metadata values.

Ensures data quality before using values from tags or detection.
"""

from typing import Optional


def is_valid_bpm(bpm: str) -> bool:
    """
    Validate BPM value is within reasonable DJ range.

    Args:
        bpm: BPM value as string

    Returns:
        True if valid, False otherwise

    Examples:
        >>> is_valid_bpm("128")
        True
        >>> is_valid_bpm("999")
        False
        >>> is_valid_bpm("invalid")
        False
    """
    if not bpm or not bpm.strip():
        return False

    try:
        bpm_int = int(float(bpm))
        # Typical DJ BPM range: 60-200
        # House: 120-130, Techno: 125-135, DnB: 160-180, Dubstep: 140
        return 60 <= bpm_int <= 200
    except (ValueError, TypeError):
        return False


def is_valid_key(key: str) -> bool:
    """
    Validate musical key format.

    Accepts standard notation: "C maj", "F# min", "A major", "Db minor"
    Also accepts shorthand: "Am", "Cmaj", "F#m"

    Args:
        key: Musical key as string

    Returns:
        True if valid format, False otherwise

    Examples:
        >>> is_valid_key("C maj")
        True
        >>> is_valid_key("F# min")
        True
        >>> is_valid_key("Am")
        True
        >>> is_valid_key("XYZ")
        False
    """
    if not key or not key.strip():
        return False

    key_stripped = key.strip()
    key_lower = key_stripped.lower()

    # Valid pitch classes
    valid_pitches = [
        "c", "c#", "db", "d", "d#", "eb", "e", "f",
        "f#", "gb", "g", "g#", "ab", "a", "a#", "bb", "b"
    ]

    # Check for shorthand format (e.g., "Am", "Cmaj", "F#m")
    for pitch in valid_pitches:
        if key_lower.startswith(pitch):
            remainder = key_lower[len(pitch):]
            # Check if remainder is valid modifier
            if remainder in ["", "m", "maj", "min", "major", "minor"]:
                return True

    # Check space-separated format (e.g., "A min", "C maj")
    parts = key_lower.split()
    if len(parts) < 1 or len(parts) > 2:
        return False

    # Check pitch class
    pitch = parts[0]
    if pitch not in valid_pitches:
        return False

    # Check modifier if present
    if len(parts) == 2:
        modifier = parts[1]
        if modifier not in ["maj", "min", "major", "minor", "m"]:
            return False

    return True


def validate_and_clean_bpm(bpm: str) -> Optional[str]:
    """
    Validate BPM and return cleaned value or None if invalid.

    Args:
        bpm: BPM value to validate

    Returns:
        Cleaned BPM string or None if invalid

    Examples:
        >>> validate_and_clean_bpm("128.5")
        '129'
        >>> validate_and_clean_bpm("999")
        None
    """
    if not is_valid_bpm(bpm):
        return None

    try:
        # Round to nearest integer
        return str(int(round(float(bpm))))
    except (TypeError, ValueError):
        return None


def validate_and_clean_key(key: str) -> Optional[str]:
    """
    Validate key and return cleaned value or None if invalid.

    Args:
        key: Musical key to validate

    Returns:
        Cleaned key string or None if invalid

    Examples:
        >>> validate_and_clean_key("c major")
        'C maj'
        >>> validate_and_clean_key("XYZ")
        None
    """
    if not is_valid_key(key):
        return None

    # Normalize format
    key_lower = key.lower().strip()
    parts = key_lower.split()

    # Capitalize pitch
    pitch = parts[0][0].upper() + parts[0][1:]

    # Normalize modifier
    if len(parts) == 2:
        modifier = parts[1]
        if modifier in ["major", "maj"]:
            return f"{pitch} maj"
        elif modifier in ["minor", "min", "m"]:
            return f"{pitch} min"

    # Default to major if no modifier
    return f"{pitch} maj"
