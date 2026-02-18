"""API layer for peak limiter functionality."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional
import logging
import concurrent.futures

from crate.core.limiter import (
    LimiterResult,
    limit_file,
    collect_audio_files,
    DEFAULT_CEILING_PERCENT,
)

logger = logging.getLogger(__name__)


class LimiterMode(Enum):
    """Limiter operation mode."""
    ANALYZE = "analyze"  # Report only, no changes
    APPLY = "apply"      # Apply limiting to files


@dataclass
class LimiterRequest:
    """Request to limit audio files.
    
    Attributes:
        paths: Files or directories to process
        mode: analyze or apply
        ceiling_percent: Maximum output level (default: 99.7%)
        release_ms: Limiter release time
        recursive: Process subdirectories
    """
    paths: List[Path]
    mode: LimiterMode = LimiterMode.ANALYZE
    ceiling_percent: float = DEFAULT_CEILING_PERCENT  # 99.7% per Platinum Notes
    release_ms: float = 100.0
    recursive: bool = True


@dataclass
class LimiterStatus:
    """Status of a limiter operation."""
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    needed_limiting: int = 0
    results: List[LimiterResult] = field(default_factory=list)


class LimiterAPI:
    """High-level API for peak limiter operations."""
    
    def __init__(self, max_workers: int = 4, logger: Optional[logging.Logger] = None):
        """Initialize the limiter API.
        
        Args:
            max_workers: Maximum concurrent file operations
            logger: Optional logger instance
        """
        self.max_workers = max_workers
        self.logger = logger or logging.getLogger(__name__)
    
    def limit(self, request: LimiterRequest) -> LimiterStatus:
        """Process files with peak limiting.
        
        Args:
            request: LimiterRequest with paths and options
            
        Returns:
            LimiterStatus with results
        """
        status = LimiterStatus()
        
        # Collect all audio files
        all_files: List[Path] = []
        for path in request.paths:
            all_files.extend(collect_audio_files(path, request.recursive))
        
        status.total = len(all_files)
        
        if not all_files:
            self.logger.warning("No audio files found to process")
            return status
        
        self.logger.info(f"Processing {len(all_files)} files with peak limiter")
        
        # Process files
        dry_run = request.mode == LimiterMode.ANALYZE
        
        def process_file(file_path: Path) -> LimiterResult:
            return limit_file(
                input_path=file_path,
                ceiling_percent=request.ceiling_percent,
                release_ms=request.release_ms,
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
                    if result.samples_limited and result.samples_limited > 0:
                        status.needed_limiting += 1
                else:
                    status.failed += 1
                    self.logger.warning(f"Failed to process {result.path}: {result.error}")
        
        self.logger.info(
            f"Limiter complete: {status.succeeded}/{status.total} succeeded, "
            f"{status.needed_limiting} needed limiting"
        )
        
        return status
