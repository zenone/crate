"""
Data models for the API layer.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class RenameRequest:
    """Request to rename one or more MP3 files."""

    path: Path
    recursive: bool = False
    dry_run: bool = False
    template: Optional[str] = None


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
