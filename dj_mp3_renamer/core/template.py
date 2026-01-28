"""
Template-based filename generation.

These are pure functions with no side effects.
"""

import re
from typing import Dict

from .metadata_parsing import strip_mix_from_title
from .sanitization import squash_spaces


DEFAULT_TEMPLATE = "{artist} - {title} [{camelot} {bpm}]"

_TOKEN_RE = re.compile(r"\{([a-z_]+)\}")


def build_filename_from_template(meta: Dict[str, str], template: str) -> str:
    """
    Safely expand a template using known tokens.

    Unknown tokens are left intact.

    Args:
        meta: Dictionary of metadata values
        template: Template string with {token} placeholders

    Returns:
        Expanded template string

    Examples:
        >>> build_filename_from_template({"artist": "DJ", "title": "Song"}, "{artist} - {title}")
        'DJ - Song'
    """
    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        return meta.get(key, m.group(0))

    return _TOKEN_RE.sub(repl, template)


def build_default_components(meta: Dict[str, str]) -> Dict[str, str]:
    """
    Build default filename components from metadata.

    Provides atomic template variables with sensible defaults.
    All variables are basic/atomic - users control formatting in template.

    Args:
        meta: Raw metadata dictionary

    Returns:
        Enriched metadata dictionary with defaults

    Examples:
        >>> meta = {"artist": "DJ", "title": "Song", "bpm": "128"}
        >>> result = build_default_components(meta)
        >>> result["artist"], result["bpm"]
        ('DJ', '128')
    """
    artist = meta.get("artist") or "Unknown Artist"
    title = meta.get("title") or "Unknown Title"
    mix = meta.get("mix") or ""
    clean_title = strip_mix_from_title(title, mix) if mix else title

    bpm = meta.get("bpm", "")
    camelot = meta.get("camelot", "")
    raw_key = meta.get("key", "")

    return {
        **meta,
        "artist": artist,
        "title": clean_title,
        "mix": mix,
        "bpm": bpm,
        "key": raw_key,
        "camelot": camelot,
        "year": meta.get("year", ""),
        "label": meta.get("label", ""),
        "track": meta.get("track", ""),
        "album": meta.get("album", ""),
    }
