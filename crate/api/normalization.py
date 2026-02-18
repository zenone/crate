"""
Normalization API - Volume leveling for DJ libraries.

Provides ReplayGain-style loudness normalization using EBU R128 (LUFS).

API Contract:
- NormalizationRequest: What to normalize and how
- NormalizationResult: Per-file analysis/adjustment results
- NormalizationAPI: Orchestration layer
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class NormalizationMode(Enum):
    """How to handle normalization."""
    ANALYZE = "analyze"  # Measure only, no changes
    TAG = "tag"          # Write ReplayGain tags (non-destructive)
    APPLY = "apply"      # Modify audio data (destructive)


@dataclass
class NormalizationRequest:
    """Request to normalize audio files.

    Attributes:
        paths: Files or directories to process
        mode: analyze, tag, or apply
        target_lufs: Target loudness (-11.5 is DJ standard per Platinum Notes)
        prevent_clipping: Reduce gain if it would cause clipping
        recursive: Process subdirectories
    """
    paths: List[Path]
    mode: NormalizationMode = NormalizationMode.ANALYZE
    target_lufs: float = -11.5  # DJ standard (Platinum Notes)
    prevent_clipping: bool = True
    recursive: bool = False


@dataclass
class NormalizationResult:
    """Result of normalizing a single file.

    Attributes:
        path: File that was processed
        success: Whether operation succeeded
        original_lufs: Measured loudness (LUFS)
        original_peak_db: Peak amplitude (dB)
        adjustment_db: Gain adjustment needed/applied
        clipping_prevented: Whether gain was reduced to prevent clipping
        error: Error message if failed
    """
    path: Path
    success: bool
    original_lufs: Optional[float] = None
    original_peak_db: Optional[float] = None
    adjustment_db: Optional[float] = None
    clipping_prevented: bool = False
    error: Optional[str] = None


@dataclass
class NormalizationStatus:
    """Status of a normalization batch operation.

    Attributes:
        total: Total files to process
        processed: Files processed so far
        succeeded: Files that succeeded
        failed: Files that failed
        results: Per-file results
    """
    total: int = 0
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    results: List[NormalizationResult] = field(default_factory=list)


class NormalizationAPI:
    """API for audio normalization operations.

    Example:
        >>> api = NormalizationAPI()
        >>> request = NormalizationRequest(
        ...     paths=[Path("track.mp3")],
        ...     mode=NormalizationMode.ANALYZE
        ... )
        >>> status = api.normalize(request)
        >>> print(f"Original: {status.results[0].original_lufs} LUFS")
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the normalization API.

        Args:
            logger: Logger instance (creates default if not provided)
        """
        self.logger = logger or logging.getLogger(__name__)

    def normalize(self, request: NormalizationRequest) -> NormalizationStatus:
        """Normalize files according to request.

        Args:
            request: NormalizationRequest with paths and options

        Returns:
            NormalizationStatus with results for each file
        """
        from ..core.normalization import (
            collect_audio_files,
        )

        status = NormalizationStatus()

        # Collect all audio files
        files = collect_audio_files(request.paths, request.recursive)
        status.total = len(files)

        for file_path in files:
            result = self._process_file(file_path, request)
            status.results.append(result)
            status.processed += 1

            if result.success:
                status.succeeded += 1
            else:
                status.failed += 1

        return status

    def _process_file(
        self,
        file_path: Path,
        request: NormalizationRequest
    ) -> NormalizationResult:
        """Process a single file.

        Args:
            file_path: Path to audio file
            request: NormalizationRequest with options

        Returns:
            NormalizationResult for this file
        """
        from ..core.normalization import (
            analyze_loudness,
            apply_gain,
            calculate_adjustment,
            write_replaygain_tags,
        )

        try:
            # Step 1: Analyze loudness
            lufs, peak_db = analyze_loudness(file_path, self.logger)

            if lufs is None or peak_db is None:
                return NormalizationResult(
                    path=file_path,
                    success=False,
                    error="Failed to analyze loudness"
                )

            # Step 2: Calculate adjustment
            adjustment_db, clipping_prevented = calculate_adjustment(
                current_lufs=lufs,
                target_lufs=request.target_lufs,
                peak_db=peak_db,
                prevent_clipping=request.prevent_clipping
            )

            result = NormalizationResult(
                path=file_path,
                success=True,
                original_lufs=lufs,
                original_peak_db=peak_db,
                adjustment_db=adjustment_db,
                clipping_prevented=clipping_prevented
            )

            # Step 3: Apply changes based on mode
            if request.mode == NormalizationMode.TAG:
                write_replaygain_tags(file_path, adjustment_db, self.logger)
            elif request.mode == NormalizationMode.APPLY:
                apply_gain(file_path, adjustment_db, self.logger)

            return result

        except Exception as e:
            self.logger.error(f"Failed to process {file_path}: {e}")
            return NormalizationResult(
                path=file_path,
                success=False,
                error=str(e)
            )
