"""API layer for pitch correction functionality."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional
import logging
import concurrent.futures

from crate.core.pitch_correction import (
    PitchAnalysisResult,
    PitchCorrectionResult,
    analyze_pitch,
    correct_pitch,
    collect_audio_files,
    DEFAULT_THRESHOLD_CENTS,
)

logger = logging.getLogger(__name__)


class PitchCorrectionMode(Enum):
    """Pitch correction operation mode."""
    ANALYZE = "analyze"  # Report only, no changes
    CORRECT = "correct"  # Apply pitch correction


@dataclass
class PitchCorrectionRequest:
    """Request to analyze/correct pitch in audio files.
    
    Attributes:
        paths: Files or directories to process
        mode: analyze or correct
        threshold_cents: Minimum deviation to flag/correct (default: 10)
        recursive: Process subdirectories
    """
    paths: List[Path]
    mode: PitchCorrectionMode = PitchCorrectionMode.ANALYZE
    threshold_cents: float = DEFAULT_THRESHOLD_CENTS  # 10 cents per Platinum Notes
    recursive: bool = True


@dataclass
class PitchCorrectionStatus:
    """Status of a pitch correction operation."""
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    needs_correction: int = 0
    results: List[PitchCorrectionResult] = field(default_factory=list)


class PitchCorrectionAPI:
    """High-level API for pitch correction operations."""
    
    def __init__(self, max_workers: int = 2, logger: Optional[logging.Logger] = None):
        """Initialize the pitch correction API.
        
        Args:
            max_workers: Maximum concurrent file operations (lower for CPU-bound)
            logger: Optional logger instance
        """
        self.max_workers = max_workers
        self.logger = logger or logging.getLogger(__name__)
    
    def process(self, request: PitchCorrectionRequest) -> PitchCorrectionStatus:
        """Process files for pitch analysis/correction.
        
        Args:
            request: PitchCorrectionRequest with paths and options
            
        Returns:
            PitchCorrectionStatus with results
        """
        status = PitchCorrectionStatus()
        
        # Collect all audio files
        all_files: List[Path] = []
        for path in request.paths:
            all_files.extend(collect_audio_files(path, request.recursive))
        
        status.total = len(all_files)
        
        if not all_files:
            self.logger.warning("No audio files found to process")
            return status
        
        self.logger.info(f"Processing {len(all_files)} files for pitch correction")
        
        # Process files
        dry_run = request.mode == PitchCorrectionMode.ANALYZE
        
        def process_file(file_path: Path) -> PitchCorrectionResult:
            return correct_pitch(
                input_path=file_path,
                threshold_cents=request.threshold_cents,
                dry_run=dry_run,
            )
        
        # Use thread pool (pitch detection is CPU-bound but librosa releases GIL)
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(process_file, f): f for f in all_files}
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                status.results.append(result)
                
                if result.success:
                    status.succeeded += 1
                    # Check if needed correction (shift_cents != 0)
                    if result.shift_cents and abs(result.shift_cents) >= request.threshold_cents:
                        status.needs_correction += 1
                else:
                    status.failed += 1
                    self.logger.warning(f"Failed to process {result.path}: {result.error}")
        
        self.logger.info(
            f"Pitch analysis complete: {status.succeeded}/{status.total} succeeded, "
            f"{status.needs_correction} need correction"
        )
        
        return status
