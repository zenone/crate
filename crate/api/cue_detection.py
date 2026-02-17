"""
Cue Detection API - Auto-detect hot cue points for DJ software.

Provides basic cue point detection based on audio analysis:
- First beat (intro marker)
- Energy peaks (drop markers)
- Energy dips (breakdown markers)

API Contract:
- CueDetectionRequest: What to analyze
- CuePoint: A detected cue point
- CueDetectionResult: All cues for a file
- CueDetectionAPI: Orchestration layer
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class CueType(Enum):
    """Type of cue point."""
    INTRO = "intro"           # First beat / track start
    DROP = "drop"             # Energy peak / main section
    BREAKDOWN = "breakdown"   # Energy dip / quiet section
    BUILD = "build"           # Rising energy before drop
    OUTRO = "outro"           # Track ending section
    MEMORY = "memory"         # General marker (Rekordbox memory cue)


class ExportFormat(Enum):
    """Export format for cue points."""
    REKORDBOX = "rekordbox"   # Rekordbox XML
    JSON = "json"             # Generic JSON


@dataclass
class CuePoint:
    """A detected cue point.

    Attributes:
        position_ms: Position in milliseconds from track start
        cue_type: Type of cue (intro, drop, breakdown, etc.)
        confidence: Detection confidence (0.0-1.0)
        label: Human-readable label
        color: Suggested color (Rekordbox format: 0xRRGGBB)
        hot_cue_index: Suggested hot cue slot (0-7 for most DJ software)
    """
    position_ms: int
    cue_type: CueType
    confidence: float = 1.0
    label: Optional[str] = None
    color: Optional[int] = None  # 0xRRGGBB
    hot_cue_index: Optional[int] = None


@dataclass
class CueDetectionRequest:
    """Request to detect cue points.

    Attributes:
        paths: Files or directories to process
        detect_intro: Detect intro/first beat
        detect_drops: Detect energy peaks (drops)
        detect_breakdowns: Detect energy dips (breakdowns)
        max_cues: Maximum cue points per track (default 8)
        sensitivity: Detection sensitivity (0.0-1.0, higher = more cues)
        recursive: Process subdirectories
    """
    paths: List[Path]
    detect_intro: bool = True
    detect_drops: bool = True
    detect_breakdowns: bool = True
    max_cues: int = 8
    sensitivity: float = 0.5
    recursive: bool = False


@dataclass
class CueDetectionResult:
    """Result of cue detection for a single file.

    Attributes:
        path: File that was processed
        success: Whether detection succeeded
        cues: Detected cue points
        duration_ms: Track duration in milliseconds
        bpm: Detected BPM (if available)
        error: Error message if failed
    """
    path: Path
    success: bool
    cues: List[CuePoint] = field(default_factory=list)
    duration_ms: Optional[int] = None
    bpm: Optional[float] = None
    error: Optional[str] = None


@dataclass
class CueDetectionStatus:
    """Status of a cue detection batch operation.

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
    results: List[CueDetectionResult] = field(default_factory=list)


# Rekordbox color palette (common DJ colors)
REKORDBOX_COLORS = {
    CueType.INTRO: 0x28E214,      # Green
    CueType.DROP: 0xE81414,       # Red
    CueType.BREAKDOWN: 0x14AAE8,  # Blue
    CueType.BUILD: 0xE8D414,      # Yellow
    CueType.OUTRO: 0xAA14E8,      # Purple
    CueType.MEMORY: 0xE88214,     # Orange
}


class CueDetectionAPI:
    """API for cue point detection operations.

    Example:
        >>> api = CueDetectionAPI()
        >>> request = CueDetectionRequest(paths=[Path("track.mp3")])
        >>> status = api.detect(request)
        >>> for cue in status.results[0].cues:
        ...     print(f"{cue.cue_type.value}: {cue.position_ms}ms")
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the cue detection API.

        Args:
            logger: Logger instance (creates default if not provided)
        """
        self.logger = logger or logging.getLogger(__name__)

    def detect(self, request: CueDetectionRequest) -> CueDetectionStatus:
        """Detect cue points in files.

        Args:
            request: CueDetectionRequest with paths and options

        Returns:
            CueDetectionStatus with results for each file
        """
        from ..core.cue_detection import collect_audio_files

        status = CueDetectionStatus()

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
        request: CueDetectionRequest
    ) -> CueDetectionResult:
        """Process a single file for cue detection.

        Args:
            file_path: Path to audio file
            request: CueDetectionRequest with options

        Returns:
            CueDetectionResult for this file
        """
        from ..core.cue_detection import (
            assign_hot_cue_slots,
            detect_energy_dips,
            detect_energy_peaks,
            detect_first_beat,
            get_audio_duration,
            get_bpm,
        )

        try:
            cues: List[CuePoint] = []

            # Get track metadata
            duration_ms = get_audio_duration(file_path, self.logger)
            bpm = get_bpm(file_path, self.logger)

            # Detect intro (first beat)
            if request.detect_intro:
                intro_cue = detect_first_beat(file_path, self.logger)
                if intro_cue:
                    intro_cue.color = REKORDBOX_COLORS[CueType.INTRO]
                    cues.append(intro_cue)

            # Detect drops (energy peaks)
            if request.detect_drops:
                drops = detect_energy_peaks(
                    file_path,
                    self.logger,
                    sensitivity=request.sensitivity
                )
                for drop in drops:
                    drop.color = REKORDBOX_COLORS[CueType.DROP]
                    cues.append(drop)

            # Detect breakdowns (energy dips)
            if request.detect_breakdowns:
                breakdowns = detect_energy_dips(
                    file_path,
                    self.logger,
                    sensitivity=request.sensitivity
                )
                for bd in breakdowns:
                    bd.color = REKORDBOX_COLORS[CueType.BREAKDOWN]
                    cues.append(bd)

            # Limit to max_cues and assign hot cue slots
            cues = assign_hot_cue_slots(cues, request.max_cues)

            return CueDetectionResult(
                path=file_path,
                success=True,
                cues=cues,
                duration_ms=duration_ms,
                bpm=bpm
            )

        except Exception as e:
            self.logger.error(f"Failed to detect cues in {file_path}: {e}")
            return CueDetectionResult(
                path=file_path,
                success=False,
                error=str(e)
            )

    def export_rekordbox(
        self,
        results: List[CueDetectionResult],
        output_path: Path
    ) -> bool:
        """Export cue points to Rekordbox XML format.

        Args:
            results: List of CueDetectionResult to export
            output_path: Path to write XML file

        Returns:
            True if export succeeded
        """
        from ..core.cue_detection import write_rekordbox_xml

        try:
            write_rekordbox_xml(results, output_path, self.logger)
            return True
        except Exception as e:
            self.logger.error(f"Failed to export Rekordbox XML: {e}")
            return False
