"""API layer for clipped peak repair functionality."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional
import logging
import concurrent.futures

from crate.core.clip_repair import (
    ClipRepairResult,
    repair_file,
    collect_audio_files,
    DEFAULT_CLIP_THRESHOLD,
    DEFAULT_MIN_CLIP_SAMPLES,
)

logger = logging.getLogger(__name__)


class ClipRepairMode(Enum):
    """Clip repair operation mode."""
    ANALYZE = "analyze"  # Report only, no changes
    APPLY = "apply"      # Apply repair to files


@dataclass
class ClipRepairRequest:
    """Request to repair clipped audio files.
    
    Attributes:
        paths: Files or directories to process
        mode: analyze or apply
        threshold: Amplitude threshold for clipping detection (default: 0.99)
        min_samples: Minimum consecutive samples to count as clipping
        recursive: Process subdirectories
    """
    paths: List[Path]
    mode: ClipRepairMode = ClipRepairMode.ANALYZE
    threshold: float = DEFAULT_CLIP_THRESHOLD
    min_samples: int = DEFAULT_MIN_CLIP_SAMPLES
    recursive: bool = True


@dataclass
class ClipRepairStatus:
    """Status of a clip repair operation."""
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    needed_repair: int = 0
    total_clips_repaired: int = 0
    results: List[ClipRepairResult] = field(default_factory=list)


class ClipRepairAPI:
    """High-level API for clipped peak repair operations."""
    
    def __init__(self, max_workers: int = 4, logger: Optional[logging.Logger] = None):
        """Initialize the clip repair API.
        
        Args:
            max_workers: Maximum concurrent file operations
            logger: Optional logger instance
        """
        self.max_workers = max_workers
        self.logger = logger or logging.getLogger(__name__)
    
    def repair(self, request: ClipRepairRequest) -> ClipRepairStatus:
        """Process files with clip repair.
        
        Args:
            request: ClipRepairRequest with paths and options
            
        Returns:
            ClipRepairStatus with results
        """
        status = ClipRepairStatus()
        
        # Collect all audio files
        all_files: List[Path] = []
        for path in request.paths:
            all_files.extend(collect_audio_files(path, request.recursive))
        
        status.total = len(all_files)
        
        if not all_files:
            self.logger.warning("No audio files found to process")
            return status
        
        self.logger.info(f"Processing {len(all_files)} files for clip repair")
        
        # Process files
        dry_run = request.mode == ClipRepairMode.ANALYZE
        
        def process_file(file_path: Path) -> ClipRepairResult:
            return repair_file(
                input_path=file_path,
                threshold=request.threshold,
                min_samples=request.min_samples,
                dry_run=dry_run,
            )
        
        # Use thread pool for I/O-bound operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(process_file, f): f for f in all_files}
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                status.results.append(result)
                
                if result.success:
                    status.succeeded += 1
                    if result.clips_repaired and result.clips_repaired > 0:
                        status.needed_repair += 1
                        status.total_clips_repaired += result.clips_repaired
                else:
                    status.failed += 1
                    self.logger.warning(f"Failed to process {result.path}: {result.error}")
        
        self.logger.info(
            f"Clip repair complete: {status.succeeded}/{status.total} succeeded, "
            f"{status.needed_repair} had clipping, {status.total_clips_repaired} clips repaired"
        )
        
        return status
