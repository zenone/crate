"""Pitch correction for audio files.

Detects pitch deviation and corrects audio to the nearest semitone.
Uses librosa for pitch detection and pyrubberband for pitch shifting.

Default: Off (10 cent threshold when enabled, per Platinum Notes).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple
import logging

import numpy as np
import librosa
import soundfile as sf

logger = logging.getLogger(__name__)

# Constants
DEFAULT_THRESHOLD_CENTS = 10  # Platinum Notes default
CENTS_PER_SEMITONE = 100


@dataclass
class PitchAnalysisResult:
    """Result of pitch analysis for a single file."""
    path: Path
    success: bool
    detected_pitch_hz: Optional[float] = None
    nearest_note: Optional[str] = None
    deviation_cents: Optional[float] = None
    needs_correction: bool = False
    error: Optional[str] = None


@dataclass
class PitchCorrectionResult:
    """Result of pitch correction for a single file."""
    path: Path
    success: bool
    original_pitch_hz: Optional[float] = None
    corrected_pitch_hz: Optional[float] = None
    shift_cents: Optional[float] = None
    nearest_note: Optional[str] = None
    error: Optional[str] = None


# Note names for A440 tuning
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def hz_to_midi(freq_hz: float) -> float:
    """Convert frequency in Hz to MIDI note number."""
    if freq_hz <= 0:
        return 0
    return 69 + 12 * np.log2(freq_hz / 440.0)


def midi_to_hz(midi_note: float) -> float:
    """Convert MIDI note number to frequency in Hz."""
    return 440.0 * (2 ** ((midi_note - 69) / 12))


def midi_to_note_name(midi_note: float) -> str:
    """Convert MIDI note number to note name (e.g., 'A4')."""
    note_num = int(round(midi_note))
    octave = (note_num // 12) - 1
    note_idx = note_num % 12
    return f"{NOTE_NAMES[note_idx]}{octave}"


def calculate_deviation_cents(freq_hz: float) -> Tuple[float, float, str]:
    """Calculate deviation from nearest semitone.
    
    Args:
        freq_hz: Detected frequency in Hz
        
    Returns:
        Tuple of (deviation_cents, nearest_midi, nearest_note_name)
    """
    midi = hz_to_midi(freq_hz)
    nearest_midi = round(midi)
    deviation_cents = (midi - nearest_midi) * CENTS_PER_SEMITONE
    note_name = midi_to_note_name(nearest_midi)
    return deviation_cents, nearest_midi, note_name


def detect_pitch(
    audio: np.ndarray,
    sample_rate: int,
    fmin: float = 80.0,
    fmax: float = 2000.0,
) -> Optional[float]:
    """Detect the predominant pitch of audio.
    
    Uses librosa's piptrack for pitch detection, then finds the
    most common pitch in the signal.
    
    Args:
        audio: Audio samples (mono)
        sample_rate: Sample rate in Hz
        fmin: Minimum frequency to detect
        fmax: Maximum frequency to detect
        
    Returns:
        Predominant pitch in Hz, or None if no pitch detected
    """
    # Ensure mono
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)
    
    # Use pyin for pitch detection (more accurate than piptrack)
    f0, voiced_flag, voiced_probs = librosa.pyin(
        audio,
        fmin=fmin,
        fmax=fmax,
        sr=sample_rate,
        fill_na=0.0,
    )
    
    # Filter to voiced segments with sufficient confidence
    voiced_pitches = f0[voiced_flag & (voiced_probs > 0.5) & (f0 > 0)]
    
    if len(voiced_pitches) == 0:
        return None
    
    # Return median pitch (robust to outliers)
    return float(np.median(voiced_pitches))


def shift_pitch(
    audio: np.ndarray,
    sample_rate: int,
    cents: float,
) -> np.ndarray:
    """Shift audio pitch by a given number of cents.
    
    Uses pyrubberband for high-quality pitch shifting that
    preserves tempo.
    
    Args:
        audio: Audio samples
        sample_rate: Sample rate in Hz
        cents: Pitch shift in cents (positive = up, negative = down)
        
    Returns:
        Pitch-shifted audio
    """
    import pyrubberband as pyrb
    
    # Convert cents to semitones
    semitones = cents / CENTS_PER_SEMITONE
    
    # pyrubberband expects (samples, channels) or 1D
    shifted = pyrb.pitch_shift(audio, sample_rate, semitones)
    
    return shifted


def analyze_pitch(
    file_path: Path,
    threshold_cents: float = DEFAULT_THRESHOLD_CENTS,
) -> PitchAnalysisResult:
    """Analyze pitch of an audio file.
    
    Args:
        file_path: Path to audio file
        threshold_cents: Minimum deviation to flag for correction
        
    Returns:
        PitchAnalysisResult with analysis details
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return PitchAnalysisResult(
            path=file_path,
            success=False,
            error=f"File not found: {file_path}"
        )
    
    try:
        # Load audio
        audio, sample_rate = librosa.load(file_path, sr=None, mono=True)
        
        # Detect pitch
        pitch_hz = detect_pitch(audio, sample_rate)
        
        if pitch_hz is None:
            return PitchAnalysisResult(
                path=file_path,
                success=True,
                detected_pitch_hz=None,
                nearest_note=None,
                deviation_cents=None,
                needs_correction=False,
            )
        
        # Calculate deviation
        deviation_cents, nearest_midi, note_name = calculate_deviation_cents(pitch_hz)
        needs_correction = abs(deviation_cents) >= threshold_cents
        
        return PitchAnalysisResult(
            path=file_path,
            success=True,
            detected_pitch_hz=pitch_hz,
            nearest_note=note_name,
            deviation_cents=deviation_cents,
            needs_correction=needs_correction,
        )
        
    except Exception as e:
        logger.exception(f"Error analyzing pitch for {file_path}")
        return PitchAnalysisResult(
            path=file_path,
            success=False,
            error=str(e)
        )


