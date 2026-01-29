"""
High-level API for DJ MP3 Renamer.

This orchestrates all core modules and provides a clean interface.
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from pathlib import Path
from typing import Optional, Tuple

from ..core.audio_analysis import auto_detect_metadata, lookup_acoustid
from ..core.config import load_config
from ..core.conflict_resolution import resolve_metadata_conflict
from ..core.io import ReservationBook, find_mp3s, read_mp3_metadata, write_bpm_key_to_tags
from ..core.key_conversion import to_camelot
from ..core.sanitization import safe_filename
from ..core.template import DEFAULT_TEMPLATE, build_default_components, build_filename_from_template
from .models import RenameRequest, RenameResult, RenameStatus


class RenamerAPI:
    """
    High-level API for renaming MP3 files.

    This is the main entry point for programmatic access to the renamer.
    """

    def __init__(self, workers: int = 4, logger: Optional[logging.Logger] = None):
        """
        Initialize the Renamer API.

        Args:
            workers: Number of worker threads for concurrent processing
            logger: Optional logger instance (creates one if not provided)
        """
        self.workers = max(1, workers)
        self.logger = logger or logging.getLogger("dj_mp3_renamer")
        self.config = load_config()  # Load user configuration

    def rename_files(self, request: RenameRequest) -> RenameStatus:
        """
        Rename MP3 files according to request.

        Args:
            request: RenameRequest with path, options, and template

        Returns:
            RenameStatus with overall results

        Examples:
            >>> api = RenamerAPI()
            >>> request = RenameRequest(path=Path("/music"), dry_run=True)
            >>> status = api.rename_files(request)
            >>> print(f"Renamed {status.renamed} files")
        """
        target = request.path.expanduser().resolve()

        if not target.exists():
            self.logger.error("Path does not exist: %s", target)
            return RenameStatus(total=0, renamed=0, skipped=0, errors=0, results=[])

        # Find MP3 files
        if target.is_file():
            mp3s = [target] if target.suffix.lower() == ".mp3" else []
        else:
            mp3s = find_mp3s(target, recursive=request.recursive)

        if not mp3s:
            self.logger.warning("No .mp3 files found at: %s", target)
            return RenameStatus(total=0, renamed=0, skipped=0, errors=0, results=[])

        # Process files
        book = ReservationBook()
        template = request.template or DEFAULT_TEMPLATE

        results = []
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = [
                executor.submit(
                    self._rename_one,
                    src,
                    request.dry_run,
                    template,
                    book,
                    request.auto_detect,
                )
                for src in mp3s
            ]

            # Manual polling loop for responsive cancellation
            # (as_completed blocks, so we poll manually every 100ms)
            processed_count = 0
            pending_futures = set(futures)

            # Call initial progress callback to enable immediate cancellation
            if request.progress_callback:
                try:
                    request.progress_callback(0, "Starting...")
                except Exception as cb_err:
                    if "cancel" in type(cb_err).__name__.lower():
                        self.logger.info(f"Operation cancelled before processing started")
                        for f in pending_futures:
                            f.cancel()
                        raise

            try:
                # Poll for completed futures while checking for cancellation
                iteration = 0
                while pending_futures:
                    iteration += 1
                    # Check for cancellation every iteration
                    if request.progress_callback:
                        try:
                            # DEBUG: Log every 10 iterations
                            if iteration % 10 == 0:
                                self.logger.info(f"🔄 Polling iteration {iteration}: {len(pending_futures)} pending, {processed_count} processed")
                            request.progress_callback(processed_count, "")
                        except Exception as cb_err:
                            self.logger.warning(f"progress_callback raised: {type(cb_err).__name__}: {cb_err}")
                            if "cancel" in type(cb_err).__name__.lower():
                                self.logger.warning(f"⚠️  CANCELLATION EXCEPTION CAUGHT - cancelling {len(pending_futures)} pending futures")
                                for f in pending_futures:
                                    f.cancel()
                                raise

                    # Find completed futures
                    done_futures = {f for f in pending_futures if f.done()}

                    # Process completed futures
                    for future in done_futures:
                        try:
                            result = future.result()
                            results.append(result)

                            # Update progress
                            processed_count += 1
                            if request.progress_callback:
                                try:
                                    request.progress_callback(processed_count, result.src.name)
                                except Exception as cb_err:
                                    if "cancel" in type(cb_err).__name__.lower():
                                        self.logger.info(f"Operation cancelled via progress callback")
                                        for f in pending_futures:
                                            f.cancel()
                                        raise
                                    self.logger.warning(f"Progress callback error: {cb_err}")
                        except Exception as e:
                            # Future raised an exception - still count as processed
                            self.logger.error(f"Future error: {e}")

                    # Remove completed futures from pending set
                    pending_futures -= done_futures

                    # Sleep briefly to avoid busy-waiting (100ms polling interval)
                    if pending_futures:
                        time.sleep(0.1)
            except Exception:
                # On any exception (including cancellation), cancel pending futures
                for f in futures:
                    if not f.done():
                        f.cancel()
                raise  # Re-raise the exception

        # Compute stats
        renamed = sum(1 for r in results if r.status == "renamed")
        skipped = sum(1 for r in results if r.status == "skipped")
        errors = sum(1 for r in results if r.status == "error")

        return RenameStatus(
            total=len(mp3s),
            renamed=renamed,
            skipped=skipped,
            errors=errors,
            results=results,
        )

    def _rename_one(
        self,
        src: Path,
        dry_run: bool,
        template: str,
        book: ReservationBook,
        auto_detect: bool,
    ) -> RenameResult:
        """
        Rename a single file.

        Args:
            src: Source file path
            dry_run: If True, don't actually rename
            template: Filename template
            book: ReservationBook for collision handling
            auto_detect: If True, auto-detect BPM/Key if missing

        Returns:
            RenameResult
        """
        try:
            dst, reason, meta = self._derive_target(src, template, book, auto_detect)

            if dst is None:
                self.logger.info("SKIP  %s  (%s)", src.name, reason)
                return RenameResult(src=src, dst=None, status="skipped", message=reason, metadata=meta)

            if dry_run:
                self.logger.info("DRY   %s  ->  %s", src.name, dst.name)
                return RenameResult(src=src, dst=dst, status="renamed", message="dry-run", metadata=meta)

            os.replace(src.as_posix(), dst.as_posix())
            self.logger.info("REN   %s  ->  %s", src.name, dst.name)
            return RenameResult(src=src, dst=dst, status="renamed", metadata=meta)

        except Exception as exc:
            self.logger.error("ERR   %s  (%s)", src, exc)
            self.logger.debug("Trace", exc_info=True)
            return RenameResult(src=src, dst=None, status="error", message=str(exc), metadata=None)

    def _enhance_metadata(self, src: Path, meta: dict) -> dict:
        """
        Enhance metadata using MusicBrainz and AI audio analysis with conflict resolution.

        Args:
            src: Source file path
            meta: Metadata from ID3 tags

        Returns:
            Enhanced metadata dictionary
        """
        verify_mode = self.config.get("verify_mode", False)
        enable_mb = self.config.get("enable_musicbrainz", False)
        use_mb_for_all = self.config.get("use_mb_for_all_fields", True)

        # Check what needs detection
        needs_bpm = not meta.get("bpm", "").strip() or verify_mode
        needs_key = not meta.get("key", "").strip() or verify_mode
        needs_artist = not meta.get("artist", "").strip() or meta.get("artist") == "Unknown Artist"
        needs_title = not meta.get("title", "").strip() or meta.get("title") == "Unknown Title"

        mb_data = None
        mb_confidence = 0.0

        # Step 1: MusicBrainz lookup (if enabled)
        if enable_mb and (needs_bpm or needs_key or (use_mb_for_all and (needs_artist or needs_title))):
            try:
                self.logger.info(f"Looking up MusicBrainz data for: {src.name}")
                mb_data, mb_source = lookup_acoustid(src, self.logger, self.config.get("acoustid_api_key"))

                if mb_data and mb_source == "Database":
                    mb_confidence = mb_data.get("confidence", 0.0)
                    self.logger.info(f"  MusicBrainz match found (confidence: {mb_confidence:.2f})")
            except Exception as mb_err:
                self.logger.warning(f"MusicBrainz lookup failed: {mb_err}")

        # Step 2: AI Audio analysis for BPM/Key (if still needed)
        ai_bpm = None
        ai_key = None

        if needs_bpm or needs_key:
            try:
                self.logger.info(f"Analyzing audio for: {src.name}")
                ai_bpm, bpm_src, ai_key, key_src = auto_detect_metadata(
                    src,
                    meta.get("bpm", ""),
                    meta.get("key", ""),
                    self.logger,
                    enable_musicbrainz=False,  # Already did MB lookup above
                    acoustid_api_key=self.config.get("acoustid_api_key")
                )
            except Exception as ai_err:
                self.logger.error(f"AI audio analysis failed: {ai_err}", exc_info=True)

        # Step 3: Resolve conflicts for each field
        conflicts = []

        # Artist
        if use_mb_for_all and mb_data:
            artist_resolution = resolve_metadata_conflict(
                "artist",
                meta.get("artist"),
                mb_data.get("artist"),
                None,
                mb_confidence,
                verify_mode
            )
            if artist_resolution["conflicts"]:
                conflicts.extend(artist_resolution["conflicts"])
            if artist_resolution["overridden"]:
                self.logger.info(f"  Artist: {artist_resolution['overridden']}")
            meta["artist"] = artist_resolution["final_value"]
            meta["artist_source"] = artist_resolution["source"]

        # Title
        if use_mb_for_all and mb_data:
            title_resolution = resolve_metadata_conflict(
                "title",
                meta.get("title"),
                mb_data.get("title"),
                None,
                mb_confidence,
                verify_mode
            )
            if title_resolution["conflicts"]:
                conflicts.extend(title_resolution["conflicts"])
            if title_resolution["overridden"]:
                self.logger.info(f"  Title: {title_resolution['overridden']}")
            meta["title"] = title_resolution["final_value"]
            meta["title_source"] = title_resolution["source"]

        # BPM
        bpm_resolution = resolve_metadata_conflict(
            "bpm",
            meta.get("bpm"),
            mb_data.get("bpm") if mb_data else None,
            ai_bpm,
            mb_confidence,
            verify_mode
        )
        if bpm_resolution["conflicts"]:
            conflicts.extend(bpm_resolution["conflicts"])
            for conflict in bpm_resolution["conflicts"]:
                self.logger.warning(f"  BPM conflict: {conflict}")
        meta["bpm"] = bpm_resolution["final_value"]
        meta["bpm_source"] = bpm_resolution["source"]

        # Key
        key_resolution = resolve_metadata_conflict(
            "key",
            meta.get("key"),
            mb_data.get("key") if mb_data else None,
            ai_key,
            mb_confidence,
            verify_mode
        )
        if key_resolution["conflicts"]:
            conflicts.extend(key_resolution["conflicts"])
            for conflict in key_resolution["conflicts"]:
                self.logger.warning(f"  Key conflict: {conflict}")
        meta["key"] = key_resolution["final_value"]
        meta["key_source"] = key_resolution["source"]

        # Update Camelot from resolved key
        meta["camelot"] = to_camelot(meta["key"]) if meta["key"] else ""

        # Step 4: Write enhanced data back to tags
        try:
            needs_write = False
            write_bpm = None
            write_key = None

            if bpm_resolution["source"] in ["MusicBrainz", "AI Audio"] and meta["bpm"]:
                write_bpm = meta["bpm"]
                needs_write = True

            if key_resolution["source"] in ["MusicBrainz", "AI Audio"] and meta["key"]:
                write_key = meta["key"]
                needs_write = True

            if needs_write:
                write_success = write_bpm_key_to_tags(src, write_bpm, write_key, self.logger)
                if write_success:
                    self.logger.info(f"  Saved enhanced metadata to ID3 tags")
        except Exception as tag_err:
            self.logger.error(f"  Failed to write tags: {tag_err}")

        # Add conflicts to metadata for potential UI display
        if conflicts:
            meta["conflicts"] = conflicts

        return meta

    def _derive_target(
        self,
        src: Path,
        template: str,
        book: ReservationBook,
        auto_detect: bool,
    ) -> Tuple[Optional[Path], Optional[str], Optional[dict]]:
        """
        Derive target path for a source file.

        Args:
            src: Source file path
            template: Filename template
            book: ReservationBook
            auto_detect: If True, auto-detect BPM/Key if missing

        Returns:
            Tuple of (target_path, error_message, metadata)
        """
        meta, err = read_mp3_metadata(src, self.logger)
        if err:
            return None, err, None
        assert meta is not None

        # Enhanced metadata detection and validation
        if auto_detect:
            meta = self._enhance_metadata(src, meta)
        else:
            # Just set sources for existing data
            if meta.get("bpm"):
                meta["bpm_source"] = "Tags"
            if meta.get("key"):
                meta["key_source"] = "Tags"

        tokens = build_default_components(meta)
        expanded = build_filename_from_template(tokens, template)
        stem = safe_filename(expanded)

        ext = src.suffix.lower() if src.suffix else ".mp3"
        if ext != ".mp3":
            ext = ".mp3"

        # Check if the file already has the desired name BEFORE collision handling
        desired_path = src.parent / f"{stem}{ext}"
        if desired_path.resolve() == src.resolve():
            return None, "Already has desired name", meta

        # File needs renaming - use collision detection
        dst = book.reserve_unique(src.parent, stem, ext)
        return dst, None, meta
