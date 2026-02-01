"""
High-level API for DJ MP3 Renamer.

This orchestrates all core modules and provides a clean interface.
"""

import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from pathlib import Path
from typing import Optional, Tuple

from ..core.audio_analysis import auto_detect_metadata, lookup_acoustid
from ..core.audio_analysis_parallel import (
    parallel_audio_analysis,
    batch_audio_analysis,
    estimate_analysis_time,
    log_performance_comparison,
    detect_optimal_worker_count
)
from ..core.config import load_config, save_config, clear_config_cache, get_config_value as core_get_config_value, set_config_value as core_set_config_value, DEFAULT_CONFIG
from ..core.conflict_resolution import resolve_metadata_conflict
from ..core.io import ReservationBook, find_mp3s, read_mp3_metadata, write_bpm_key_to_tags
from ..core.key_conversion import to_camelot
from ..core.sanitization import safe_filename
from ..core.template import DEFAULT_TEMPLATE, build_default_components, build_filename_from_template
from .models import RenameRequest, RenameResult, RenameStatus, OperationStatus, FilePreview, TemplateValidation


class OperationCancelled(Exception):
    """Raised when operation is cancelled by user."""
    pass


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
        self.logger = logger or logging.getLogger("crate")
        self.config = load_config()  # Load user configuration

        # Async operation tracking
        self._operations: dict[str, dict] = {}
        self._lock = threading.Lock()

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
        if request.file_paths:
            # Use specific file paths if provided
            mp3s = [Path(fp).expanduser().resolve() for fp in request.file_paths if Path(fp).suffix.lower() == ".mp3"]
        elif target.is_file():
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
            dst, reason, meta = self._derive_target(
                src, template, book, auto_detect,
                write_tags=True  # Rename operations write enhanced metadata
            )

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

    def _enhance_metadata(self, src: Path, meta: dict, write_tags: bool = True) -> dict:
        """
        Enhance metadata using MusicBrainz and AI audio analysis with conflict resolution.

        Args:
            src: Source file path
            meta: Metadata from ID3 tags
            write_tags: If True, write enhanced metadata back to ID3 tags (default: True)
                       Set to False for preview operations (read-only)

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

        # Step 4: Write enhanced data back to tags (only if write_tags=True)
        if write_tags:
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
        else:
            self.logger.debug(f"  Skipping tag write (preview mode)")

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
        write_tags: bool = True,
    ) -> Tuple[Optional[Path], Optional[str], Optional[dict]]:
        """
        Derive target path for a source file.

        Args:
            src: Source file path
            template: Filename template
            book: ReservationBook
            auto_detect: If True, auto-detect BPM/Key if missing
            write_tags: If True, write enhanced metadata back to ID3 tags (default: True)
                       Set to False for preview operations (read-only)

        Returns:
            Tuple of (target_path, error_message, metadata)
        """
        meta, err = read_mp3_metadata(src, self.logger)
        if err:
            return None, err, None
        assert meta is not None

        # Enhanced metadata detection and validation
        if auto_detect:
            meta = self._enhance_metadata(src, meta, write_tags=write_tags)
        else:
            # Just set sources for existing data
            if meta.get("bpm"):
                meta["bpm_source"] = "Tags"
            if meta.get("key"):
                meta["key_source"] = "Tags"

        tokens = build_default_components(meta, self.config)
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

    # Async Operation Support

    def start_rename_async(self, request: RenameRequest) -> str:
        """
        Start rename operation asynchronously.

        This method returns immediately with an operation ID. Use
        get_operation_status() to poll for progress and results.

        Args:
            request: RenameRequest with path, options, and template

        Returns:
            operation_id: UUID for tracking operation

        Examples:
            >>> api = RenamerAPI()
            >>> request = RenameRequest(path=Path("/music"), dry_run=False)
            >>> operation_id = api.start_rename_async(request)
            >>>
            >>> # Poll for status
            >>> while True:
            >>>     status = api.get_operation_status(operation_id)
            >>>     if status.status != "running":
            >>>         break
            >>>     print(f"Progress: {status.progress}/{status.total}")
            >>>     time.sleep(0.5)
        """
        operation_id = str(uuid.uuid4())

        # Initialize operation state
        with self._lock:
            self._operations[operation_id] = {
                "status": "running",
                "progress": 0,
                "total": 0,
                "current_file": "",
                "start_time": time.time(),
                "end_time": None,
                "results": None,
                "error": None,
                "cancelled": False,
            }

        # Start operation in background thread
        thread = threading.Thread(
            target=self._run_operation_async,
            args=(operation_id, request),
            daemon=True,
            name=f"rename-{operation_id[:8]}"
        )
        thread.start()

        self.logger.info(f"Started async operation {operation_id}")
        return operation_id

    def _run_operation_async(self, operation_id: str, request: RenameRequest) -> None:
        """
        Run operation asynchronously in background thread.

        Updates operation state as it progresses. Called by start_rename_async().

        Args:
            operation_id: Operation ID
            request: RenameRequest
        """
        # Find files to get total count
        target = request.path.expanduser().resolve()
        if not target.exists():
            with self._lock:
                self._operations[operation_id]["status"] = "error"
                self._operations[operation_id]["error"] = f"Path does not exist: {target}"
                self._operations[operation_id]["end_time"] = time.time()
            return

        # Use specific file paths if provided, otherwise find all MP3s
        if request.file_paths:
            # Use specific files passed in request (for selective rename)
            self.logger.info(f"Using {len(request.file_paths)} specific files from request")
            mp3s = [Path(fp).expanduser().resolve() for fp in request.file_paths]
            # Filter to only existing MP3 files
            mp3s = [f for f in mp3s if f.exists() and f.suffix.lower() == ".mp3"]
            self.logger.info(f"After filtering: {len(mp3s)} valid MP3 files found")
        elif target.is_file():
            mp3s = [target] if target.suffix.lower() == ".mp3" else []
        else:
            mp3s = find_mp3s(target, recursive=request.recursive)

        # Update total count
        with self._lock:
            self._operations[operation_id]["total"] = len(mp3s)

        if not mp3s:
            with self._lock:
                self._operations[operation_id]["status"] = "completed"
                self._operations[operation_id]["end_time"] = time.time()
                self._operations[operation_id]["results"] = RenameStatus(
                    total=0, renamed=0, skipped=0, errors=0, results=[]
                )
            return

        # Define progress callback that updates state and checks cancellation
        def progress_callback(count: int, filename: str):
            with self._lock:
                if self._operations[operation_id]["cancelled"]:
                    raise OperationCancelled("Operation cancelled by user")
                self._operations[operation_id]["progress"] = count
                self._operations[operation_id]["current_file"] = filename

        # Create modified request with our progress callback
        async_request = RenameRequest(
            path=request.path,
            recursive=request.recursive,
            dry_run=request.dry_run,
            template=request.template,
            auto_detect=request.auto_detect,
            file_paths=request.file_paths,  # ← FIX: Pass specific files to rename_files()
            progress_callback=progress_callback
        )

        try:
            # Run the operation (this blocks until complete)
            results = self.rename_files(async_request)

            # Update state with results
            with self._lock:
                self._operations[operation_id]["status"] = "completed"
                self._operations[operation_id]["end_time"] = time.time()
                self._operations[operation_id]["results"] = results

            self.logger.info(f"Operation {operation_id} completed: {results.renamed} renamed")

        except OperationCancelled:
            with self._lock:
                self._operations[operation_id]["status"] = "cancelled"
                self._operations[operation_id]["end_time"] = time.time()
            self.logger.info(f"Operation {operation_id} cancelled by user")

        except Exception as e:
            self.logger.error(f"Operation {operation_id} failed: {e}", exc_info=True)
            with self._lock:
                self._operations[operation_id]["status"] = "error"
                self._operations[operation_id]["end_time"] = time.time()
                self._operations[operation_id]["error"] = str(e)

    def get_operation_status(self, operation_id: str) -> Optional[OperationStatus]:
        """
        Get status of an asynchronous operation.

        Args:
            operation_id: Operation ID from start_rename_async()

        Returns:
            OperationStatus or None if operation not found

        Examples:
            >>> status = api.get_operation_status(operation_id)
            >>> if status:
            >>>     print(f"Status: {status.status}")
            >>>     print(f"Progress: {status.progress}/{status.total}")
            >>> else:
            >>>     print("Operation not found")
        """
        with self._lock:
            if operation_id not in self._operations:
                return None

            op = self._operations[operation_id]
            return OperationStatus(
                operation_id=operation_id,
                status=op["status"],
                progress=op["progress"],
                total=op["total"],
                current_file=op["current_file"],
                start_time=op["start_time"],
                end_time=op["end_time"],
                results=op["results"],
                error=op["error"]
            )

    def cancel_operation(self, operation_id: str) -> bool:
        """
        Cancel a running operation.

        The operation will stop gracefully after processing the current file.

        Args:
            operation_id: Operation ID to cancel

        Returns:
            True if operation was cancelled, False if not found or already complete

        Examples:
            >>> success = api.cancel_operation(operation_id)
            >>> if success:
            >>>     print("Cancellation requested")
            >>> else:
            >>>     print("Operation not running or already complete")
        """
        with self._lock:
            if operation_id not in self._operations:
                return False

            op = self._operations[operation_id]
            if op["status"] != "running":
                return False  # Already complete/cancelled/error

            op["cancelled"] = True
            self.logger.info(f"Cancellation requested for operation {operation_id}")
            return True

    def clear_operation(self, operation_id: str) -> bool:
        """
        Remove operation from tracking (cleanup).

        Use this after retrieving results to free memory. Operations are
        kept indefinitely until cleared.

        Args:
            operation_id: Operation ID to remove

        Returns:
            True if removed, False if not found

        Examples:
            >>> # Get final results
            >>> status = api.get_operation_status(operation_id)
            >>> # Process results...
            >>> # Clean up
            >>> api.clear_operation(operation_id)
        """
        with self._lock:
            if operation_id in self._operations:
                del self._operations[operation_id]
                self.logger.debug(f"Cleared operation {operation_id}")
                return True
            return False

    # File Preview Support

    def preview_rename(self, request: RenameRequest) -> list[FilePreview]:
        """
        Preview rename operation without executing.

        Shows what files would be renamed and their new names. Useful for
        displaying confirmation dialog before applying changes.

        Args:
            request: RenameRequest (dry_run and progress_callback ignored)

        Returns:
            List of FilePreview objects showing old → new names

        Examples:
            >>> api = RenamerAPI()
            >>> request = RenameRequest(path=Path("/music"))
            >>> previews = api.preview_rename(request)
            >>> for p in previews:
            >>>     if p.status == "will_rename":
            >>>         print(f"{p.src.name} → {p.dst.name}")
            >>>     elif p.status == "will_skip":
            >>>         print(f"{p.src.name}: {p.reason}")

        Notes:
            - This is a fast operation (no audio analysis)
            - Does not modify any files
            - Uses collision detection (ReservationBook)
        """
        target = request.path.expanduser().resolve()

        if not target.exists():
            self.logger.warning(f"Path does not exist: {target}")
            return []

        # Find MP3 files
        if request.file_paths:
            # Use specific file paths if provided
            mp3s = [Path(fp).expanduser().resolve() for fp in request.file_paths if Path(fp).suffix.lower() == ".mp3"]
        elif target.is_file():
            mp3s = [target] if target.suffix.lower() == ".mp3" else []
        else:
            mp3s = find_mp3s(target, recursive=request.recursive)

        if not mp3s:
            self.logger.info(f"No MP3 files found at: {target}")
            return []

        # Calculate targets for each file
        previews = []
        book = ReservationBook()
        template = request.template or DEFAULT_TEMPLATE

        for src in mp3s:
            try:
                # Get target path
                # Task #122: Pass write_tags=False to prevent disk writes during preview
                dst, reason, meta = self._derive_target(
                    src, template, book,
                    auto_detect=request.auto_detect,  # Use request setting
                    write_tags=False  # CRITICAL: Preview must be read-only
                )

                if dst:
                    previews.append(FilePreview(
                        src=src,
                        dst=dst,
                        status="will_rename",
                        metadata=meta
                    ))
                else:
                    previews.append(FilePreview(
                        src=src,
                        dst=None,
                        status="will_skip",
                        reason=reason,
                        metadata=meta
                    ))

            except Exception as e:
                self.logger.error(f"Preview error for {src}: {e}")
                previews.append(FilePreview(
                    src=src,
                    dst=None,
                    status="error",
                    reason=str(e),
                    metadata=None
                ))

        return previews

    # Config Management Support

    def get_config(self) -> dict:
        """
        Get current configuration.

        Returns all configuration settings including user overrides
        and defaults.

        Returns:
            Configuration dictionary with all settings

        Examples:
            >>> api = RenamerAPI()
            >>> config = api.get_config()
            >>> print(config["default_template"])
            {artist} - {title} [{camelot} {bpm}]
        """
        return load_config()

    def update_config(self, updates: dict) -> bool:
        """
        Update configuration values.

        Merges provided updates into existing configuration and saves.
        Automatically updates the instance config and clears cache.

        Args:
            updates: Dictionary of key-value pairs to update

        Returns:
            True if successful, False otherwise

        Examples:
            >>> api = RenamerAPI()
            >>> success = api.update_config({
            >>>     "default_template": "{bpm} - {artist} - {title}",
            >>>     "auto_detect_bpm": False
            >>> })
            >>> if success:
            >>>     print("Config updated")
        """
        config = load_config()
        config.update(updates)
        success = save_config(config)
        if success:
            self.config = config
            clear_config_cache()
        return success

    def get_config_value(self, key: str, default=None):
        """
        Get single configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default

        Examples:
            >>> api = RenamerAPI()
            >>> template = api.get_config_value("default_template")
            >>> print(template)
        """
        return self.config.get(key, default)

    def set_config_value(self, key: str, value) -> bool:
        """
        Set single configuration value.

        Args:
            key: Configuration key
            value: Value to set

        Returns:
            True if successful, False otherwise

        Examples:
            >>> api = RenamerAPI()
            >>> success = api.set_config_value("auto_detect_bpm", False)
            >>> if success:
            >>>     print("Config updated")
        """
        self.config[key] = value
        success = save_config(self.config)
        if success:
            clear_config_cache()
        return success

    def get_default_config(self) -> dict:
        """
        Get default configuration values.

        Returns configuration defaults without any user overrides.
        Useful for reset functionality.

        Returns:
            Default configuration dictionary

        Examples:
            >>> api = RenamerAPI()
            >>> defaults = api.get_default_config()
            >>> print(defaults["auto_detect_bpm"])
            True
        """
        return DEFAULT_CONFIG.copy()

    # Template Validation Support

    def validate_template(self, template: str) -> TemplateValidation:
        """
        Validate filename template.

        Checks template for invalid characters, unknown variables, and
        generates example output with sample data. Useful for real-time
        validation in template editors.

        Args:
            template: Template string to validate

        Returns:
            TemplateValidation with errors, warnings, and example

        Examples:
            >>> api = RenamerAPI()
            >>> result = api.validate_template("{artist} - {title}")
            >>> if result.valid:
            >>>     print(f"Valid! Example: {result.example}")
            >>> else:
            >>>     print(f"Errors: {result.errors}")
        """
        errors = []
        warnings = []

        # Check for empty template
        if not template or template.strip() == "":
            errors.append("Template cannot be empty")
            return TemplateValidation(
                valid=False,
                errors=errors,
                warnings=warnings,
                example=None
            )

        # Check for invalid filename characters
        invalid_chars = r'\/:*?"<>|'
        found_invalid = [c for c in invalid_chars if c in template]
        if found_invalid:
            errors.append(
                f"Template contains invalid filename characters: {', '.join(repr(c) for c in found_invalid)}"
            )

        # Check for leading/trailing spaces
        if template.startswith(" ") or template.endswith(" "):
            warnings.append("Template has leading or trailing spaces (will be trimmed)")

        # Check for multiple consecutive spaces
        if "  " in template:
            warnings.append("Template contains multiple consecutive spaces")

        # Try to expand with sample data
        sample_meta = {
            "artist": "Sample Artist",
            "title": "Sample Title",
            "bpm": "128",
            "key": "Am",
            "camelot": "8A",
            "album": "Sample Album",
            "year": "2024",
            "label": "Sample Label",
            "track": "01",
            "mix": "Original Mix",
        }

        example = None
        try:
            # Use config for padding if available (for consistent examples)
            tokens = build_default_components(sample_meta, self.config)
            expanded = build_filename_from_template(tokens, template)
            example = safe_filename(expanded)

            # Check if example is empty after sanitization
            if not example or example.strip() == "":
                errors.append("Template produces empty filename after sanitization")

            # Check for unresolved template variables in output
            if example and "{" in example and "}" in example:
                # Find unresolved variables
                import re
                unresolved = re.findall(r'\{(\w+)\}', example)
                if unresolved:
                    for var in unresolved:
                        errors.append(f"Unknown template variable: {{{var}}}")

            # Check for very long filenames
            if example and len(example) > 200:
                warnings.append(f"Template produces long filename ({len(example)} characters)")

        except KeyError as e:
            # Unknown template variable (shouldn't happen with build_filename_from_template)
            var_name = str(e).strip("'\"")
            errors.append(f"Unknown template variable: {{{var_name}}}")
        except Exception as e:
            # Other template expansion error
            errors.append(f"Template expansion error: {str(e)}")

        # Final validation
        valid = len(errors) == 0

        return TemplateValidation(
            valid=valid,
            errors=errors,
            warnings=warnings,
            example=example
        )

    # Metadata Enhancement Support

    def analyze_file(self, file_path: Path) -> Optional[dict]:
        """
        Analyze single file metadata.

        Performs comprehensive metadata analysis including:
        - Reading existing ID3 tags
        - MusicBrainz lookup (if enabled)
        - AI audio analysis for BPM/Key
        - Conflict resolution between sources
        - Returns enhanced metadata

        Args:
            file_path: Path to MP3 file

        Returns:
            Enhanced metadata dict or None if error

        Examples:
            >>> api = RenamerAPI()
            >>> metadata = api.analyze_file(Path("/music/track.mp3"))
            >>> if metadata:
            >>>     print(f"BPM: {metadata['bpm']} (from {metadata['bpm_source']})")
            >>>     print(f"Key: {metadata['key']} (from {metadata['key_source']})")

        Notes:
            - Respects config settings (enable_musicbrainz, auto_detect_*)
            - May take several seconds for full analysis
            - Returns None if file cannot be read
        """
        # Read existing metadata
        meta, err = read_mp3_metadata(file_path, self.logger)
        if err:
            self.logger.error(f"Failed to read {file_path}: {err}")
            return None

        # Enhance with MusicBrainz + AI analysis
        try:
            enhanced = self._enhance_metadata(file_path, meta)
            return enhanced
        except Exception as e:
            self.logger.error(f"Failed to enhance metadata for {file_path}: {e}", exc_info=True)
            return None
