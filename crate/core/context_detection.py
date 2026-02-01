"""
Context Detection Module

Analyzes music file metadata to detect album vs singles context
and suggest appropriate naming templates.

Features:
- Album detection via metadata grouping
- Track number sequence analysis
- Confidence scoring
- Template suggestions
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import re


class ContextType(Enum):
    """Classification types for file context."""
    ALBUM = "ALBUM"
    PARTIAL_ALBUM = "PARTIAL_ALBUM"
    INCOMPLETE_ALBUM = "INCOMPLETE_ALBUM"
    SINGLES = "SINGLES"


@dataclass
class TemplateSuggestion:
    """A suggested template with reasoning."""
    template: str
    reason: str
    preset_id: Optional[str] = None


@dataclass
class ContextAnalysis:
    """Analysis result for a group of files."""
    type: ContextType
    confidence: float
    album_name: Optional[str]
    file_count: int
    track_range: Optional[str]
    suggested_templates: List[TemplateSuggestion] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def extract_track_number(track_str: Optional[str]) -> Optional[int]:
    """
    Extract numeric track number from various formats.

    Handles:
    - "1", "01", "001" -> 1
    - "1/12", "01/12" -> 1
    - "A", "B", "" -> None

    Args:
        track_str: Track metadata string

    Returns:
        Integer track number or None if not numeric
    """
    if not track_str:
        return None

    # Handle "1/12" format
    if '/' in track_str:
        track_str = track_str.split('/')[0]

    # Remove leading zeros and extract number
    match = re.match(r'(\d+)', str(track_str).strip())
    if match:
        return int(match.group(1))

    return None


def is_sequential(track_numbers: List[int], allow_gaps: bool = False) -> bool:
    """
    Check if track numbers form a sequential pattern.

    Args:
        track_numbers: List of track numbers
        allow_gaps: If True, allow gaps but check for general sequence

    Returns:
        True if sequential (with or without gaps depending on allow_gaps)
    """
    if not track_numbers:
        return False

    sorted_tracks = sorted(track_numbers)

    if not allow_gaps:
        # Strict sequential: 1,2,3,4,5...
        if sorted_tracks[0] != 1:
            return False
        for i in range(len(sorted_tracks) - 1):
            if sorted_tracks[i + 1] != sorted_tracks[i] + 1:
                return False
        return True
    else:
        # Loose sequential: Generally ascending pattern, allows gaps and higher starts
        # Single track is always considered sequential
        if len(sorted_tracks) == 1:
            return True

        # Check if starts reasonably low (< 20 for loose mode)
        if sorted_tracks[0] > 20:
            return False

        # Check if mostly ascending (80% of pairs increase)
        if len(sorted_tracks) > 1:
            ascending_pairs = 0
            for i in range(len(sorted_tracks) - 1):
                if sorted_tracks[i + 1] > sorted_tracks[i]:
                    ascending_pairs += 1
            return ascending_pairs >= (len(sorted_tracks) - 1) * 0.8

        return True


def analyze_context(files: List[Dict]) -> List[ContextAnalysis]:
    """
    Analyze file metadata to detect album vs singles context.

    Algorithm:
    1. Group files by album tag
    2. For each group:
       - Check if album tag exists
       - Check if enough files (3+ for album)
       - Extract track numbers
       - Check if sequential
       - Calculate confidence
       - Generate suggestions

    Args:
        files: List of file dicts with 'path' and 'metadata' keys

    Returns:
        List of ContextAnalysis objects (one per album group)
    """
    if not files:
        return []

    # Group files by (album, disc) to handle multi-disc albums (Task #100)
    album_groups: Dict[str, List[Dict]] = defaultdict(list)

    for file in files:
        metadata = file.get('metadata', {})
        album = metadata.get('album', '').strip()
        disc = metadata.get('disc', '').strip() or '1'  # Default to disc 1 if not specified

        # Use empty string as key for files without album
        # For multi-disc albums, group separately by disc number
        if album:
            album_key = f"{album}||DISC{disc}"
        else:
            album_key = ""
        album_groups[album_key].append(file)

    contexts = []

    for album_key, group_files in album_groups.items():
        # Extract album name from key (strip disc info)
        if album_key and "||DISC" in album_key:
            album_name = album_key.split("||DISC")[0]
        else:
            album_name = album_key
        context = analyze_group(album_name, group_files)
        contexts.append(context)

    return contexts


def analyze_group(album_name: str, files: List[Dict]) -> ContextAnalysis:
    """
    Analyze a single group of files (same album or no album).

    Args:
        album_name: Album name (empty string if no album)
        files: List of files in this group

    Returns:
        ContextAnalysis for this group
    """
    file_count = len(files)

    # No album tag -> SINGLES
    if not album_name:
        return ContextAnalysis(
            type=ContextType.SINGLES,
            confidence=1.0,
            album_name=None,
            file_count=file_count,
            track_range=None,
            suggested_templates=[
                TemplateSuggestion(
                    template="{artist} - {title} [{camelot} {bpm}]",
                    reason="No album metadata detected (single tracks)",
                    preset_id="dj-simple"
                ),
                TemplateSuggestion(
                    template="{artist} - {title}",
                    reason="Simple single track format",
                    preset_id="simple"
                )
            ],
            warnings=[]
        )

    # Too few files for album (< 3) -> SINGLES
    if file_count < 3:
        return ContextAnalysis(
            type=ContextType.SINGLES,
            confidence=0.8,
            album_name=album_name,
            file_count=file_count,
            track_range=None,
            suggested_templates=[
                TemplateSuggestion(
                    template="{artist} - {title}",
                    reason="Too few tracks for full album (< 3 files)",
                    preset_id="simple"
                )
            ],
            warnings=["Album tag present but only {0} file(s)".format(file_count)]
        )

    # Extract track numbers
    track_numbers = []
    missing_count = 0

    for file in files:
        metadata = file.get('metadata', {})
        track_str = metadata.get('track')
        track_num = extract_track_number(track_str)

        if track_num is not None:
            track_numbers.append(track_num)
        else:
            missing_count += 1

    # More than 30% missing tracks -> INCOMPLETE_ALBUM
    missing_percentage = missing_count / file_count
    if missing_percentage > 0.3:
        # Special case: 100% missing (no track numbers at all)
        if missing_count == file_count:
            warning_msg = "No track numbers found"
        else:
            warning_msg = "Only {0}/{1} files have track numbers".format(
                len(track_numbers), file_count
            )

        return ContextAnalysis(
            type=ContextType.INCOMPLETE_ALBUM,
            confidence=0.5,
            album_name=album_name,
            file_count=file_count,
            track_range=None,
            suggested_templates=[
                TemplateSuggestion(
                    template="{artist} - {album} - {title}",
                    reason="Album detected but many tracks missing numbers",
                    preset_id="album-basic"
                ),
                TemplateSuggestion(
                    template="{artist} - {title}",
                    reason="Alternative: Simple format (ignore track numbers)",
                    preset_id="simple"
                )
            ],
            warnings=[warning_msg]
        )

    # Check if sequential
    if not track_numbers:
        # No track numbers at all - but first check if this was caught by missing_percentage check
        if missing_count > 0:
            # Already handled by missing_percentage > 0.3 check above
            # This shouldn't be reached, but handle it anyway
            return ContextAnalysis(
                type=ContextType.INCOMPLETE_ALBUM,
                confidence=0.6,
                album_name=album_name,
                file_count=file_count,
                track_range=None,
                suggested_templates=[
                    TemplateSuggestion(
                        template="{artist} - {album} - {title}",
                        reason="Album detected but no track numbers",
                        preset_id="album-basic"
                    )
                ],
                warnings=["No track numbers found"]
            )
        else:
            # This case shouldn't happen (empty track_numbers but no missing_count)
            return ContextAnalysis(
                type=ContextType.INCOMPLETE_ALBUM,
                confidence=0.6,
                album_name=album_name,
                file_count=file_count,
                track_range=None,
                suggested_templates=[
                    TemplateSuggestion(
                        template="{artist} - {album} - {title}",
                        reason="Album detected but no track numbers",
                        preset_id="album-basic"
                    )
                ],
                warnings=["No track numbers found"]
            )

    # Perfect sequential (1,2,3...) -> ALBUM (high confidence)
    if is_sequential(track_numbers, allow_gaps=False):
        min_track = min(track_numbers)
        max_track = max(track_numbers)
        track_range = f"{min_track}-{max_track}"

        return ContextAnalysis(
            type=ContextType.ALBUM,
            confidence=0.95,
            album_name=album_name,
            file_count=file_count,
            track_range=track_range,
            suggested_templates=[
                TemplateSuggestion(
                    template="{track} - {artist} - {title}",
                    reason="Complete album with sequential tracks detected",
                    preset_id="simple-album"
                ),
                TemplateSuggestion(
                    template="{artist} - {album} - {track} - {title}",
                    reason="Full album context with track numbers",
                    preset_id="full-album"
                ),
                TemplateSuggestion(
                    template="{album} - {track} - {title}",
                    reason="Album-first format for organization",
                    preset_id="album-first"
                )
            ],
            warnings=[]
        )

    # Loose sequential with gaps -> PARTIAL_ALBUM
    if is_sequential(track_numbers, allow_gaps=True):
        min_track = min(track_numbers)
        max_track = max(track_numbers)
        track_range = f"{min_track}-{max_track}"
        gaps = max_track - min_track + 1 - len(track_numbers)

        return ContextAnalysis(
            type=ContextType.PARTIAL_ALBUM,
            confidence=0.75,
            album_name=album_name,
            file_count=file_count,
            track_range=track_range,
            suggested_templates=[
                TemplateSuggestion(
                    template="{track} - {artist} - {title}",
                    reason="Album detected with some tracks missing",
                    preset_id="simple-album"
                ),
                TemplateSuggestion(
                    template="{artist} - {album} - {track} - {title}",
                    reason="Full album context (partial collection)",
                    preset_id="full-album"
                )
            ],
            warnings=[
                "Track sequence has {0} gap(s) - may be incomplete album".format(gaps)
            ]
        )

    # Non-sequential tracks -> SINGLES
    return ContextAnalysis(
        type=ContextType.SINGLES,
        confidence=0.8,
        album_name=album_name,
        file_count=file_count,
        track_range=None,
        suggested_templates=[
            TemplateSuggestion(
                template="{artist} - {title}",
                reason="Tracks not sequential - treating as singles",
                preset_id="simple"
            )
        ],
        warnings=["Album tag present but tracks not in sequence"]
    )


def get_default_suggestion(contexts: List[ContextAnalysis]) -> Optional[Dict]:
    """
    Get the single best suggestion from multiple contexts.

    Picks the context with highest confidence.

    Args:
        contexts: List of context analyses

    Returns:
        Dict with default suggestion or None if no contexts
    """
    if not contexts:
        return None

    # Sort by confidence (highest first)
    sorted_contexts = sorted(contexts, key=lambda c: c.confidence, reverse=True)
    best_context = sorted_contexts[0]

    if not best_context.suggested_templates:
        return None

    best_template = best_context.suggested_templates[0]

    return {
        "template": best_template.template,
        "preset_id": best_template.preset_id,
        "reason": best_template.reason,
        "confidence": best_context.confidence
    }


# Task #110: Per-Album Smart Detection

def group_files_by_subdirectory(directory: str, files: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Group files by subdirectory (album folder).

    Files in the root directory are grouped as "[Root Files]".
    Files in subdirectories are grouped by their relative subdirectory path.

    Args:
        directory: Base directory path that was loaded
        files: List of file dicts with 'path' key

    Returns:
        Dict mapping subdirectory path to list of files

    Example:
        Input files:
            /Music/Dir/file1.mp3
            /Music/Dir/file2.mp3
            /Music/Dir/Album_A/track1.mp3
            /Music/Dir/Album_A/track2.mp3
            /Music/Dir/Album_B/track1.mp3

        Output:
            {
                "[Root Files]": [file1, file2],
                "Album_A": [track1, track2],
                "Album_B": [track1]
            }
    """
    import os
    from pathlib import Path

    album_groups: Dict[str, List[Dict]] = defaultdict(list)

    for file in files:
        file_path = file.get('path', '')

        # Get subdirectory relative to base directory
        try:
            file_path_obj = Path(file_path)
            directory_obj = Path(directory)

            # Get relative path
            rel_path = file_path_obj.relative_to(directory_obj)

            # Get parent directory (subdirectory name)
            if rel_path.parent == Path('.'):
                # File is in root directory
                album_key = "[Root Files]"
            else:
                # File is in subdirectory
                # Use first-level subdirectory only (handle nested structures)
                subdirs = rel_path.parts[:-1]  # All parts except filename
                if subdirs:
                    album_key = subdirs[0]  # First level subdirectory
                else:
                    album_key = "[Root Files]"

        except (ValueError, OSError):
            # Path handling error - put in root
            album_key = "[Root Files]"

        album_groups[album_key].append(file)

    return dict(album_groups)


