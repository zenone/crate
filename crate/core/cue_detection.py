"""
Core cue detection logic - Detect musically meaningful points for DJ hot cues.

Detects:
- First beat (intro marker)
- Energy peaks (drop markers)
- Energy dips (breakdown markers)

Uses librosa for audio analysis and onset/energy detection.
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

# Import CuePoint and CueType from API (avoid circular import by importing at function level)

# Try to import analysis libraries
try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    from mutagen.mp3 import MP3
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


def get_audio_duration(file_path: Path, logger: logging.Logger) -> Optional[int]:
    """Get audio duration in milliseconds.

    Args:
        file_path: Path to audio file
        logger: Logger instance

    Returns:
        Duration in milliseconds or None on failure
    """
    if MUTAGEN_AVAILABLE and file_path.suffix.lower() == ".mp3":
        try:
            audio = MP3(str(file_path))
            if audio.info and audio.info.length:
                return int(audio.info.length * 1000)
        except Exception as e:
            logger.debug(f"mutagen failed for {file_path}: {e}")

    if LIBROSA_AVAILABLE:
        try:
            duration = librosa.get_duration(path=str(file_path))
            return int(duration * 1000)
        except Exception as e:
            logger.error(f"Failed to get duration for {file_path}: {e}")

    return None


def get_bpm(file_path: Path, logger: logging.Logger) -> Optional[float]:
    """Get BPM from file metadata or detection.

    Args:
        file_path: Path to audio file
        logger: Logger instance

    Returns:
        BPM as float or None
    """
    # Try to get from metadata first
    if MUTAGEN_AVAILABLE and file_path.suffix.lower() == ".mp3":
        try:
            from mutagen.id3 import ID3
            tags = ID3(str(file_path))
            for key in ['TBPM', 'BPM']:
                if key in tags:
                    bpm_val = str(tags[key])
                    return float(bpm_val)
        except Exception:
            pass

    # Fall back to detection (use existing Crate function)
    try:
        from .audio_analysis import detect_bpm_from_audio
        bpm_str, source = detect_bpm_from_audio(file_path, logger)
        if bpm_str:
            return float(bpm_str)
    except Exception as e:
        logger.debug(f"BPM detection failed for {file_path}: {e}")

    return None


def detect_first_beat(file_path: Path, logger: logging.Logger):
    """Detect the first beat/onset in the track.

    Args:
        file_path: Path to audio file
        logger: Logger instance

    Returns:
        CuePoint for the first beat or None
    """
    from crate.api.cue_detection import CuePoint, CueType

    if not LIBROSA_AVAILABLE:
        logger.error("librosa not available for beat detection")
        return None

    try:
        # Load audio (first 30 seconds is enough for intro detection)
        y, sr = librosa.load(str(file_path), duration=30, sr=22050)

        # Detect onsets
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units='frames')

        if len(onset_frames) == 0:
            # No onsets detected, use 0
            return CuePoint(
                position_ms=0,
                cue_type=CueType.INTRO,
                confidence=0.5,
                label="Intro"
            )

        # Get first onset time
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)
        first_onset_ms = int(onset_times[0] * 1000)

        # Round to nearest beat if BPM available
        bpm = get_bpm(file_path, logger)
        if bpm and bpm > 0:
            beat_length_ms = 60000 / bpm
            first_onset_ms = int(round(first_onset_ms / beat_length_ms) * beat_length_ms)

        logger.debug(f"First beat detected at {first_onset_ms}ms for {file_path.name}")

        return CuePoint(
            position_ms=first_onset_ms,
            cue_type=CueType.INTRO,
            confidence=0.9,
            label="Intro"
        )

    except Exception as e:
        logger.error(f"Failed to detect first beat in {file_path}: {e}")
        return None


def detect_energy_peaks(
    file_path: Path,
    logger: logging.Logger,
    sensitivity: float = 0.5
) -> List:
    """Detect energy peaks (potential drop points).

    Uses RMS energy envelope to find significant increases in energy.

    Args:
        file_path: Path to audio file
        logger: Logger instance
        sensitivity: Detection sensitivity (0.0-1.0, higher = more peaks)

    Returns:
        List of CuePoints for detected peaks
    """
    from crate.api.cue_detection import CuePoint, CueType

    if not LIBROSA_AVAILABLE:
        logger.error("librosa not available for energy detection")
        return []

    try:
        # Load full audio
        y, sr = librosa.load(str(file_path), sr=22050)
        duration_ms = int(len(y) / sr * 1000)

        # Compute RMS energy
        hop_length = 512
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

        # Compute energy derivative (rate of change)
        rms_diff = np.diff(rms)

        # Find peaks in derivative (energy increases)
        # Threshold based on sensitivity
        threshold = np.percentile(rms_diff[rms_diff > 0], 100 - sensitivity * 50)

        peak_frames: list[int] = []
        min_distance_frames = int(sr * 8 / hop_length)  # Minimum 8 seconds between peaks

        for i in range(1, len(rms_diff) - 1):
            if rms_diff[i] > threshold:
                if rms_diff[i] > rms_diff[i-1] and rms_diff[i] > rms_diff[i+1]:
                    # Local maximum
                    if not peak_frames or (i - peak_frames[-1]) > min_distance_frames:
                        peak_frames.append(i)

        # Convert to time and create CuePoints
        peaks = []
        for i, frame in enumerate(peak_frames[:4]):  # Limit to 4 drops
            time_ms = int(librosa.frames_to_time(frame, sr=sr, hop_length=hop_length) * 1000)

            # Skip if too early (likely just track start) or too late
            if time_ms < 15000 or time_ms > duration_ms - 30000:
                continue

            confidence = min(1.0, rms_diff[frame] / threshold)

            peaks.append(CuePoint(
                position_ms=time_ms,
                cue_type=CueType.DROP,
                confidence=confidence,
                label=f"Drop {i+1}"
            ))

        logger.debug(f"Detected {len(peaks)} energy peaks in {file_path.name}")
        return peaks

    except Exception as e:
        logger.error(f"Failed to detect energy peaks in {file_path}: {e}")
        return []


def detect_energy_dips(
    file_path: Path,
    logger: logging.Logger,
    sensitivity: float = 0.5
) -> List:
    """Detect energy dips (potential breakdown points).

    Uses RMS energy envelope to find significant decreases in energy.

    Args:
        file_path: Path to audio file
        logger: Logger instance
        sensitivity: Detection sensitivity (0.0-1.0, higher = more dips)

    Returns:
        List of CuePoints for detected dips
    """
    from crate.api.cue_detection import CuePoint, CueType

    if not LIBROSA_AVAILABLE:
        logger.error("librosa not available for energy detection")
        return []

    try:
        # Load full audio
        y, sr = librosa.load(str(file_path), sr=22050)
        duration_ms = int(len(y) / sr * 1000)

        # Compute RMS energy
        hop_length = 512
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

        # Smooth RMS to avoid noise
        from scipy.ndimage import uniform_filter1d
        rms_smooth = uniform_filter1d(rms, size=20)

        # Find local minima (valleys)
        # A breakdown is a sustained low-energy section
        threshold = np.percentile(rms_smooth, 30 + (1 - sensitivity) * 30)

        dip_frames: list[int] = []
        min_distance_frames = int(sr * 16 / hop_length)  # Minimum 16 seconds between breakdowns

        in_dip = False
        dip_start = 0

        for i in range(len(rms_smooth)):
            if rms_smooth[i] < threshold:
                if not in_dip:
                    in_dip = True
                    dip_start = i
            else:
                if in_dip:
                    in_dip = False
                    dip_length = i - dip_start
                    # Breakdown should be at least 2 seconds
                    min_dip_length = int(sr * 2 / hop_length)
                    if dip_length > min_dip_length:
                        if not dip_frames or (dip_start - dip_frames[-1]) > min_distance_frames:
                            dip_frames.append(dip_start)

        # Convert to CuePoints
        dips = []
        for i, frame in enumerate(dip_frames[:3]):  # Limit to 3 breakdowns
            time_ms = int(librosa.frames_to_time(frame, sr=sr, hop_length=hop_length) * 1000)

            # Skip if too early or too late
            if time_ms < 30000 or time_ms > duration_ms - 30000:
                continue

            dips.append(CuePoint(
                position_ms=time_ms,
                cue_type=CueType.BREAKDOWN,
                confidence=0.7,
                label=f"Breakdown {i+1}"
            ))

        logger.debug(f"Detected {len(dips)} energy dips in {file_path.name}")
        return dips

    except Exception as e:
        logger.error(f"Failed to detect energy dips in {file_path}: {e}")
        return []


def assign_hot_cue_slots(cues: List, max_cues: int = 8) -> List:
    """Assign hot cue slot indices to cue points.

    Sorts cues by position and assigns slots 0 through max_cues-1.

    Args:
        cues: List of CuePoints
        max_cues: Maximum number of cue points

    Returns:
        List of CuePoints with hot_cue_index assigned
    """
    # Sort by position
    sorted_cues = sorted(cues, key=lambda c: c.position_ms)

    # Limit count
    limited_cues = sorted_cues[:max_cues]

    # Assign indices
    for i, cue in enumerate(limited_cues):
        cue.hot_cue_index = i

    return limited_cues


def write_rekordbox_xml(
    results: List,
    output_path: Path,
    logger: logging.Logger
) -> None:
    """Write cue points to Rekordbox XML format.

    Creates a Rekordbox-compatible XML file with track and cue point data.

    Args:
        results: List of CueDetectionResult
        output_path: Path to write XML file
        logger: Logger instance
    """
    # Create root element
    root = ET.Element("DJ_PLAYLISTS")
    root.set("Version", "1.0.0")

    # Product info
    product = ET.SubElement(root, "PRODUCT")
    product.set("Name", "Crate")
    product.set("Version", "0.1.0")
    product.set("Company", "")

    # Collection
    collection = ET.SubElement(root, "COLLECTION")
    collection.set("Entries", str(len(results)))

    for result in results:
        if not result.success:
            continue

        # Track element
        track = ET.SubElement(collection, "TRACK")
        track.set("TrackID", str(hash(str(result.path)) & 0x7FFFFFFF))
        track.set("Name", result.path.stem)
        track.set("Location", f"file://localhost{result.path.absolute()}")

        if result.duration_ms:
            track.set("TotalTime", str(result.duration_ms // 1000))

        if result.bpm:
            track.set("AverageBpm", f"{result.bpm:.2f}")

        # Add cue points as POSITION_MARK elements
        for cue in result.cues:
            pos_mark = ET.SubElement(track, "POSITION_MARK")
            pos_mark.set("Name", cue.label or cue.cue_type.value)
            pos_mark.set("Type", "0")  # Hot cue
            pos_mark.set("Start", str(cue.position_ms / 1000))  # Seconds
            pos_mark.set("Num", str(cue.hot_cue_index or 0))

            if cue.color:
                # Convert to Rekordbox color format
                r = (cue.color >> 16) & 0xFF
                g = (cue.color >> 8) & 0xFF
                b = cue.color & 0xFF
                pos_mark.set("Red", str(r))
                pos_mark.set("Green", str(g))
                pos_mark.set("Blue", str(b))

    # Write to file
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")

    with open(output_path, "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)

    logger.info(f"Wrote Rekordbox XML to {output_path}")
