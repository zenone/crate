"""Clipped peak repair for audio files.

Detects digitally clipped audio (flat-topped waveforms) and repairs
them using cubic interpolation to reconstruct natural peak shapes.

Platinum Notes approach: multiband processing + peak interpolation.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import logging

import numpy as np
import soundfile as sf
from scipy import signal
from scipy.interpolate import CubicSpline

logger = logging.getLogger(__name__)

# Constants
DEFAULT_CLIP_THRESHOLD = 0.99  # Samples above this are considered clipped
DEFAULT_MIN_CLIP_SAMPLES = 3   # Minimum consecutive samples to detect as clipping
DEFAULT_ENABLED = False        # Off by default (like Platinum Notes)


@dataclass
class ClipAnalysisResult:
    """Result of clipping analysis for a single file."""
    path: Path
    success: bool
    clip_count: int = 0
    total_clipped_samples: int = 0
    clip_percentage: float = 0.0
    max_clip_length: int = 0
    needs_repair: bool = False
    error: Optional[str] = None


@dataclass
class ClipRepairResult:
    """Result of clip repair for a single file."""
    path: Path
    success: bool
    clips_repaired: int = 0
    samples_repaired: int = 0
    original_clip_percentage: float = 0.0
    error: Optional[str] = None


def detect_clipping_regions(
    audio: np.ndarray,
    threshold: float = DEFAULT_CLIP_THRESHOLD,
    min_samples: int = DEFAULT_MIN_CLIP_SAMPLES,
) -> list[Tuple[int, int, int]]:
    """Detect clipped regions in audio.
    
    Finds consecutive samples at or above the threshold (flat-topped peaks).
    
    Args:
        audio: Audio samples (1D array, mono)
        threshold: Amplitude threshold for clipping detection
        min_samples: Minimum consecutive samples to count as clipping
        
    Returns:
        List of (start_idx, end_idx, polarity) tuples where polarity is +1 or -1
    """
    # Find samples at or above threshold (positive) or at or below -threshold (negative)
    clipped_positive = audio >= threshold
    clipped_negative = audio <= -threshold
    
    regions = []
    
    for clipped, polarity in [(clipped_positive, 1), (clipped_negative, -1)]:
        # Find runs of clipped samples
        changes = np.diff(clipped.astype(int))
        starts = np.where(changes == 1)[0] + 1
        ends = np.where(changes == -1)[0] + 1
        
        # Handle edge cases
        if clipped[0]:
            starts = np.concatenate([[0], starts])
        if clipped[-1]:
            ends = np.concatenate([ends, [len(audio)]])
        
        # Filter by minimum length
        for start, end in zip(starts, ends):
            length = end - start
            if length >= min_samples:
                regions.append((int(start), int(end), polarity))
    
    # Sort by start index
    return sorted(regions, key=lambda x: x[0])


def repair_clip_region(
    audio: np.ndarray,
    start: int,
    end: int,
    polarity: int,
    context_samples: int = 8,
) -> np.ndarray:
    """Repair a single clipped region using cubic spline interpolation.
    
    Uses samples before and after the clipped region to reconstruct
    a natural peak shape via cubic spline interpolation.
    
    Args:
        audio: Full audio array (will be modified in place)
        start: Start index of clipped region
        end: End index of clipped region (exclusive)
        polarity: +1 for positive clips, -1 for negative clips
        context_samples: Number of samples before/after to use for interpolation
        
    Returns:
        Modified audio array
    """
    clip_length = end - start
    
    # Get context samples before and after clip
    ctx_start = max(0, start - context_samples)
    ctx_end = min(len(audio), end + context_samples)
    
    # Build interpolation points from non-clipped context
    x_before = np.arange(ctx_start, start)
    x_after = np.arange(end, ctx_end)
    
    if len(x_before) < 2 or len(x_after) < 2:
        # Not enough context for interpolation
        return audio
    
    y_before = audio[x_before]
    y_after = audio[x_after]
    
    # Combine context points
    x_known = np.concatenate([x_before, x_after])
    y_known = np.concatenate([y_before, y_after])
    
    # Create cubic spline through known points
    try:
        spline = CubicSpline(x_known, y_known)
        
        # Interpolate the clipped region
        x_clip = np.arange(start, end)
        y_repaired = spline(x_clip)
        
        # Apply the repair
        audio[start:end] = y_repaired
        
    except Exception as e:
        logger.debug(f"Spline interpolation failed for region {start}-{end}: {e}")
    
    return audio


def repair_clipping(
    audio: np.ndarray,
    sample_rate: int,
    threshold: float = DEFAULT_CLIP_THRESHOLD,
    min_samples: int = DEFAULT_MIN_CLIP_SAMPLES,
) -> Tuple[np.ndarray, int, int]:
    """Repair all clipped regions in audio.
    
    Args:
        audio: Audio samples (samples x channels or 1D)
        sample_rate: Sample rate in Hz
        threshold: Amplitude threshold for clipping detection
        min_samples: Minimum consecutive samples to count as clipping
        
    Returns:
        Tuple of (repaired_audio, clips_repaired, samples_repaired)
    """
    # Handle stereo by processing each channel
    if audio.ndim == 1:
        channels = [audio.copy()]
    else:
        channels = [audio[:, i].copy() for i in range(audio.shape[1])]
    
    total_clips = 0
    total_samples = 0
    
    for ch_idx, channel in enumerate(channels):
        regions = detect_clipping_regions(channel, threshold, min_samples)
        
        for start, end, polarity in regions:
            repair_clip_region(channel, start, end, polarity)
            total_clips += 1
            total_samples += end - start
    
    # Reconstruct output
    if audio.ndim == 1:
        repaired = channels[0]
    else:
        repaired = np.column_stack(channels)
    
    return repaired.astype(audio.dtype), total_clips, total_samples


def analyze_clipping(
    file_path: Path,
    threshold: float = DEFAULT_CLIP_THRESHOLD,
    min_samples: int = DEFAULT_MIN_CLIP_SAMPLES,
) -> ClipAnalysisResult:
    """Analyze an audio file for clipping.
    
    Args:
        file_path: Path to audio file
        threshold: Amplitude threshold for clipping detection
        min_samples: Minimum consecutive samples to count as clipping
        
    Returns:
        ClipAnalysisResult with analysis details
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return ClipAnalysisResult(
            path=file_path,
            success=False,
            error=f"File not found: {file_path}"
        )
    
    try:
        # Load audio
        audio, sample_rate = sf.read(file_path)
        
        # Convert to mono for analysis
        if audio.ndim > 1:
            mono = np.mean(audio, axis=1)
        else:
            mono = audio
        
        # Detect clipping
        regions = detect_clipping_regions(mono, threshold, min_samples)
        
        clip_count = len(regions)
        total_clipped = sum(end - start for start, end, _ in regions)
        max_length = max((end - start for start, end, _ in regions), default=0)
        clip_percentage = (total_clipped / len(mono)) * 100 if len(mono) > 0 else 0
        
        return ClipAnalysisResult(
            path=file_path,
            success=True,
            clip_count=clip_count,
            total_clipped_samples=total_clipped,
            clip_percentage=clip_percentage,
            max_clip_length=max_length,
            needs_repair=clip_count > 0,
        )
        
    except Exception as e:
        logger.exception(f"Error analyzing clipping for {file_path}")
        return ClipAnalysisResult(
            path=file_path,
            success=False,
            error=str(e)
        )


