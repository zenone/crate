# crate.py
#!/usr/bin/env python3
"""
crate.py

Rename MP3 files into DJ-friendly filenames using embedded metadata (ID3 tags).

Default output style (when data exists):
  Artist - Title (Mix/Remix/Version) [Key BPM].mp3

Examples:
  # Dry-run a folder recursively
  python3 crate.py ~/Music/Incoming --dry-run -v --recursive

  # Actually rename, using 8 workers
  python3 crate.py ~/Music/Incoming --workers 8 --recursive

  # Custom template (tokens below)
  python3 crate.py ~/Music/Incoming --template "{artist} - {title} ({label}) [{camelot} {bpm}]" --recursive

Requirements:
  pip3 install mutagen tqdm

Notes:
- This script never modifies tag data; it only renames files.
- It is conservative about safety: no path traversal, illegal chars removed, collisions handled.
"""

from __future__ import annotations

import argparse
import logging
import math
import os
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

try:
    from mutagen import File as MutagenFile  # type: ignore
except Exception:  # pragma: no cover
    MutagenFile = None  # type: ignore

try:
    from tqdm import tqdm  # type: ignore
except Exception:  # pragma: no cover
    tqdm = None  # type: ignore


# ----------------------------- Logging -------------------------------- #

def configure_logging(log_path: Optional[Path], verbosity: int) -> logging.Logger:
    logger = logging.getLogger("crate")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if run in an interactive session
    if logger.handlers:
        logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.ERROR if verbosity <= 0 else (logging.INFO if verbosity == 1 else logging.DEBUG))
    console.setFormatter(fmt)
    logger.addHandler(console)

    if log_path:
        fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


# -------------------------- Sanitization ------------------------------ #

_ILLEGAL_CHARS = r'[\\/:"*?<>|]'  # Windows + common POSIX troublemakers

def safe_filename(text: str, max_len: int = 140) -> str:
    """
    Normalize and sanitize arbitrary text for safe cross-platform filenames.
    - Removes control chars
    - Replaces illegal filename chars with spaces
    - Collapses whitespace
    - Strips trailing dots/spaces (Windows)
    """
    t = unicodedata.normalize("NFKC", (text or "")).strip()
    t = re.sub(r"[\x00-\x1f]", "", t)
    t = re.sub(_ILLEGAL_CHARS, " ", t)
    t = re.sub(r"\s+", " ", t).strip(". ").strip()
    if not t:
        t = "untitled"
    return t[:max_len]


def squash_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


# -------------------------- Key conversion ---------------------------- #

