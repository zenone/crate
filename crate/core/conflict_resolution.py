"""
Conflict resolution for metadata from multiple sources.

When different sources disagree, uses confidence-based logic to pick best value.
"""

from typing import Any, Dict, Optional


def compare_bpm_values(bpm1: str, bpm2: str) -> Dict[str, Any]:
    """
    Compare two BPM values and detect differences.

    Args:
        bpm1: First BPM value
        bpm2: Second BPM value

    Returns:
        Dictionary with comparison results

    Examples:
        >>> compare_bpm_values("128", "127")
        {'matches': False, 'difference_percent': 0.78, ...}
    """
    try:
        val1 = float(bpm1)
        val2 = float(bpm2)
    except (ValueError, TypeError):
        return {
            "matches": False,
            "difference_percent": 0,
            "error": "Invalid BPM values for comparison"
        }

    # Calculate percentage difference
    diff = abs(val1 - val2)
    avg = (val1 + val2) / 2
    diff_percent = (diff / avg) * 100 if avg > 0 else 0

    # Check for double/half tempo (common detection error)
    is_double = abs(val1 - (val2 * 2)) < 2
    is_half = abs(val2 - (val1 * 2)) < 2

    return {
        "matches": diff < 1,  # Within 1 BPM
        "difference": diff,
        "difference_percent": diff_percent,
        "possible_double_tempo": is_double,
        "possible_half_tempo": is_half,
    }


def compare_key_values(key1: str, key2: str) -> Dict[str, Any]:
    """
    Compare two musical key values.

    Args:
        key1: First key value
        key2: Second key value

    Returns:
        Dictionary with comparison results

    Examples:
        >>> compare_key_values("C maj", "C min")
        {'matches': False, 'enharmonic': False}
    """
    # Normalize for comparison
    k1 = key1.lower().strip()
    k2 = key2.lower().strip()

    # Direct match
    if k1 == k2:
        return {"matches": True, "enharmonic": False}

    # Check for enharmonic equivalents
    enharmonic_map = {
        "c#": "db", "d#": "eb", "f#": "gb",
        "g#": "ab", "a#": "bb"
    }

    # Extract pitch and modifier
    parts1 = k1.split()
    parts2 = k2.split()

    if len(parts1) >= 1 and len(parts2) >= 1:
        pitch1 = parts1[0]
        pitch2 = parts2[0]

        # Check if enharmonic
        for sharp, flat in enharmonic_map.items():
            if (pitch1 == sharp and pitch2 == flat) or (pitch1 == flat and pitch2 == sharp):
                # Same modifier?
                mod1 = parts1[1] if len(parts1) > 1 else "maj"
                mod2 = parts2[1] if len(parts2) > 1 else "maj"
                if mod1 == mod2:
                    return {"matches": True, "enharmonic": True}

    return {"matches": False, "enharmonic": False}


def should_use_musicbrainz_value(
    tag_value: str,
    mb_value: str,
    mb_confidence: float,
    confidence_threshold: float = 0.85
) -> bool:
    """
    Decide if MusicBrainz value should override tag value.

    Args:
        tag_value: Value from ID3 tags
        mb_value: Value from MusicBrainz
        mb_confidence: Confidence score (0.0-1.0)
        confidence_threshold: Minimum confidence to override tags

    Returns:
        True if should use MusicBrainz value

    Examples:
        >>> should_use_musicbrainz_value("Unknown", "Daft Punk", 0.95)
        True
        >>> should_use_musicbrainz_value("Artist", "Different", 0.50)
        False
    """
    # High confidence required to override
    if mb_confidence < confidence_threshold:
        return False

    # No tag value or placeholder value
    if not tag_value or not tag_value.strip():
        return True

    tag_lower = tag_value.lower().strip()
    placeholders = ["unknown", "unknown artist", "unknown title", "various", "various artists"]
    if tag_lower in placeholders:
        return True

    # If values match, no need to override
    if tag_value.strip().lower() == mb_value.strip().lower():
        return False

    return False  # Default: trust tags


