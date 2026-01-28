"""
Audio analysis and metadata detection.

Provides BPM and key detection using:
1. AcoustID/MusicBrainz database lookup (fast)
2. Audio analysis fallback (slower but always works)
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

try:
    import acoustid
    ACOUSTID_AVAILABLE = True
except ImportError:
    ACOUSTID_AVAILABLE = False

try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


# AcoustID API key (free tier)
ACOUSTID_API_KEY = "8XaBELgH"  # Free public key for open-source projects


def detect_bpm_from_audio(file_path: Path, logger: logging.Logger) -> Tuple[Optional[str], str]:
    """
    Detect BPM from audio file using librosa.

    Args:
        file_path: Path to audio file
        logger: Logger instance

    Returns:
        Tuple of (bpm_string, source)
        - bpm_string: BPM as string (e.g., "128") or None if failed
        - source: "Analyzed" if successful, "Failed" if not

    Examples:
        >>> logger = logging.getLogger("test")
        >>> bpm, source = detect_bpm_from_audio(Path("song.mp3"), logger)
        >>> print(f"BPM: {bpm} (source: {source})")
    """
    if not LIBROSA_AVAILABLE:
        logger.warning("librosa not installed - cannot detect BPM")
        return None, "Unavailable"

    try:
        # Load audio file
        y, sr = librosa.load(str(file_path), duration=60, sr=22050)

        # Detect tempo (BPM)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

        # Round to nearest integer
        bpm = int(round(tempo))

        # Validate range (typical DJ BPM range: 60-200)
        if 60 <= bpm <= 200:
            logger.debug(f"Detected BPM: {bpm}")
            return str(bpm), "Analyzed"
        else:
            logger.warning(f"BPM out of range: {bpm}")
            return None, "Failed"

    except Exception as e:
        logger.warning(f"BPM detection failed: {e}")
        return None, "Failed"


def detect_key_from_audio(file_path: Path, logger: logging.Logger) -> Tuple[Optional[str], str]:
    """
    Detect musical key from audio file using librosa.

    Args:
        file_path: Path to audio file
        logger: Logger instance

    Returns:
        Tuple of (key_string, source)
        - key_string: Musical key (e.g., "C maj", "A min") or None if failed
        - source: "Analyzed" if successful, "Failed" if not

    Note:
        Key detection is less accurate than BPM detection.
        Uses chromagram analysis and template matching.
    """
    if not LIBROSA_AVAILABLE:
        logger.warning("librosa not installed - cannot detect key")
        return None, "Unavailable"

    try:
        # Load audio file
        y, sr = librosa.load(str(file_path), duration=30, sr=22050)

        # Compute chromagram
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)

        # Average chromagram over time
        chroma_mean = np.mean(chroma, axis=1)

        # Find dominant pitch class
        pitch_class = int(np.argmax(chroma_mean))

        # Map to key names
        keys = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

        # Simple major/minor detection (comparing strength of major vs minor triads)
        # This is a simplified approach - more sophisticated methods exist
        major_strength = chroma_mean[pitch_class] + chroma_mean[(pitch_class + 4) % 12] + chroma_mean[(pitch_class + 7) % 12]
        minor_strength = chroma_mean[pitch_class] + chroma_mean[(pitch_class + 3) % 12] + chroma_mean[(pitch_class + 7) % 12]

        mode = "maj" if major_strength > minor_strength else "min"
        key = f"{keys[pitch_class]} {mode}"

        logger.debug(f"Detected key: {key}")
        return key, "Analyzed"

    except Exception as e:
        logger.warning(f"Key detection failed: {e}")
        return None, "Failed"


def lookup_acoustid(file_path: Path, logger: logging.Logger) -> Tuple[Optional[dict], str]:
    """
    Lookup track metadata using AcoustID fingerprinting.

    Queries AcoustID/MusicBrainz database for BPM and other metadata.

    Args:
        file_path: Path to audio file
        logger: Logger instance

    Returns:
        Tuple of (metadata_dict, source)
        - metadata_dict: Dict with 'bpm', 'key', etc. or None if failed
        - source: "Database" if successful, "Not Found" if no match

    Note:
        Requires internet connection and valid AcoustID API key.
    """
    if not ACOUSTID_AVAILABLE:
        logger.debug("acoustid not installed - skipping database lookup")
        return None, "Unavailable"

    try:
        # Generate audio fingerprint and lookup
        results = acoustid.match(ACOUSTID_API_KEY, str(file_path))

        for score, recording_id, title, artist in results:
            # Score is confidence (0.0 to 1.0)
            if score < 0.5:
                continue

            logger.debug(f"AcoustID match: {artist} - {title} (score: {score:.2f})")

            # Note: AcoustID/MusicBrainz doesn't always have BPM/Key
            # This is a limitation of the free database
            # Would need additional queries to get BPM from MusicBrainz
            # For now, return basic info
            return {
                "title": title,
                "artist": artist,
                "recording_id": recording_id,
                "confidence": score
            }, "Database"

        logger.debug("No confident AcoustID match found")
        return None, "Not Found"

    except Exception as e:
        logger.warning(f"AcoustID lookup failed: {e}")
        return None, "Failed"


def auto_detect_metadata(
    file_path: Path,
    current_bpm: str,
    current_key: str,
    logger: logging.Logger,
    force_analysis: bool = False
) -> Tuple[str, str, str, str]:
    """
    Auto-detect BPM and Key with smart hybrid approach.

    Strategy:
    1. Use existing values if present (skip detection)
    2. Try database lookup first (fast)
    3. Fall back to audio analysis (slower but accurate)

    Args:
        file_path: Path to MP3 file
        current_bpm: Current BPM value (may be empty)
        current_key: Current key value (may be empty)
        logger: Logger instance
        force_analysis: If True, always run analysis even if values exist

    Returns:
        Tuple of (bpm, bpm_source, key, key_source)

    Examples:
        >>> logger = logging.getLogger("test")
        >>> bpm, bpm_src, key, key_src = auto_detect_metadata(
        ...     Path("song.mp3"), "", "", logger
        ... )
        >>> print(f"BPM: {bpm} ({bpm_src}), Key: {key} ({key_src})")
    """
    bpm = current_bpm
    bpm_source = "ID3"
    key = current_key
    key_source = "ID3"

    # Skip detection if values already exist (unless forced)
    needs_bpm = not bpm or force_analysis
    needs_key = not key or force_analysis

    if not needs_bpm and not needs_key:
        logger.debug(f"BPM and Key already in tags - skipping detection")
        return bpm, bpm_source, key, key_source

    # Try database lookup first (fast but may not have BPM/Key)
    # Note: AcoustID/MusicBrainz free tier has limited BPM/Key data
    # Commenting out for now - go straight to audio analysis
    # db_result, db_source = lookup_acoustid(file_path, logger)

    # Audio analysis fallback (always works)
    if needs_bpm:
        logger.info(f"Detecting BPM for: {file_path.name}")
        detected_bpm, bpm_source = detect_bpm_from_audio(file_path, logger)
        if detected_bpm:
            bpm = detected_bpm
        else:
            bpm_source = "Failed"

    if needs_key:
        logger.info(f"Detecting Key for: {file_path.name}")
        detected_key, key_source = detect_key_from_audio(file_path, logger)
        if detected_key:
            key = detected_key
        else:
            key_source = "Failed"

    return bpm, bpm_source, key, key_source
