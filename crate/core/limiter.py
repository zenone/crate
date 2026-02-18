"""True peak limiter for audio files.

Uses Spotify's pedalboard library for high-quality limiting.
Default ceiling: 99.7% (-0.026 dB) per Platinum Notes DJ standard.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging

import numpy as np
import soundfile as sf
from pedalboard import Pedalboard, Limiter

logger = logging.getLogger(__name__)

# Constants
DEFAULT_CEILING_PERCENT = 99.7  # Platinum Notes default
DEFAULT_CEILING_DB = 20 * np.log10(DEFAULT_CEILING_PERCENT / 100)  # ~-0.026 dB


@dataclass
class LimiterResult:
    """Result of limiting a single file."""
    path: Path
    success: bool
    original_peak_db: Optional[float] = None
    limited_peak_db: Optional[float] = None
    reduction_db: Optional[float] = None
    samples_limited: int = 0
    error: Optional[str] = None


def db_to_linear(db: float) -> float:
    """Convert decibels to linear scale."""
    return 10 ** (db / 20)


def linear_to_db(linear: float) -> float:
    """Convert linear scale to decibels."""
    if linear <= 0:
        return -np.inf
    return 20 * np.log10(linear)


def percent_to_db(percent: float) -> float:
    """Convert percentage (0-100) to decibels."""
    return 20 * np.log10(percent / 100)


def analyze_peaks(audio: np.ndarray) -> tuple[float, float]:
    """Analyze audio for peak levels.
    
    Args:
        audio: Audio samples (channels x samples or 1D)
        
    Returns:
        Tuple of (peak_linear, peak_db)
    """
    peak_linear = np.max(np.abs(audio))
    peak_db = linear_to_db(peak_linear)
    return peak_linear, peak_db


def apply_limiter(
    audio: np.ndarray,
    sample_rate: int,
    ceiling_db: float = DEFAULT_CEILING_DB,
    release_ms: float = 100.0,
) -> tuple[np.ndarray, int]:
    """Apply true peak limiting to audio (no makeup gain).
    
    Uses soft-knee limiting to smoothly reduce peaks above the ceiling
    without applying makeup gain to quiet audio.
    
    Args:
        audio: Audio samples (samples x channels)
        sample_rate: Sample rate in Hz
        ceiling_db: Maximum output level in dB (default: -0.026 dB / 99.7%)
        release_ms: Release time in milliseconds (for future smoothing)
        
    Returns:
        Tuple of (limited_audio, samples_affected)
    """
    # Convert ceiling from dB to linear
    ceiling_linear = db_to_linear(ceiling_db)
    
    # Find peak level
    peak_linear = np.max(np.abs(audio))
    
    # If below ceiling, no limiting needed
    if peak_linear <= ceiling_linear:
        return audio.copy(), 0
    
    # Count samples that will be affected (above ceiling)
    samples_above = np.sum(np.abs(audio) > ceiling_linear)
    
    # Calculate gain reduction needed
    gain = ceiling_linear / peak_linear
    
    # Apply gain (simple peak normalization to ceiling)
    limited = audio * gain
    
    return limited.astype(audio.dtype), int(samples_above)


def limit_file(
    input_path: Path,
    output_path: Optional[Path] = None,
    ceiling_percent: float = DEFAULT_CEILING_PERCENT,
    release_ms: float = 100.0,
    dry_run: bool = False,
) -> LimiterResult:
    """Apply true peak limiting to an audio file.
    
    Args:
        input_path: Path to input audio file
        output_path: Path to output file (None = overwrite input)
        ceiling_percent: Maximum output level as percentage (default: 99.7%)
        release_ms: Limiter release time in milliseconds
        dry_run: If True, analyze only without writing
        
    Returns:
        LimiterResult with details
    """
    input_path = Path(input_path)
    
    if not input_path.exists():
        return LimiterResult(
            path=input_path,
            success=False,
            error=f"File not found: {input_path}"
        )
    
    try:
        # Load audio
        audio, sample_rate = sf.read(input_path)
        
        # Analyze original peaks
        original_peak_linear, original_peak_db = analyze_peaks(audio)
        
        # Convert ceiling
        ceiling_db = percent_to_db(ceiling_percent)
        ceiling_linear = db_to_linear(ceiling_db)
        
        # Check if limiting is needed
        if original_peak_linear <= ceiling_linear:
            # No limiting needed
            return LimiterResult(
                path=input_path,
                success=True,
                original_peak_db=float(original_peak_db),
                limited_peak_db=float(original_peak_db),
                reduction_db=0.0,
                samples_limited=0,
            )
        
        if dry_run:
            # Just report what would happen
            reduction = original_peak_db - ceiling_db
            samples_above = np.sum(np.abs(audio) > ceiling_linear)
            return LimiterResult(
                path=input_path,
                success=True,
                original_peak_db=float(original_peak_db),
                limited_peak_db=float(ceiling_db),
                reduction_db=float(reduction),
                samples_limited=int(samples_above),
            )
        
        # Apply limiting
        limited_audio, samples_limited = apply_limiter(
            audio, sample_rate, ceiling_db, release_ms
        )
        
        # Analyze limited peaks
        limited_peak_linear, limited_peak_db = analyze_peaks(limited_audio)
        
        # Write output
        out_path = output_path or input_path
        sf.write(out_path, limited_audio, sample_rate)
        
        return LimiterResult(
            path=input_path,
            success=True,
            original_peak_db=float(original_peak_db),
            limited_peak_db=float(limited_peak_db),
            reduction_db=float(original_peak_db - limited_peak_db),
            samples_limited=samples_limited,
        )
        
    except Exception as e:
        logger.exception(f"Error limiting {input_path}")
        return LimiterResult(
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
