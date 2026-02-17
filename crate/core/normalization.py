"""
Core normalization logic - Volume leveling using LUFS measurement.

Implements EBU R128 loudness measurement and ReplayGain-style normalization.

Dependencies:
- pyloudnorm (preferred) or soundfile + numpy (fallback)
- mutagen (for ReplayGain tag writing)
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

# Try to import pyloudnorm (preferred LUFS measurement)
try:
    import pyloudnorm as pyln
    PYLOUDNORM_AVAILABLE = True
except ImportError:
    PYLOUDNORM_AVAILABLE = False

# Try to import soundfile for audio loading
try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

# Fallback to librosa if soundfile unavailable
try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

# mutagen for tag writing
try:
    from mutagen.id3 import ID3, TXXX
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False


# Supported audio extensions
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aiff", ".aif", ".ogg"}


def collect_audio_files(paths: List[Path], recursive: bool = False) -> List[Path]:
    """Collect all audio files from paths.

    Args:
        paths: List of files or directories
        recursive: Whether to recurse into subdirectories

    Returns:
        List of audio file paths
    """
    files = []

    for path in paths:
        if path.is_file():
            if path.suffix.lower() in AUDIO_EXTENSIONS:
                files.append(path)
        elif path.is_dir():
            if recursive:
                for ext in AUDIO_EXTENSIONS:
                    files.extend(path.rglob(f"*{ext}"))
            else:
                for ext in AUDIO_EXTENSIONS:
                    files.extend(path.glob(f"*{ext}"))

    return sorted(set(files))


def analyze_loudness(
    file_path: Path,
    logger: logging.Logger
) -> Tuple[Optional[float], Optional[float]]:
    """Analyze file loudness using LUFS measurement.

    Args:
        file_path: Path to audio file
        logger: Logger instance

    Returns:
        Tuple of (integrated_lufs, peak_db) or (None, None) on failure
    """
    if PYLOUDNORM_AVAILABLE and SOUNDFILE_AVAILABLE:
        return _analyze_loudness_pyloudnorm(file_path, logger)
    elif LIBROSA_AVAILABLE:
        return _analyze_loudness_librosa(file_path, logger)
    else:
        logger.error("No loudness analysis library available. Install pyloudnorm or librosa.")
        return None, None


def _analyze_loudness_pyloudnorm(
    file_path: Path,
    logger: logging.Logger
) -> Tuple[Optional[float], Optional[float]]:
    """Analyze loudness using pyloudnorm (preferred method).

    Args:
        file_path: Path to audio file
        logger: Logger instance

    Returns:
        Tuple of (integrated_lufs, peak_db)
    """
    try:
        # Load audio
        data, rate = sf.read(str(file_path))

        # Handle mono/stereo
        if len(data.shape) == 1:
            data = data.reshape(-1, 1)

        # Create meter (EBU R128)
        meter = pyln.Meter(rate)

        # Measure integrated loudness
        loudness = meter.integrated_loudness(data)

        # Measure peak (true peak would be better but this is simpler)
        peak_linear = np.max(np.abs(data))
        peak_db = 20 * np.log10(peak_linear) if peak_linear > 0 else -70.0

        logger.debug(f"Analyzed {file_path.name}: {loudness:.1f} LUFS, {peak_db:.1f} dB peak")

        return loudness, peak_db

    except Exception as e:
        logger.error(f"Failed to analyze {file_path}: {e}")
        return None, None


def _analyze_loudness_librosa(
    file_path: Path,
    logger: logging.Logger
) -> Tuple[Optional[float], Optional[float]]:
    """Analyze loudness using librosa (fallback method).

    Note: This is an approximation. librosa doesn't implement true LUFS,
    so we use RMS as a proxy with a rough conversion.

    Args:
        file_path: Path to audio file
        logger: Logger instance

    Returns:
        Tuple of (estimated_lufs, peak_db)
    """
    try:
        # Load audio
        y, sr = librosa.load(str(file_path), sr=None, mono=False)

        # Handle mono
        if len(y.shape) == 1:
            y = y.reshape(1, -1)

        # Mix to mono for RMS calculation
        y_mono = np.mean(y, axis=0)

        # Calculate RMS
        rms = np.sqrt(np.mean(y_mono ** 2))

        # Convert RMS to dB
        rms_db = 20 * np.log10(rms) if rms > 0 else -70.0

        # Rough conversion from RMS dB to LUFS
        # LUFS is typically ~3dB lower than RMS dB for music
        estimated_lufs = rms_db - 3.0

        # Peak measurement
        peak_linear = np.max(np.abs(y))
        peak_db = 20 * np.log10(peak_linear) if peak_linear > 0 else -70.0

        logger.debug(f"Analyzed {file_path.name}: ~{estimated_lufs:.1f} LUFS (estimated), {peak_db:.1f} dB peak")

        return estimated_lufs, peak_db

    except Exception as e:
        logger.error(f"Failed to analyze {file_path}: {e}")
        return None, None


def calculate_adjustment(
    current_lufs: float,
    target_lufs: float,
    peak_db: float,
    prevent_clipping: bool = True
) -> Tuple[float, bool]:
    """Calculate gain adjustment needed to reach target loudness.

    Args:
        current_lufs: Current integrated loudness (LUFS)
        target_lufs: Target loudness (LUFS)
        peak_db: Current peak level (dB)
        prevent_clipping: Whether to limit gain to prevent clipping

    Returns:
        Tuple of (adjustment_db, clipping_prevented)
    """
    # Basic adjustment
    adjustment = target_lufs - current_lufs
    clipping_prevented = False

    if prevent_clipping and adjustment > 0:
        # Calculate headroom
        headroom = 0.0 - peak_db  # How much room before 0 dB

        if adjustment > headroom:
            # Would clip - limit adjustment
            adjustment = headroom
            clipping_prevented = True

    return adjustment, clipping_prevented


def write_replaygain_tags(
    file_path: Path,
    adjustment_db: float,
    logger: logging.Logger
) -> bool:
    """Write ReplayGain tags to MP3 file.

    Args:
        file_path: Path to MP3 file
        adjustment_db: Gain adjustment in dB
        logger: Logger instance

    Returns:
        True if successful
    """
    if not MUTAGEN_AVAILABLE:
        logger.error("mutagen not available for tag writing")
        return False

    try:
        # Load or create ID3 tags
        try:
            audio = ID3(str(file_path))
        except Exception:
            audio = ID3()

        # ReplayGain track gain
        gain_str = f"{adjustment_db:+.2f} dB"
        audio.add(TXXX(encoding=3, desc="REPLAYGAIN_TRACK_GAIN", text=gain_str))

        # Save
        audio.save(str(file_path))

        logger.info(f"Wrote ReplayGain tag to {file_path.name}: {gain_str}")
        return True

    except Exception as e:
        logger.error(f"Failed to write tags to {file_path}: {e}")
        return False


def apply_gain(
    file_path: Path,
    adjustment_db: float,
    logger: logging.Logger
) -> bool:
    """Apply gain adjustment to audio file (destructive).

    Warning: This modifies the audio data!

    Args:
        file_path: Path to audio file
        adjustment_db: Gain adjustment in dB
        logger: Logger instance

    Returns:
        True if successful
    """
    if not SOUNDFILE_AVAILABLE:
        logger.error("soundfile not available for audio modification")
        return False

    try:
        # Load audio
        data, rate = sf.read(str(file_path))

        # Convert dB to linear gain
        gain_linear = 10 ** (adjustment_db / 20)

        # Apply gain
        data_adjusted = data * gain_linear

        # Clip to prevent overflow (should not happen if prevent_clipping was used)
        data_adjusted = np.clip(data_adjusted, -1.0, 1.0)

        # Write back
        # Note: For MP3, this would require re-encoding which loses quality
        # Better to use ReplayGain tags for MP3
        if file_path.suffix.lower() == ".mp3":
            logger.warning("Applying gain to MP3 requires re-encoding. Consider using TAG mode instead.")

        sf.write(str(file_path), data_adjusted, rate)

        logger.info(f"Applied {adjustment_db:+.2f} dB gain to {file_path.name}")
        return True

    except Exception as e:
        logger.error(f"Failed to apply gain to {file_path}: {e}")
        return False