def resolve_metadata_conflict(
    field: str,
    tag_value: Optional[str],
    mb_value: Optional[str],
    ai_value: Optional[str],
    mb_confidence: float = 0.0,
    verify_mode: bool = False
) -> Dict[str, Any]:
    """
    Resolve conflicts between multiple metadata sources.

    Strategy:
    1. Validate all values
    2. Check for agreement
    3. Use confidence scores to decide
    4. Log conflicts for user review

    Args:
        field: Field name (e.g., "bpm", "artist")
        tag_value: Value from ID3 tags
        mb_value: Value from MusicBrainz
        ai_value: Value from AI audio analysis
        mb_confidence: MusicBrainz confidence score
        verify_mode: If True, flag discrepancies even if tags present

    Returns:
        Resolution result with final value and metadata

    Examples:
        >>> resolve_metadata_conflict("bpm", "128", None, "127", 0.0)
        {...}
    """
    result: Dict[str, Any] = {
        "final_value": None,
        "source": None,
        "conflicts": [],
        "validated_by": None,
        "overridden": None,
    }

    # Collect available values
    sources = {}
    if tag_value:
        sources["Tags"] = tag_value
    if mb_value:
        sources["MusicBrainz"] = mb_value
    if ai_value:
        sources["AI Audio"] = ai_value

    # No values available
    if not sources:
        result["final_value"] = ""
        result["source"] = "None"
        return result

    # Only one source available
    if len(sources) == 1:
        source_name = list(sources.keys())[0]
        result["final_value"] = sources[source_name]
        result["source"] = source_name
        return result

    # Multiple sources - check for agreement
    unique_values = set(sources.values())

    # All sources agree
    if len(unique_values) == 1:
        result["final_value"] = list(unique_values)[0]
        result["source"] = "Tags" if tag_value else list(sources.keys())[0]
        if len(sources) > 1:
            result["validated_by"] = " & ".join(k for k in sources.keys() if k != result["source"])
        return result

    # Conflicts detected - resolve based on field type and confidence
    if field in ["bpm", "key"]:
        # Critical DJ fields - check for validation
        if tag_value and ai_value:
            if field == "bpm":
                comparison = compare_bpm_values(tag_value, ai_value)
                if not comparison["matches"]:
                    result["conflicts"].append({
                        "sources": ["Tags", "AI Audio"],
                        "values": [tag_value, ai_value],
                        "difference_percent": comparison["difference_percent"],
                        "disagreement": f"AI Audio suggests: {ai_value}"
                    })

                    # If verify mode, trust AI over suspicious tags
                    if verify_mode and comparison["difference_percent"] > 5:
                        result["final_value"] = ai_value
                        result["source"] = "AI Audio"
                        result["overridden"] = f"Tags ({tag_value}) overridden in verify mode"
                        return result

            elif field == "key":
                comparison = compare_key_values(tag_value, ai_value)
                if not comparison["matches"] and not comparison.get("enharmonic"):
                    result["conflicts"].append({
                        "sources": ["Tags", "AI Audio"],
                        "values": [tag_value, ai_value],
                        "disagreement": f"AI Audio suggests: {ai_value}"
                    })

    # Non-critical fields (artist, title, album, year)
    # MusicBrainz can override if high confidence
    if field in ["artist", "title", "album", "year"] and mb_value:
        if should_use_musicbrainz_value(tag_value or "", mb_value, mb_confidence):
            result["final_value"] = mb_value
            result["source"] = "MusicBrainz"
            result["overridden"] = f"Tags ({tag_value}) replaced by high-confidence match"
            return result

    # Default: trust tags if present
    if tag_value:
        result["final_value"] = tag_value
        result["source"] = "Tags"
    elif mb_value and mb_confidence > 0.8:
        result["final_value"] = mb_value
        result["source"] = "MusicBrainz"
    elif ai_value:
        result["final_value"] = ai_value
        result["source"] = "AI Audio"
    else:
        result["final_value"] = ""
        result["source"] = "None"

    return result