def analyze_per_album_context(directory: str, files: List[Dict], max_albums: int = 100) -> Dict:
    """
    Analyze context with per-album detection (Task #110).

    Groups files by subdirectory and analyzes each album separately.
    Returns per-album detection results for frontend multi-selection UI.

    Args:
        directory: Base directory path that was loaded
        files: List of file dicts with 'path' and 'metadata' keys
        max_albums: Maximum number of albums to analyze (performance limit)

    Returns:
        Dict with per-album results:
        {
            "per_album_mode": True,
            "albums": [
                {
                    "path": "Album_A",
                    "album_name": "Greatest Hits",
                    "file_count": 12,
                    "detection": {
                        "type": "ALBUM",
                        "confidence": "high",
                        "suggested_template": "{track} - {title}",
                        "reason": "Sequential tracks 1-12 detected"
                    }
                },
                ...
            ],
            "global_suggestion": {...},  # Fallback for backward compat
            "warning": "..." (if truncated)
        }
    """
    import logging
    logger = logging.getLogger(__name__)

    if not files:
        logger.info("Per-album detection: No files provided")
        return {
            "per_album_mode": False,
            "albums": [],
            "global_suggestion": None
        }

    # Group files by subdirectory
    album_groups = group_files_by_subdirectory(directory, files)
    logger.info(f"Per-album detection: Grouped {len(files)} files into {len(album_groups)} album group(s)")

    for album_key in album_groups.keys():
        logger.info(f"  - Album group: '{album_key}' ({len(album_groups[album_key])} files)")

    # Check if we have multiple albums (per-album mode only makes sense with 2+)
    if len(album_groups) < 2:
        # Single album or flat structure - use current single-banner mode
        logger.info(f"Per-album detection: Only {len(album_groups)} album group(s) found (need 2+), using single-banner mode")
        contexts = analyze_context(files)
        return {
            "per_album_mode": False,
            "albums": [],
            "global_suggestion": get_default_suggestion(contexts)
        }

    # Limit max albums for performance
    truncated = False
    warning = None

    if len(album_groups) > max_albums:
        truncated = True
        warning = f"Only analyzing first {max_albums} albums (out of {len(album_groups)} total)"

        # Truncate to max_albums (keep first N)
        album_keys = list(album_groups.keys())[:max_albums]
        album_groups = {key: album_groups[key] for key in album_keys}

    # Analyze each album
    albums = []

    for album_path, album_files in album_groups.items():
        # Get album name from metadata (prefer over directory name)
        album_name = None
        for file in album_files:
            metadata = file.get('metadata', {})
            if metadata.get('album'):
                album_name = metadata.get('album')
                break

        # Fallback to directory name if no metadata album
        if not album_name:
            album_name = album_path

        # Analyze this album group
        contexts = analyze_context(album_files)

        if contexts:
            context = contexts[0]  # Take first (highest confidence)

            # Get suggested template
            suggested_template = None
            reason = None

            if context.suggested_templates:
                best_template = context.suggested_templates[0]
                suggested_template = best_template.template
                reason = best_template.reason

            # Map confidence float to string
            if context.confidence >= 0.9:
                confidence_str = "high"
            elif context.confidence >= 0.7:
                confidence_str = "medium"
            else:
                confidence_str = "low"

            albums.append({
                "path": album_path,
                "album_name": album_name,
                "file_count": len(album_files),
                "files": [f.get('path', '') for f in album_files],  # File paths
                "detection": {
                    "type": context.type.value,
                    "confidence": confidence_str,
                    "suggested_template": suggested_template,
                    "reason": reason or "Analysis complete"
                }
            })
        else:
            # Detection failed for this album
            albums.append({
                "path": album_path,
                "album_name": album_name,
                "file_count": len(album_files),
                "files": [f.get('path', '') for f in album_files],
                "detection": {
                    "type": "UNKNOWN",
                    "confidence": "none",
                    "suggested_template": None,
                    "reason": "Detection failed"
                },
                "error": "Context analysis failed"
            })

    # Get global suggestion (fallback for backward compatibility)
    all_contexts = analyze_context(files)
    global_suggestion = get_default_suggestion(all_contexts)

    result = {
        "per_album_mode": True,
        "albums": albums,
        "global_suggestion": global_suggestion
    }

    if truncated and warning:
        result["warning"] = warning
        result["truncated"] = True

    return result