def repair_file(
    input_path: Path,
    output_path: Optional[Path] = None,
    threshold: float = DEFAULT_CLIP_THRESHOLD,
    min_samples: int = DEFAULT_MIN_CLIP_SAMPLES,
    dry_run: bool = False,
) -> ClipRepairResult:
    """Repair clipping in an audio file.
    
    Args:
        input_path: Path to input audio file
        output_path: Path to output file (None = overwrite input)
        threshold: Amplitude threshold for clipping detection
        min_samples: Minimum consecutive samples to count as clipping
        dry_run: If True, analyze only without writing
        
    Returns:
        ClipRepairResult with details
    """
    input_path = Path(input_path)
    
    # First analyze
    analysis = analyze_clipping(input_path, threshold, min_samples)
    
    if not analysis.success:
        return ClipRepairResult(
            path=input_path,
            success=False,
            error=analysis.error
        )
    
    if not analysis.needs_repair:
        # No clipping detected
        return ClipRepairResult(
            path=input_path,
            success=True,
            clips_repaired=0,
            samples_repaired=0,
            original_clip_percentage=0.0,
        )
    
    if dry_run:
        return ClipRepairResult(
            path=input_path,
            success=True,
            clips_repaired=analysis.clip_count,
            samples_repaired=analysis.total_clipped_samples,
            original_clip_percentage=analysis.clip_percentage,
        )
    
    try:
        # Load audio
        audio, sample_rate = sf.read(input_path)
        
        # Repair clipping
        repaired, clips_fixed, samples_fixed = repair_clipping(
            audio, sample_rate, threshold, min_samples
        )
        
        # Write output
        out_path = output_path or input_path
        sf.write(out_path, repaired, sample_rate)
        
        return ClipRepairResult(
            path=input_path,
            success=True,
            clips_repaired=clips_fixed,
            samples_repaired=samples_fixed,
            original_clip_percentage=analysis.clip_percentage,
        )
        
    except Exception as e:
        logger.exception(f"Error repairing clipping for {input_path}")
        return ClipRepairResult(
            path=input_path,
            success=False,
            error=str(e)
        )


def collect_audio_files(path: Path, recursive: bool = True) -> list[Path]:
    """Collect audio files from a path.
    
    Args:
        path: File or directory path
        recursive: If True, search subdirectories
        
    Returns:
        List of audio file paths
    """
    extensions = {'.mp3', '.wav', '.flac', '.aiff', '.aif', '.m4a', '.ogg'}
    
    path = Path(path)
    
    if path.is_file():
        if path.suffix.lower() in extensions:
            return [path]
        return []
    
    if path.is_dir():
        if recursive:
            files = path.rglob('*')
        else:
            files = path.glob('*')
        
        return sorted([f for f in files if f.suffix.lower() in extensions])
    
    return []
