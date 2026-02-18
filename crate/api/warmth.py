"""API layer for warmth/saturation functionality."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional
import logging
import concurrent.futures

from crate.core.warmth import (
    WarmthResult,
    apply_warmth,
    collect_audio_files,
    DEFAULT_DRIVE,
    DEFAULT_MIX,
    DEFAULT_TONE,
)

logger = logging.getLogger(__name__)


class WarmthMode(Enum):
    """Warmth operation mode."""
    ANALYZE = "analyze"  # Report only, no changes
    APPLY = "apply"      # Apply warmth to files


@dataclass
class WarmthRequest:
    """Request to apply warmth to audio files.
    
    Attributes:
        paths: Files or directories to process
        mode: analyze or apply
        drive: Saturation amount (0.0 to 1.0, default: 0.15)
        mix: Wet/dry mix (0.0 to 1.0, default: 0.3)
        tone: Tonal balance (0.0=dark, 1.0=bright, default: 0.5)
        recursive: Process subdirectories
    """
    paths: List[Path]
    mode: WarmthMode = WarmthMode.ANALYZE
    drive: float = DEFAULT_DRIVE
    mix: float = DEFAULT_MIX
    tone: float = DEFAULT_TONE
    recursive: bool = True


@dataclass
class WarmthStatus:
    """Status of a warmth operation."""
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    processed: int = 0
    results: List[WarmthResult] = field(default_factory=list)


class WarmthAPI:
    """High-level API for warmth/saturation operations."""
    
    def __init__(self, max_workers: int = 4, logger: Optional[logging.Logger] = None):
        """Initialize the warmth API.
        
        Args:
            max_workers: Maximum concurrent file operations
            logger: Optional logger instance
        """
        self.max_workers = max_workers
        self.logger = logger or logging.getLogger(__name__)
    
    def apply(self, request: WarmthRequest) -> WarmthStatus:
        """Process files with warmth/saturation.
        
        Args:
            request: WarmthRequest with paths and options
            
        Returns:
            WarmthStatus with results
        """
        status = WarmthStatus()
        
        # Collect all audio files
        all_files: List[Path] = []
        for path in request.paths:
            all_files.extend(collect_audio_files(path, request.recursive))
        
        status.total = len(all_files)
        
        if not all_files:
            self.logger.warning("No audio files found to process")
            return status
        
        self.logger.info(f"Processing {len(all_files)} files with warmth")
        
        # Process files
        dry_run = request.mode == WarmthMode.ANALYZE
        
        def process_file(file_path: Path) -> WarmthResult:
            return apply_warmth(
                input_path=file_path,
                drive=request.drive,
                mix=request.mix,
                tone=request.tone,
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
                    if result.harmonics_added:
                        status.processed += 1
                else:
                    status.failed += 1
                    self.logger.warning(f"Failed to process {result.path}: {result.error}")
        
        self.logger.info(
            f"Warmth complete: {status.succeeded}/{status.total} succeeded, "
            f"{status.processed} processed"
        )
        
        return status