_PITCH_CLASS: Dict[str, int] = {
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

_CAMELOT_MAJOR_BY_PC = {0: "8B", 1: "3B", 2: "10B", 3: "5B", 4: "12B", 5: "7B", 6: "2B", 7: "9B", 8: "4B", 9: "11B", 10: "6B", 11: "1B"}
_CAMELOT_MINOR_BY_PC = {0: "5A", 1: "12A", 2: "7A", 3: "2A", 4: "9A", 5: "4A", 6: "11A", 7: "6A", 8: "1A", 9: "8A", 10: "3A", 11: "10A"}


def normalize_key_raw(key: str) -> str:
    """
    Attempt to normalize common key strings:
      - "C#m", "C# minor", "G Maj", "F#min", "Am"
    Returns normalized "C#m" or "C" etc, or "" if unknown.
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

    if tonic not in _PITCH_CLASS:
        return ""
    return f"{tonic}{'m' if is_minor else ''}"


def to_camelot(key: str) -> str:
    """
    Convert normalized key to Camelot. Accepts raw key strings too.
    Returns "" if unknown.
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
    pc = _PITCH_CLASS.get(tonic)
    if pc is None:
        return ""
    return (_CAMELOT_MINOR_BY_PC if minor else _CAMELOT_MAJOR_BY_PC).get(pc, "")


# -------------------------- Metadata reading --------------------------- #

def _first_tag(tags: Any, *keys: str) -> Optional[str]:
    """
    Get first textual value for any of the given keys from mutagen tags.
    Handles both ID3 frames and easy tags.
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


def extract_year(s: str) -> str:
    if not s:
        return ""
    m = re.search(r"\b(19\d{2}|20\d{2})\b", s)
    return m.group(1) if m else ""


def extract_track_number(s: str) -> str:
    if not s:
        return ""
    m = re.match(r"^\s*(\d{1,3})", s)
    if not m:
        return ""
    n = int(m.group(1))
    return f"{n:02d}" if 1 <= n <= 99 else str(n)


def normalize_bpm(s: str) -> str:
    if not s:
        return ""
    try:
        v = float(str(s).strip())
        if math.isnan(v) or v <= 0:
            return ""
        return str(int(round(v)))
    except Exception:
        m = re.search(r"(\d{2,3}(?:\.\d+)?)", str(s))
        if not m:
            return ""
        try:
            return str(int(round(float(m.group(1)))))
        except Exception:
            return ""


_MIX_MARKERS = [
    "mix", "remix", "rework", "edit", "vip", "version", "bootleg", "dub",
    "extended", "radio", "club", "instrumental", "acapella",
]


def infer_mix(title: str) -> str:
    """
    If title contains "(Something Remix)" / "[Extended Mix]" / "- VIP" etc,
    return that suffix text (without outer brackets). Otherwise "".
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


def read_mp3_metadata(path: Path, logger: logging.Logger) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    """
    Read useful metadata from an MP3 file.
    Returns (meta, error). meta keys are normalized strings (may be empty).
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


# -------------------------- Template building -------------------------- #

DEFAULT_TEMPLATE = "{artist} - {title}{mix_paren}{kb}"

_TOKEN_RE = re.compile(r"\{([a-z_]+)\}")

def build_filename_from_template(meta: Dict[str, str], template: str) -> str:
    """
    Safely expand a template using known tokens only.
    Unknown tokens are left intact.
    """
    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        return meta.get(key, m.group(0))

    return _TOKEN_RE.sub(repl, template)


def build_default_components(meta: Dict[str, str]) -> Dict[str, str]:
    artist = meta.get("artist") or "Unknown Artist"
    title = meta.get("title") or "Unknown Title"
    mix = meta.get("mix") or ""
    clean_title = strip_mix_from_title(title, mix) if mix else title

    bpm = meta.get("bpm", "")
    camelot = meta.get("camelot", "")
    raw_key = meta.get("key", "")

    mix_paren = f" ({mix})" if mix else ""
    kb_inner = squash_spaces(" ".join([camelot or raw_key, bpm]).strip())
    kb = f" [{kb_inner}]" if kb_inner else ""

    return {
        **meta,
        "artist": artist,
        "title": clean_title,
        "mix": mix,
        "mix_paren": mix_paren,
        "kb": kb,
        "bpm": bpm,
        "key": raw_key,
        "camelot": camelot,
        "year": meta.get("year", ""),
        "label": meta.get("label", ""),
        "track": meta.get("track", ""),
        "album": meta.get("album", ""),
    }


# -------------------------- Collision handling ------------------------- #

_dir_locks: Dict[Path, Lock] = {}
_dir_locks_guard = Lock()

def _get_dir_lock(directory: Path) -> Lock:
    with _dir_locks_guard:
        if directory not in _dir_locks:
            _dir_locks[directory] = Lock()
        return _dir_locks[directory]


class ReservationBook:
    """Thread-safe per-directory reservation of destination paths."""

    def __init__(self) -> None:
        self._per_dir: Dict[Path, set[Path]] = {}
        self._guard = Lock()

    def reserve_unique(self, directory: Path, stem: str, ext: str) -> Path:
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


# --------------------------- Renaming --------------------------------- #

@dataclass(frozen=True)
class RenameResult:
    src: Path
    dst: Optional[Path]
    status: str  # "renamed" | "skipped" | "error"
    message: Optional[str] = None


def derive_target(
    src: Path,
    logger: logging.Logger,
    template: str,
    book: ReservationBook,
) -> Tuple[Optional[Path], Optional[str]]:
    meta, err = read_mp3_metadata(src, logger)
    if err:
        return None, err
    assert meta is not None

    tokens = build_default_components(meta)
    expanded = build_filename_from_template(tokens, template or DEFAULT_TEMPLATE)
    stem = safe_filename(expanded)

    ext = src.suffix.lower() if src.suffix else ".mp3"
    if ext != ".mp3":
        ext = ".mp3"

    dst = book.reserve_unique(src.parent, stem, ext)
    if dst.resolve() == src.resolve():
        return None, "Already has desired name"

    return dst, None


def rename_one(
    src: Path,
    logger: logging.Logger,
    dry_run: bool,
    template: str,
    book: ReservationBook,
) -> RenameResult:
    try:
        dst, reason = derive_target(src, logger, template=template, book=book)
        if dst is None:
            logger.info("SKIP  %s  (%s)", src.name, reason)
            return RenameResult(src=src, dst=None, status="skipped", message=reason)

        if dry_run:
            logger.info("DRY   %s  ->  %s", src.name, dst.name)
            return RenameResult(src=src, dst=dst, status="renamed", message="dry-run")

        os.replace(src.as_posix(), dst.as_posix())
        logger.info("REN   %s  ->  %s", src.name, dst.name)
        return RenameResult(src=src, dst=dst, status="renamed")
    except Exception as exc:
        logger.error("ERR   %s  (%s)", src, exc)
        logger.debug("Trace", exc_info=True)
        return RenameResult(src=src, dst=None, status="error", message=str(exc))


def find_mp3s(root: Path, recursive: bool) -> List[Path]:
    if recursive:
        return [p for p in root.rglob("*.mp3") if p.is_file()]
    return [p for p in root.glob("*.mp3") if p.is_file()]


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rename MP3 files using metadata into DJ-friendly filenames."
    )
    parser.add_argument("path", type=Path, help="File or directory to process")
    parser.add_argument("--recursive", action="store_true", help="Recurse into subfolders")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change, but do not rename files")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker threads (default: 4)")
    parser.add_argument("-l", "--log", type=Path, default=None, help="Write detailed log to a file")
    parser.add_argument("-v", "--verbosity", action="count", default=0, help="Increase verbosity (-v, -vv)")
    parser.add_argument(
        "--template",
        type=str,
        default=DEFAULT_TEMPLATE,
        help=(
            "Filename template. Tokens: {artist} {title} {mix} {mix_paren} {bpm} {key} {camelot} "
            "{year} {label} {album} {track} {kb}. "
            "Default: '{artist} - {title}{mix_paren}{kb}'"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    logger = configure_logging(args.log, args.verbosity)

    if MutagenFile is None:
        logger.error("Missing dependency: mutagen. Install with: pip3 install mutagen")
        return 2
    if tqdm is None:
        logger.error("Missing dependency: tqdm. Install with: pip3 install tqdm")
        return 2

    target = args.path.expanduser().resolve()
    if not target.exists():
        logger.error("Path does not exist: %s", target)
        return 2

    if target.is_file():
        mp3s = [target] if target.suffix.lower() == ".mp3" else []
    else:
        mp3s = find_mp3s(target, recursive=args.recursive)

    if not mp3s:
        logger.error("No .mp3 files found at: %s", target)
        return 1

    book = ReservationBook()

    renamed = skipped = errors = 0
    bar = tqdm(total=len(mp3s), disable=(args.verbosity >= 2))

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futures = [
            ex.submit(rename_one, src, logger, args.dry_run, args.template, book)
            for src in mp3s
        ]
        for fut in as_completed(futures):
            res = fut.result()
            if res.status == "renamed":
                renamed += 1
            elif res.status == "skipped":
                skipped += 1
            else:
                errors += 1
            bar.update(1)

    bar.close()

    if args.verbosity >= 1:
        print(f"Done. Renamed: {renamed} | Skipped: {skipped} | Errors: {errors}")
        if args.dry_run:
            print("(Dry run - no files changed)")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
