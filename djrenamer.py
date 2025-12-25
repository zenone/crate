#!/usr/bin/env python3
"""
djrenamer.py

DJ-friendly MP3 renamer + (optional) tag cleanup + (optional) online enrichment via AcoustID/MusicBrainz.

Filename goals (Rekordbox / CDJ workflows):
- Human-scan friendly in Finder and on USB
- Stable sorting (optional track numbers for albums)
- Avoid illegal filesystem characters
- Keep the "core identity" up front: Artist - Title
- Optionally append Mix/Version, Key, BPM (when available)

Notes:
- rekordbox can analyze BPM/KEY for its own database, but it may not reliably write BPM back
  into the audio file’s tags. This tool can write TBPM/TKEY itself if you want deterministic tags.

Install:
  pip install mutagen tqdm requests

Optional (for fingerprint lookup):
  brew install chromaprint
  export ACOUSTID_API_KEY="..."
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import dataclasses
import math
import os
import re
import shutil
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from mutagen.id3 import (
    ID3,
    ID3NoHeaderError,
    TALB,
    TBPM,
    TKEY,
    TPE1,
    TIT2,
    TRCK,
    TXXX,
)
from tqdm import tqdm


# --------------------------- Text + filename utils ---------------------------

_ILLEGAL_FS = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
_MULTI_SPACE = re.compile(r"\s+")
_DASH_SPACES = re.compile(r"\s*-\s*")
_FEAT = re.compile(r"\b(feat|ft)\.?\b", re.IGNORECASE)


def squash_spaces(s: str) -> str:
    return _MULTI_SPACE.sub(" ", s).strip()


def normalize_dash_spaces(s: str) -> str:
    # "A- B" -> "A - B" for readability
    return _DASH_SPACES.sub(" - ", s).strip()


def clean_text(s: str) -> str:
    s = s.replace("\u200b", "")  # zero width space
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    s = squash_spaces(s)
    s = _FEAT.sub("feat.", s)
    return s


def safe_filename(stem: str, max_len: int = 140) -> str:
    stem = clean_text(stem)
    stem = _ILLEGAL_FS.sub(" ", stem)
    stem = stem.replace("..", ".")
    stem = stem.strip(" .")
    stem = squash_spaces(stem)
    if len(stem) > max_len:
        stem = stem[:max_len].rstrip(" .")
    return stem or "untitled"


def split_track_prefix_from_name(name: str) -> Tuple[str, str]:
    """
    If filename starts with '01', '01 ', '01-', '01.' etc, return ('01 ', rest).
    """
    m = re.match(r"^(?P<num>\d{1,3})(?P<sep>[\s._-]+)(?P<rest>.+)$", name.strip())
    if not m:
        return "", name
    num = int(m.group("num"))
    if 0 <= num <= 999:
        width = 2 if num < 100 else 3
        prefix = f"{num:0{width}d} "
        return prefix, m.group("rest").strip()
    return "", name


# ------------------------------ Key conversion ------------------------------

_PITCH_CLASS: Dict[str, int] = {
    "C": 0,
    "B#": 0,
    "C#": 1,
    "DB": 1,
    "D": 2,
    "D#": 3,
    "EB": 3,
    "E": 4,
    "FB": 4,
    "E#": 5,
    "F": 5,
    "F#": 6,
    "GB": 6,
    "G": 7,
    "G#": 8,
    "AB": 8,
    "A": 9,
    "A#": 10,
    "BB": 10,
    "B": 11,
    "CB": 11,
}

# Camelot reference mapping (common DJ convention)
# Major: C=8B, G=9B, D=10B, A=11B, E=12B, B=1B, F#=2B, C#=3B, Ab=4B, Eb=5B, Bb=6B, F=7B
# Minor: A=8A, E=9A, B=10A, F#=11A, C#=12A, G#=1A, D#=2A, A#=3A, F=4A, C=5A, G=6A, D=7A
_CAMELOT_BY_PC_MODE: Dict[Tuple[int, str], str] = {
    # major
    (0, "maj"): "8B",
    (7, "maj"): "9B",
    (2, "maj"): "10B",
    (9, "maj"): "11B",
    (4, "maj"): "12B",
    (11, "maj"): "1B",
    (6, "maj"): "2B",
    (1, "maj"): "3B",
    (8, "maj"): "4B",
    (3, "maj"): "5B",
    (10, "maj"): "6B",
    (5, "maj"): "7B",
    # minor
    (9, "min"): "8A",
    (4, "min"): "9A",
    (11, "min"): "10A",
    (6, "min"): "11A",
    (1, "min"): "12A",
    (8, "min"): "1A",
    (3, "min"): "2A",
    (10, "min"): "3A",
    (5, "min"): "4A",
    (0, "min"): "5A",
    (7, "min"): "6A",
    (2, "min"): "7A",
}


def _parse_key_to_pc_and_mode(key: str) -> Optional[Tuple[int, str]]:
    """Return (pitch_class, mode) where mode is 'maj' or 'min'."""
    if not key:
        return None
    k = clean_text(key).upper().replace("♭", "B").replace("♯", "#")
    k = k.replace("MINOR", "M").replace("MAJOR", "")
    k = k.replace(" ", "")

    m = re.fullmatch(r"(\d{1,2})(A|B)", k)
    if m:
        cam = f"{int(m.group(1))}{m.group(2)}"
        for (pc, mode), val in _CAMELOT_BY_PC_MODE.items():
            if val == cam:
                return pc, mode
        return None

    m = re.fullmatch(r"([A-G])([#B]?)(M?)", k)
    if not m:
        return None
    root = m.group(1) + (m.group(2) or "")
    mode = "min" if m.group(3) == "M" else "maj"
    pc = _PITCH_CLASS.get(root)
    if pc is None:
        return None
    return pc, mode


def key_to_camelot(key: str) -> Optional[str]:
    parsed = _parse_key_to_pc_and_mode(key)
    if not parsed:
        return None
    pc, mode = parsed
    return _CAMELOT_BY_PC_MODE.get((pc, mode))


# ------------------------------ Tag handling --------------------------------

@dataclasses.dataclass
class TrackMeta:
    path: Path
    artist: str = ""
    title: str = ""
    album: str = ""
    mix: str = ""
    key: str = ""
    bpm: Optional[float] = None
    track_number: Optional[int] = None
    track_total: Optional[int] = None
    musicbrainz_recording_id: str = ""


def _get_id3(path: Path) -> Optional[ID3]:
    try:
        return ID3(path)
    except ID3NoHeaderError:
        return None
    except Exception:
        return None


def _get_text_frame(id3: Optional[ID3], keys: List[str]) -> str:
    if not id3:
        return ""
    for k in keys:
        try:
            if k in id3 and getattr(id3[k], "text", None):
                val = str(id3[k].text[0])
                if val:
                    return val
        except Exception:
            continue
    return ""


def _get_txxx(id3: Optional[ID3], desc: str) -> str:
    if not id3:
        return ""
    for frame in id3.getall("TXXX"):
        try:
            if frame.desc.strip().lower() == desc.strip().lower() and frame.text:
                return str(frame.text[0])
        except Exception:
            pass
    return ""


def parse_trck(trck_raw: str) -> Tuple[Optional[int], Optional[int]]:
    """
    TRCK can be "1/12" or "01/12" or "1".
    """
    if not trck_raw:
        return None, None
    s = clean_text(trck_raw)
    m = re.match(r"^\s*(\d{1,3})(?:\s*/\s*(\d{1,3}))?\s*$", s)
    if not m:
        return None, None
    n = int(m.group(1))
    t = int(m.group(2)) if m.group(2) else None
    return n, t


def parse_bpm(raw: str) -> Optional[float]:
    if not raw:
        return None
    s = clean_text(raw).replace(",", ".")
    try:
        bpm = float(s)
    except ValueError:
        return None
    if not (30.0 <= bpm <= 250.0):
        return None
    return round(bpm, 1)


def read_track_meta(path: Path) -> TrackMeta:
    tm = TrackMeta(path=path)
    id3 = _get_id3(path)

    tm.artist = _get_text_frame(id3, ["TPE1"]) or _get_txxx(id3, "ARTIST")
    tm.title = _get_text_frame(id3, ["TIT2"]) or _get_txxx(id3, "TITLE")
    tm.album = _get_text_frame(id3, ["TALB"]) or _get_txxx(id3, "ALBUM")

    tm.mix = _get_txxx(id3, "SUBTITLE") or _get_txxx(id3, "MIXNAME") or _get_txxx(id3, "VERSION")

    tm.key = _get_text_frame(id3, ["TKEY"]) or _get_txxx(id3, "INITIALKEY") or _get_txxx(id3, "KEY")
    tm.bpm = parse_bpm(_get_text_frame(id3, ["TBPM"]) or _get_txxx(id3, "BPM") or _get_txxx(id3, "TEMPO"))

    trck_raw = _get_text_frame(id3, ["TRCK"]) or _get_txxx(id3, "TRCK")
    if trck_raw:
        tm.track_number, tm.track_total = parse_trck(trck_raw)

    tm.musicbrainz_recording_id = _get_txxx(id3, "MusicBrainz Recording Id") or _get_txxx(
        id3, "MUSICBRAINZ_RECORDINGID"
    )

    # Fallback from filename if tags are sparse
    if not tm.artist or not tm.title:
        base = path.stem
        _, rest = split_track_prefix_from_name(base)
        if " - " in rest:
            a, t = rest.split(" - ", 1)
            tm.artist = tm.artist or clean_text(a)
            tm.title = tm.title or clean_text(t)

    tm.artist = clean_text(tm.artist)
    tm.title = clean_text(tm.title)
    tm.album = clean_text(tm.album)
    tm.mix = clean_text(tm.mix)
    tm.key = clean_text(tm.key)

    return tm


def write_clean_tags(
    tm: TrackMeta,
    *,
    write_key_as_camelot: bool,
    write_bpm: bool,
    write_mbids: bool,
    dry_run: bool,
    verbosity: int,
) -> None:
    """
    Conservatively normalize whitespace, and (optionally) write BPM/KEY into ID3.
    """
    try:
        id3 = ID3(tm.path)
    except ID3NoHeaderError:
        id3 = ID3()
    except Exception as e:
        if verbosity >= 2:
            print(f"[tags] unable to read ID3 for {tm.path}: {e}", file=sys.stderr)
        return

    def set_text(frame_id: str, frame_obj) -> None:
        id3.setall(frame_id, [frame_obj])

    if tm.artist:
        set_text("TPE1", TPE1(encoding=3, text=[tm.artist]))
    if tm.title:
        set_text("TIT2", TIT2(encoding=3, text=[tm.title]))
    if tm.album:
        set_text("TALB", TALB(encoding=3, text=[tm.album]))
    if tm.track_number:
        tr = f"{tm.track_number}/{tm.track_total}" if tm.track_total else str(tm.track_number)
        set_text("TRCK", TRCK(encoding=3, text=[tr]))

    if tm.key:
        if write_key_as_camelot:
            cam = key_to_camelot(tm.key)
            set_text("TKEY", TKEY(encoding=3, text=[cam or tm.key]))
        else:
            set_text("TKEY", TKEY(encoding=3, text=[tm.key]))

    if write_bpm and tm.bpm is not None:
        set_text("TBPM", TBPM(encoding=3, text=[str(tm.bpm)]))

    if write_mbids and tm.musicbrainz_recording_id:
        id3.add(TXXX(encoding=3, desc="MusicBrainz Recording Id", text=[tm.musicbrainz_recording_id]))

    if dry_run:
        return
    try:
        id3.save(tm.path)
    except Exception as e:
        if verbosity >= 1:
            print(f"[tags] failed saving tags for {tm.path}: {e}", file=sys.stderr)


# ---------------------------- Online enrichment -----------------------------

_ACOUSTID_URL = "https://api.acoustid.org/v2/lookup"
_MB_WS2 = "https://musicbrainz.org/ws/2"


class RateLimiter:
    def __init__(self, min_interval_s: float):
        self.min_interval_s = min_interval_s
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self):
        # thread-safe global limiter
        with self._lock:
            now = time.time()
            delta = now - self._last
            if delta < self.min_interval_s:
                time.sleep(self.min_interval_s - delta)
            self._last = time.time()


def _have_fpcalc() -> bool:
    return shutil.which("fpcalc") is not None


def fpcalc_fingerprint(path: Path) -> Optional[Tuple[int, str]]:
    """
    Return (duration_seconds, fingerprint_string) using chromaprint fpcalc.
    """
    if not _have_fpcalc():
        return None
    try:
        proc = subprocess.run(
            ["fpcalc", "-length", "120", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return None
        dur = None
        fp = None
        for line in proc.stdout.splitlines():
            if line.startswith("DURATION="):
                dur = int(line.split("=", 1)[1].strip())
            elif line.startswith("FINGERPRINT="):
                fp = line.split("=", 1)[1].strip()
        if dur is None or not fp:
            return None
        return dur, fp
    except Exception:
        return None


def acoustid_lookup(path: Path, *, api_key: str, verbosity: int) -> Optional[dict]:
    """
    Query AcoustID with fpcalc fingerprint. Returns best match (dict) or None.
    """
    fp = fpcalc_fingerprint(path)
    if not fp:
        if verbosity >= 2:
            print(f"[acoustid] fpcalc missing or failed for {path}", file=sys.stderr)
        return None
    duration, fingerprint = fp
    params = {
        "client": api_key,
        "meta": "recordings+releasegroups+compress",
        "duration": str(duration),
        "fingerprint": fingerprint,
    }
    try:
        r = requests.get(_ACOUSTID_URL, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "ok":
            return None
        results = data.get("results") or []
        if not results:
            return None
        best = max(results, key=lambda x: x.get("score", 0.0))
        return best
    except Exception as e:
        if verbosity >= 2:
            print(f"[acoustid] lookup failed: {e}", file=sys.stderr)
        return None


def musicbrainz_recording_lookup(mbid: str, *, ua: str, limiter: RateLimiter, verbosity: int) -> Optional[dict]:
    """
    Fetch recording details from MusicBrainz WS2.
    """
    limiter.wait()
    url = f"{_MB_WS2}/recording/{mbid}"
    params = {"fmt": "json", "inc": "artists+releases"}
    headers = {"User-Agent": ua}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        if verbosity >= 2:
            print(f"[musicbrainz] recording lookup failed: {e}", file=sys.stderr)
        return None


def apply_online_enrichment(tm: TrackMeta, *, ua: str, limiter: RateLimiter, verbosity: int) -> TrackMeta:
    """
    Enrich missing tags using AcoustID -> MusicBrainz, when available.
    Only fills blanks.
    """
    api_key = os.environ.get("ACOUSTID_API_KEY", "").strip()
    if not api_key:
        if verbosity >= 2:
            print("[acoustid] ACOUSTID_API_KEY not set; skipping", file=sys.stderr)
        return tm

    best = acoustid_lookup(tm.path, api_key=api_key, verbosity=verbosity)
    if not best:
        return tm

    recs = best.get("recordings") or []
    if not recs:
        return tm

    rec = recs[0]
    mbid = rec.get("id") or ""
    if not mbid:
        return tm

    tm.musicbrainz_recording_id = tm.musicbrainz_recording_id or mbid

    rec_json = musicbrainz_recording_lookup(mbid, ua=ua, limiter=limiter, verbosity=verbosity)
    if not rec_json:
        return tm

    title = clean_text(rec_json.get("title", "") or "")
    if title and not tm.title:
        tm.title = title

    if not tm.artist:
        ac = rec_json.get("artist-credit") or []
        if ac:
            names = []
            for item in ac:
                if isinstance(item, dict) and item.get("name"):
                    names.append(item["name"])
            if names:
                tm.artist = clean_text(" & ".join(names))

    if not tm.album:
        releases = rec_json.get("releases") or []
        if releases:
            rel = releases[0]
            if rel.get("title"):
                tm.album = clean_text(rel["title"])

    return tm


# ------------------------------ Naming logic --------------------------------

def build_filename(tm: TrackMeta, *, include_key_bpm: bool, album_mode: str, write_key_as_camelot: bool) -> str:
    """
    album_mode: "force" | "on" | "off"
    """
    artist = tm.artist or "Unknown Artist"
    title = tm.title or "Unknown Title"

    mix = tm.mix
    if mix and mix.lower() not in title.lower():
        title_out = f"{title} ({mix})"
    else:
        title_out = title

    core = f"{artist} - {title_out}"

    suffix_bits: List[str] = []
    if include_key_bpm:
        key = tm.key
        if write_key_as_camelot and key:
            key = key_to_camelot(key) or key
        if key:
            suffix_bits.append(key)
        if tm.bpm is not None:
            bpm_str = str(int(tm.bpm)) if abs(tm.bpm - int(tm.bpm)) < 1e-6 else str(tm.bpm)
            suffix_bits.append(f"{bpm_str} BPM")
    if suffix_bits:
        core = f"{core} [{' '.join(suffix_bits)}]"

    track_prefix = ""
    if album_mode in ("force", "on") and tm.track_number:
        width = 2 if (tm.track_total or 0) < 100 else 3
        track_prefix = f"{tm.track_number:0{width}d} "

    return safe_filename(f"{track_prefix}{core}") + tm.path.suffix.lower()


def compute_album_consistency(tracks: List[TrackMeta]) -> bool:
    """
    Decide if this set of tracks appears to be a single album/EP.
    Heuristic: all non-empty album tags identical AND at least half have track numbers.
    """
    albums = {t.album for t in tracks if t.album}
    if len(albums) != 1:
        return False
    with_trck = sum(1 for t in tracks if t.track_number is not None)
    return with_trck >= max(1, math.ceil(len(tracks) * 0.5))


def unique_target_path(src: Path, target_name: str) -> Path:
    dst = src.with_name(target_name)
    if not dst.exists():
        return dst
    stem = dst.stem
    suffix = dst.suffix
    i = 2
    while True:
        cand = dst.with_name(f"{stem} ({i}){suffix}")
        if not cand.exists():
            return cand
        i += 1


# ---------------------------------- CLI -------------------------------------

def iter_mp3s(root: Path, recursive: bool) -> List[Path]:
    if root.is_file() and root.suffix.lower() == ".mp3":
        return [root]
    if not root.is_dir():
        return []
    if recursive:
        return [p for p in root.rglob("*.mp3") if p.is_file()]
    return [p for p in root.glob("*.mp3") if p.is_file()]


def rename_one(
    path: Path,
    *,
    include_key_bpm: bool,
    album_mode_effective: str,
    clean_tags: bool,
    write_key_as_camelot: bool,
    write_bpm: bool,
    online: bool,
    ua: str,
    limiter: RateLimiter,
    dry_run: bool,
    verbosity: int,
) -> Tuple[str, Optional[Path], Optional[Path]]:
    """
    Returns (status, src, dst):
      status in {"renamed","skipped","error"}
    """
    try:
        tm = read_track_meta(path)

        if online and (not tm.artist or not tm.title or not tm.album):
            tm = apply_online_enrichment(tm, ua=ua, limiter=limiter, verbosity=verbosity)

        if clean_tags:
            write_clean_tags(
                tm,
                write_key_as_camelot=write_key_as_camelot,
                write_bpm=write_bpm,
                write_mbids=True,
                dry_run=dry_run,
                verbosity=verbosity,
            )

        new_name = build_filename(
            tm,
            include_key_bpm=include_key_bpm,
            album_mode=album_mode_effective,
            write_key_as_camelot=write_key_as_camelot,
        )

        if path.name == new_name:
            return "skipped", path, None

        dst = unique_target_path(path, new_name)

        if verbosity >= 2:
            print(f"{path} -> {dst}")

        if not dry_run:
            path.rename(dst)

        return "renamed", path, dst
    except Exception as e:
        if verbosity >= 1:
            print(f"[error] {path}: {e}", file=sys.stderr)
        return "error", path, None


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Rename MP3s into DJ-friendly filenames (Artist - Title [Key BPM])")
    ap.add_argument("path", type=str, help="File or folder to process")
    ap.add_argument("--recursive", "-r", action="store_true", help="Recurse into subfolders")
    ap.add_argument("--dry-run", action="store_true", help="Show what would change without renaming/writing tags")
    ap.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity (-v, -vv)")

    ap.add_argument("--workers", type=int, default=max(4, (os.cpu_count() or 4)), help="Parallel workers for local IO")
    ap.add_argument("--include-key-bpm", action="store_true", default=True, help="Append [Key BPM] to filename when available (default on)")
    ap.add_argument("--no-key-bpm", dest="include_key_bpm", action="store_false", help="Do not append key/bpm to filename")

    ap.add_argument("--clean-tags", action="store_true", help="Normalize whitespace and (optionally) write TBPM/TKEY")
    ap.add_argument("--write-bpm", action="store_true", help="When --clean-tags, write TBPM if bpm is known")
    ap.add_argument("--write-key-camelot", action="store_true", help="When --clean-tags, write key as Camelot (e.g., 8A) if parseable")

    ap.add_argument("--online", action="store_true", help="Attempt AcoustID/MusicBrainz enrichment for missing tags (requires fpcalc + ACOUSTID_API_KEY)")
    ap.add_argument(
        "--user-agent",
        type=str,
        default="djrenamer/1.0 (local)",
        help="HTTP User-Agent for MusicBrainz (set something descriptive, ideally with contact info)",
    )

    g = ap.add_mutually_exclusive_group()
    g.add_argument("--auto-album", action="store_true", default=True, help="Auto-detect single-album folders and prefix track numbers (default)")
    g.add_argument("--force-album", action="store_true", help="Always prefix track numbers when TRCK exists")
    g.add_argument("--no-album", action="store_true", help="Never prefix track numbers")

    args = ap.parse_args(argv)

    root = Path(os.path.expanduser(args.path)).resolve()
    mp3s = iter_mp3s(root, args.recursive)
    if not mp3s:
        print("No MP3 files found.", file=sys.stderr)
        return 2

    metas = [read_track_meta(p) for p in mp3s]

    album_on_by_folder: Dict[Path, bool] = {}
    if args.no_album:
        for m in metas:
            album_on_by_folder[m.path.parent] = False
    elif args.force_album:
        for m in metas:
            album_on_by_folder[m.path.parent] = True
    else:
        by_dir: Dict[Path, List[TrackMeta]] = {}
        for m in metas:
            by_dir.setdefault(m.path.parent, []).append(m)
        for d, tms in by_dir.items():
            album_on_by_folder[d] = compute_album_consistency(tms)

    ua = args.user_agent
    limiter = RateLimiter(1.0)

    renamed = skipped = errors = 0

    bar = tqdm(total=len(metas), disable=(args.verbose == 0))
    with cf.ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futures = []
        for tm in metas:
            album_effective = "on" if album_on_by_folder.get(tm.path.parent, False) else "off"
            if args.force_album:
                album_effective = "force"
            if args.no_album:
                album_effective = "off"

            futures.append(
                ex.submit(
                    rename_one,
                    tm.path,
                    include_key_bpm=args.include_key_bpm,
                    album_mode_effective=album_effective,
                    clean_tags=args.clean_tags,
                    write_key_as_camelot=args.write_key_camelot,
                    write_bpm=args.write_bpm,
                    online=args.online,
                    ua=ua,
                    limiter=limiter,
                    dry_run=args.dry_run,
                    verbosity=args.verbose,
                )
            )

        for fut in cf.as_completed(futures):
            status, _, _ = fut.result()
            if status == "renamed":
                renamed += 1
            elif status == "skipped":
                skipped += 1
            else:
                errors += 1
            bar.update(1)
    bar.close()

    if args.verbose >= 1:
        print(f"Done. Renamed: {renamed} | Skipped: {skipped} | Errors: {errors}")
        if args.dry_run:
            print("(Dry run - no files changed)")

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
