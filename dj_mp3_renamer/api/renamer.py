"""
High-level API for DJ MP3 Renamer.

This orchestrates all core modules and provides a clean interface.
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Tuple

from ..core.io import ReservationBook, find_mp3s, read_mp3_metadata
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
                )
                for src in mp3s
            ]

            for future in as_completed(futures):
                result = future.result()
                results.append(result)

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
    ) -> RenameResult:
        """
        Rename a single file.

        Args:
            src: Source file path
            dry_run: If True, don't actually rename
            template: Filename template
            book: ReservationBook for collision handling

        Returns:
            RenameResult
        """
        try:
            dst, reason, meta = self._derive_target(src, template, book)

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
    ) -> Tuple[Optional[Path], Optional[str], Optional[dict]]:
        """
        Derive target path for a source file.

        Args:
            src: Source file path
            template: Filename template
            book: ReservationBook

        Returns:
            Tuple of (target_path, error_message, metadata)
        """
        meta, err = read_mp3_metadata(src, self.logger)
        if err:
            return None, err, None
        assert meta is not None

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