def correct_pitch(
    input_path: Path,
    output_path: Optional[Path] = None,
    threshold_cents: float = DEFAULT_THRESHOLD_CENTS,
    dry_run: bool = False,
) -> PitchCorrectionResult:
    """Correct pitch of an audio file to nearest semitone.
    
    Args:
        input_path: Path to input audio file
        output_path: Path to output file (None = overwrite input)
        threshold_cents: Minimum deviation to correct
        dry_run: If True, analyze only without writing
        
    Returns:
        PitchCorrectionResult with details
    """
    input_path = Path(input_path)
    
    # First analyze
    analysis = analyze_pitch(input_path, threshold_cents)
    
    if not analysis.success:
        return PitchCorrectionResult(
            path=input_path,
            success=False,
            error=analysis.error
        )
    
    if analysis.detected_pitch_hz is None:
        # No pitch detected, nothing to correct
        return PitchCorrectionResult(
            path=input_path,
            success=True,
            original_pitch_hz=None,
            corrected_pitch_hz=None,
            shift_cents=0,
            nearest_note=None,
        )
    
    if not analysis.needs_correction:
        # Within tolerance, no correction needed
        return PitchCorrectionResult(
            path=input_path,
            success=True,
            original_pitch_hz=analysis.detected_pitch_hz,
            corrected_pitch_hz=analysis.detected_pitch_hz,
            shift_cents=0,
            nearest_note=analysis.nearest_note,
        )
    
    # Calculate shift needed (negate deviation to correct)
    shift_cents = -analysis.deviation_cents
    
    if dry_run:
        # Just report what would happen
        _, nearest_midi, _ = calculate_deviation_cents(analysis.detected_pitch_hz)
        corrected_hz = midi_to_hz(nearest_midi)
        return PitchCorrectionResult(
            path=input_path,
            success=True,
            original_pitch_hz=analysis.detected_pitch_hz,
            corrected_pitch_hz=corrected_hz,
            shift_cents=shift_cents,
            nearest_note=analysis.nearest_note,
        )
    
    try:
        # Load audio at original sample rate
        audio, sample_rate = sf.read(input_path)
        
        # Shift pitch
        corrected = shift_pitch(audio, sample_rate, shift_cents)
        
        # Write output
        out_path = output_path or input_path
        sf.write(out_path, corrected, sample_rate)
        
        # Calculate corrected pitch
        _, nearest_midi, _ = calculate_deviation_cents(analysis.detected_pitch_hz)
        corrected_hz = midi_to_hz(nearest_midi)
        
        return PitchCorrectionResult(
            path=input_path,
            success=True,
            original_pitch_hz=analysis.detected_pitch_hz,
            corrected_pitch_hz=corrected_hz,
            shift_cents=shift_cents,
            nearest_note=analysis.nearest_note,
        )
        
    except Exception as e:
        logger.exception(f"Error correcting pitch for {input_path}")
        return PitchCorrectionResult(
            path=input_path,
            success=False,
            error=str(e)
        )


def collect_audio_files(path: Path, recursive: bool = True) -> List[Path]:
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
