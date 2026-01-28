"""
I/O operations: file system and metadata reading.

These functions have side effects (reading files).
"""

import logging
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from .key_conversion import normalize_key_raw, to_camelot
from .metadata_parsing import (
    extract_year,
    extract_track_number,
    normalize_bpm,
    infer_mix,
)
from .sanitization import squash_spaces

try:
    from mutagen import File as MutagenFile  # type: ignore
except Exception:  # pragma: no cover
    MutagenFile = None  # type: ignore


def _first_tag(tags: Any, *keys: str) -> Optional[str]:
    """
    Get first textual value for any of the given keys from mutagen tags.

    Handles both ID3 frames and easy tags.

    Args:
        tags: Mutagen tags object
        *keys: Tag keys to search for

    Returns:
        First found tag value as string, or None
    """
    if not tags:
        return None

    for k in keys:
        try:
            v = tags.get(k)
        except Exception:
            v = None

        if not v:
            continue

        if hasattr(v, "text"):
            t = v.text
            if isinstance(t, list) and t:
                return str(t[0])
            if t:
                return str(t)

        if isinstance(v, list) and v:
            return str(v[0])
        if isinstance(v, (str, int, float)):
            return str(v)

    return None


def read_mp3_metadata(
    path: Path, logger: logging.Logger
) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    """
    Read useful metadata from an MP3 file.

    Args:
        path: Path to MP3 file
        logger: Logger instance

    Returns:
        Tuple of (metadata_dict, error_message).
        If successful, metadata_dict is populated and error is None.
        If failed, metadata_dict is None and error is a string.

    Examples:
        >>> logger = logging.getLogger("test")
        >>> meta, err = read_mp3_metadata(Path("song.mp3"), logger)
        >>> if err is None:
        ...     print(meta["artist"])
    """
    if MutagenFile is None:
        return None, "Missing dependency: mutagen (pip3 install mutagen)"

    try:
        audio = MutagenFile(path.as_posix(), easy=False)
        if audio is None or not getattr(audio, "tags", None):
            return None, "No readable tags"

        tags = audio.tags

        artist = _first_tag(tags, "TPE1", "artist", "ARTIST")
        title = _first_tag(tags, "TIT2", "title", "TITLE")
        album = _first_tag(tags, "TALB", "album", "ALBUM")
        label = _first_tag(tags, "TPUB", "publisher")
        bpm = _first_tag(tags, "TBPM", "bpm")
        key = _first_tag(tags, "TKEY", "initialkey", "key")
        date = _first_tag(tags, "TDRC", "TYER", "date", "YEAR")
        track = _first_tag(tags, "TRCK", "tracknumber", "TRACKNUMBER")

        meta: Dict[str, str] = {
            "artist": squash_spaces(artist or ""),
            "title": squash_spaces(title or ""),
            "album": squash_spaces(album or ""),
            "label": squash_spaces(label or ""),
            "year": extract_year(date or ""),
            "track": extract_track_number(track or ""),
            "bpm": normalize_bpm(bpm or ""),
            "key": normalize_key_raw(key or ""),
        }
        meta["camelot"] = to_camelot(meta["key"]) if meta["key"] else ""
        meta["mix"] = infer_mix(meta["title"])

        return meta, None
    except Exception as exc:
        logger.debug("Metadata read error for %s", path, exc_info=True)
        return None, f"Metadata read error: {exc.__class__.__name__}"


def find_mp3s(root: Path, recursive: bool) -> List[Path]:
    """
    Find MP3 files in a directory.

    Args:
        root: Root directory to search
        recursive: If True, search subdirectories recursively

    Returns:
        List of Path objects to MP3 files

    Examples:
        >>> mp3s = find_mp3s(Path("/music"), recursive=True)
        >>> len(mp3s)
        42
    """
    if recursive:
        return [p for p in root.rglob("*.mp3") if p.is_file()]
    return [p for p in root.glob("*.mp3") if p.is_file()]


# Global per-directory locks for thread-safety
_dir_locks: Dict[Path, Lock] = {}
_dir_locks_guard = Lock()


def _get_dir_lock(directory: Path) -> Lock:
    """Get or create a lock for a specific directory."""
    with _dir_locks_guard:
        if directory not in _dir_locks:
            _dir_locks[directory] = Lock()
        return _dir_locks[directory]


class ReservationBook:
    """
    Thread-safe per-directory reservation of destination paths.

    Prevents filename collisions when renaming files concurrently.
    """

    def __init__(self) -> None:
        self._per_dir: Dict[Path, set[Path]] = {}
        self._guard = Lock()

    def reserve_unique(self, directory: Path, stem: str, ext: str) -> Path:
        """
        Reserve a unique filename in a directory.

        If the filename exists or is already reserved, appends (2), (3), etc.

        Args:
            directory: Target directory
            stem: Filename stem (without extension)
            ext: File extension (e.g., ".mp3")

        Returns:
            Reserved Path object

        Examples:
            >>> book = ReservationBook()
            >>> path = book.reserve_unique(Path("/music"), "song", ".mp3")
            >>> path.name
            'song.mp3'
        """
        lock = _get_dir_lock(directory)
        with lock:
            with self._guard:
                reserved = self._per_dir.setdefault(directory, set())

            candidate = directory / f"{stem}{ext}"
            if not candidate.exists() and candidate not in reserved:
                reserved.add(candidate)
                return candidate

            n = 2
            while True:
                candidate = directory / f"{stem} ({n}){ext}"
                if not candidate.exists() and candidate not in reserved:
                    reserved.add(candidate)
                    return candidate
                n += 1
