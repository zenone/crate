"""
High-level API for DJ MP3 Renamer.

This orchestrates all core modules and provides a clean interface.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Tuple

from ..core.audio_analysis import auto_detect_metadata
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

            processed_count = 0
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

                # Call progress callback if provided
                processed_count += 1
                if request.progress_callback:
                    try:
                        request.progress_callback(processed_count, result.src.name)
                    except Exception as cb_err:
                        # Check if this is a cancellation request (exception name contains "cancel")
                        if "cancel" in type(cb_err).__name__.lower():
                            self.logger.info(f"Operation cancelled via progress callback")
                            raise  # Re-raise cancellation exceptions to stop processing
                        self.logger.warning(f"Progress callback error: {cb_err}")

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

        # Auto-detect BPM/Key if missing and auto_detect is enabled
        if auto_detect:
            needs_bpm = not meta.get("bpm", "").strip()
            needs_key = not meta.get("key", "").strip()

            if needs_bpm or needs_key:
                try:
                    self.logger.info(f"Auto-detecting metadata for: {src.name}")

                    # Run detection (wrapped in try/except for safety)
                    detected_bpm, bpm_source, detected_key, key_source = auto_detect_metadata(
                        src,
                        meta.get("bpm", ""),
                        meta.get("key", ""),
                        self.logger
                    )

                    # Update metadata dict
                    if needs_bpm and detected_bpm:
                        meta["bpm"] = detected_bpm
                        meta["bpm_source"] = bpm_source
                        self.logger.info(f"  Detected BPM: {detected_bpm} (source: {bpm_source})")

                    if needs_key and detected_key:
                        meta["key"] = detected_key
                        meta["camelot"] = to_camelot(detected_key) if detected_key else ""
                        meta["key_source"] = key_source
                        self.logger.info(f"  Detected Key: {detected_key} (source: {key_source})")

                    # Write detected values to ID3 tags (permanent storage)
                    if (needs_bpm and detected_bpm) or (needs_key and detected_key):
                        try:
                            write_success = write_bpm_key_to_tags(
                                src,
                                detected_bpm if needs_bpm else None,
                                detected_key if needs_key else None,
                                self.logger
                            )
                            if write_success:
                                self.logger.info(f"  Saved detected metadata to ID3 tags")
                        except Exception as tag_err:
                            self.logger.error(f"  Failed to write tags: {tag_err}")

                except Exception as detect_err:
                    self.logger.error(f"Auto-detection failed for {src.name}: {detect_err}", exc_info=True)
                    # Continue processing even if auto-detection fails
                    meta["bpm_source"] = "Failed"
                    meta["key_source"] = "Failed"

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
