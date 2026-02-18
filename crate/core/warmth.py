"""Analog warmth/saturation for audio files.

Adds subtle harmonic saturation similar to analog gear using
a tube-style soft clipping algorithm. Creates "vinyl warmth"
without harsh distortion.

Platinum Notes approach: iZotope Exciter-style harmonic enhancement.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import logging

import numpy as np
import soundfile as sf
from scipy import signal

logger = logging.getLogger(__name__)

# Constants
DEFAULT_DRIVE = 0.15        # Subtle warmth (0.0 to 1.0)
DEFAULT_MIX = 0.3           # Wet/dry mix (0.0 to 1.0)
DEFAULT_TONE = 0.5          # Tonal balance (0.0=dark, 1.0=bright)
DEFAULT_ENABLED = False     # Off by default


@dataclass
class WarmthAnalysisResult:
    """Result of warmth analysis for a single file."""
    path: Path
    success: bool
    peak_level_db: Optional[float] = None
    dynamic_range_db: Optional[float] = None
    recommended_drive: Optional[float] = None
    error: Optional[str] = None


@dataclass
class WarmthResult:
    """Result of warmth processing for a single file."""
    path: Path
    success: bool
    drive_applied: float = 0.0
    mix_applied: float = 0.0
    harmonics_added: bool = False
    error: Optional[str] = None


def soft_clip_tanh(x: np.ndarray, drive: float) -> np.ndarray:
    """Apply tanh soft clipping for tube-like saturation.
    
    The tanh function naturally compresses peaks while adding
    odd harmonics, similar to tube amplifier saturation.
    
    Args:
        x: Input samples
        drive: Drive amount (0.0 to 1.0, higher = more saturation)
        
    Returns:
        Saturated samples
    """
    # Scale drive to useful range (1.0 to 5.0)
    gain = 1.0 + (drive * 4.0)
    
    # Apply gain then soft clip
    saturated = np.tanh(x * gain)
    
    # Normalize output level to match input peak
    input_peak = np.max(np.abs(x))
    output_peak = np.max(np.abs(saturated))
    
    if output_peak > 0:
        saturated = saturated * (input_peak / output_peak)
    
    return saturated


def apply_exciter(
    audio: np.ndarray,
    sample_rate: int,
    drive: float = DEFAULT_DRIVE,
    mix: float = DEFAULT_MIX,
    tone: float = DEFAULT_TONE,
) -> np.ndarray:
    """Apply harmonic exciter/warmth effect.
    
    Combines subtle saturation with high-frequency enhancement
    to create presence and warmth similar to analog gear.
    
    Args:
        audio: Input audio samples
        sample_rate: Sample rate in Hz
        drive: Saturation amount (0.0 to 1.0)
        mix: Wet/dry mix (0.0 to 1.0)
        tone: Tonal balance (0.0=dark, 1.0=bright)
        
    Returns:
        Processed audio
    """
    # Store original for mixing
    dry = audio.copy()
    
    # High-pass filter to isolate harmonics-generating frequencies
    # This prevents bass from getting muddy with saturation
    nyquist = sample_rate / 2
    hp_cutoff = min(200 / nyquist, 0.9)  # 200 Hz high-pass for saturation path
    
    try:
        b_hp, a_hp = signal.butter(2, hp_cutoff, btype='high')
        
        # Process each channel if stereo
        if audio.ndim == 1:
            channels = [audio]
        else:
            channels = [audio[:, i] for i in range(audio.shape[1])]
        
        processed_channels = []
        
        for channel in channels:
            # Split into low (clean) and high (saturate) bands
            low_band = channel - signal.filtfilt(b_hp, a_hp, channel)
            high_band = signal.filtfilt(b_hp, a_hp, channel)
            
            # Apply saturation to high band only
            saturated_high = soft_clip_tanh(high_band, drive)
            
            # Apply tone control (low-pass filter on saturated signal)
            # Higher tone = more high frequency content preserved
            tone_cutoff = min((2000 + tone * 8000) / nyquist, 0.95)
            b_lp, a_lp = signal.butter(2, tone_cutoff, btype='low')
            
            # Blend based on tone setting
            if tone < 0.5:
                # Darker tone: more filtering
                saturated_high = signal.filtfilt(b_lp, a_lp, saturated_high)
            
            # Recombine bands
            wet = low_band + saturated_high
            
            # Mix wet/dry
            processed = (dry if audio.ndim == 1 else channel) * (1 - mix) + wet * mix
            processed_channels.append(processed)
        
        # Reconstruct stereo if needed
        if audio.ndim == 1:
            result = processed_channels[0]
        else:
            result = np.column_stack(processed_channels)
        
        return result.astype(audio.dtype)
        
    except Exception as e:
        logger.warning(f"Exciter processing failed: {e}, returning original")
        return audio


def analyze_for_warmth(
    file_path: Path,
) -> WarmthAnalysisResult:
    """Analyze an audio file to recommend warmth settings.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        WarmthAnalysisResult with recommendations
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return WarmthAnalysisResult(
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
        
        # Calculate peak level
        peak = np.max(np.abs(mono))
        peak_db = 20 * np.log10(peak) if peak > 0 else -np.inf
        
        # Calculate dynamic range (difference between peak and RMS)
        rms = np.sqrt(np.mean(mono ** 2))
        rms_db = 20 * np.log10(rms) if rms > 0 else -np.inf
        dynamic_range = peak_db - rms_db
        
        # Recommend drive based on dynamic range
        # Less dynamic = needs less warmth (already compressed)
        # More dynamic = can handle more warmth
        if dynamic_range < 6:
            recommended = 0.1  # Already compressed, go easy
        elif dynamic_range < 12:
            recommended = 0.15  # Normal
        else:
            recommended = 0.2  # Dynamic, can handle more
        
        return WarmthAnalysisResult(
            path=file_path,
            success=True,
            peak_level_db=float(peak_db),
            dynamic_range_db=float(dynamic_range),
            recommended_drive=recommended,
        )
        
    except Exception as e:
        logger.exception(f"Error analyzing for warmth: {file_path}")
        return WarmthAnalysisResult(
            path=file_path,
            success=False,
            error=str(e)
        )


def apply_warmth(
    input_path: Path,
    output_path: Optional[Path] = None,
    drive: float = DEFAULT_DRIVE,
    mix: float = DEFAULT_MIX,
    tone: float = DEFAULT_TONE,
    dry_run: bool = False,
) -> WarmthResult:
    """Apply warmth/saturation to an audio file.
    
    Args:
        input_path: Path to input audio file
        output_path: Path to output file (None = overwrite input)
        drive: Saturation amount (0.0 to 1.0)
        mix: Wet/dry mix (0.0 to 1.0)
        tone: Tonal balance (0.0=dark, 1.0=bright)
        dry_run: If True, analyze only without writing
        
    Returns:
        WarmthResult with details
    """
    input_path = Path(input_path)
    
    if not input_path.exists():
        return WarmthResult(
            path=input_path,
            success=False,
            error=f"File not found: {input_path}"
        )
    
    # Validate parameters
    drive = max(0.0, min(1.0, drive))
    mix = max(0.0, min(1.0, mix))
    tone = max(0.0, min(1.0, tone))
    
    if dry_run:
        return WarmthResult(
            path=input_path,
            success=True,
            drive_applied=drive,
            mix_applied=mix,
            harmonics_added=True,
        )
    
    try:
        # Load audio
        audio, sample_rate = sf.read(input_path)
        
        # Apply warmth
        processed = apply_exciter(audio, sample_rate, drive, mix, tone)
        
        # Write output
        out_path = output_path or input_path
        sf.write(out_path, processed, sample_rate)
        
        return WarmthResult(
            path=input_path,
            success=True,
            drive_applied=drive,
            mix_applied=mix,
            harmonics_added=True,
        )
        
    except Exception as e:
        logger.exception(f"Error applying warmth to {input_path}")
        return WarmthResult(
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
