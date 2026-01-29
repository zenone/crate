"""
Data models for the API layer.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


@dataclass(frozen=True)
class RenameRequest:
    """Request to rename one or more MP3 files."""

    path: Path
    recursive: bool = False
    dry_run: bool = False
    template: Optional[str] = None
    auto_detect: bool = True  # Auto-detect BPM/Key if missing
    progress_callback: Optional[Callable[[int, str], None]] = None  # Called after each file: (count, filename)


@dataclass(frozen=True)
class RenameResult:
    """Result of a single file rename operation."""

    src: Path
    dst: Optional[Path]
    status: str  # "renamed" | "skipped" | "error"
    message: Optional[str] = None
    metadata: Optional[dict[str, str]] = None  # MP3 metadata (artist, title, bpm, key, etc.)


@dataclass(frozen=True)
class RenameStatus:
    """Overall status of a batch rename operation."""

    total: int
    renamed: int
    skipped: int
    errors: int
    results: list[RenameResult]


@dataclass(frozen=True)
class OperationStatus:
    """
    Status of an asynchronous operation.

    Used for polling operation progress in web UI.
    Enables non-blocking operations with real-time status updates.
    """

    operation_id: str
    status: str  # "running" | "completed" | "cancelled" | "error"
    progress: int  # Files processed so far
    total: int  # Total files to process
    current_file: str  # Currently processing file
    start_time: float  # Unix timestamp
    end_time: Optional[float] = None  # Unix timestamp when finished
    results: Optional[RenameStatus] = None  # Final results (when completed)
    error: Optional[str] = None  # Error message (when error)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for web API."""
        return {
            "operation_id": self.operation_id,
            "status": self.status,
            "progress": self.progress,
            "total": self.total,
            "current_file": self.current_file,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "results": {
                "total": self.results.total,
                "renamed": self.results.renamed,
                "skipped": self.results.skipped,
                "errors": self.results.errors,
            } if self.results else None,
            "error": self.error,
        }
