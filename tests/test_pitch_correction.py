"""Tests for pitch correction functionality."""

import numpy as np
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from crate.core.pitch_correction import (
    PitchAnalysisResult,
    PitchCorrectionResult,
    hz_to_midi,
    midi_to_hz,
    midi_to_note_name,
    calculate_deviation_cents,
    detect_pitch,
    analyze_pitch,
    correct_pitch,
    collect_audio_files,
    DEFAULT_THRESHOLD_CENTS,
)
from crate.api.pitch_correction import (
    PitchCorrectionAPI,
    PitchCorrectionMode,
    PitchCorrectionRequest,
    PitchCorrectionStatus,
)


class TestPitchConversions:
    """Test pitch conversion functions."""
    
    def test_hz_to_midi_a440(self):
        """A440 should be MIDI note 69."""
        assert hz_to_midi(440.0) == pytest.approx(69.0)
    
    def test_hz_to_midi_a880(self):
        """A880 (octave up) should be MIDI note 81."""
        assert hz_to_midi(880.0) == pytest.approx(81.0)
    
    def test_midi_to_hz_69(self):
        """MIDI note 69 should be 440 Hz."""
        assert midi_to_hz(69) == pytest.approx(440.0)
    
    def test_midi_to_hz_81(self):
        """MIDI note 81 should be 880 Hz."""
        assert midi_to_hz(81) == pytest.approx(880.0)
    
    def test_midi_to_note_name_a4(self):
        """MIDI note 69 is A4."""
        assert midi_to_note_name(69) == "A4"
    
    def test_midi_to_note_name_c4(self):
        """MIDI note 60 is C4 (middle C)."""
        assert midi_to_note_name(60) == "C4"
    
    def test_midi_to_note_name_sharp(self):
        """MIDI note 61 is C#4."""
        assert midi_to_note_name(61) == "C#4"
    
    def test_calculate_deviation_in_tune(self):
        """A440 has zero deviation from A4."""
        deviation, nearest, note = calculate_deviation_cents(440.0)
        assert deviation == pytest.approx(0.0)
        assert note == "A4"
    
    def test_calculate_deviation_sharp(self):
        """Slightly sharp pitch has positive deviation."""
        # 5 cents sharp from A4
        freq = 440.0 * (2 ** (5 / 1200))
        deviation, nearest, note = calculate_deviation_cents(freq)
        assert deviation == pytest.approx(5.0, rel=0.1)
        assert note == "A4"
    
    def test_calculate_deviation_flat(self):
        """Slightly flat pitch has negative deviation."""
        # 5 cents flat from A4
        freq = 440.0 * (2 ** (-5 / 1200))
        deviation, nearest, note = calculate_deviation_cents(freq)
        assert deviation == pytest.approx(-5.0, rel=0.1)
        assert note == "A4"


class TestPitchDetection:
    """Test pitch detection functions."""
    
    def test_detect_pitch_sine_wave(self):
        """Detect pitch of a pure sine wave."""
        sample_rate = 22050
        duration = 1.0
        freq = 440.0  # A4
        
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        audio = np.sin(2 * np.pi * freq * t).astype(np.float32)
        
        detected = detect_pitch(audio, sample_rate)
        
        # Should detect approximately 440 Hz
        assert detected is not None
        assert detected == pytest.approx(440.0, rel=0.05)  # 5% tolerance
    
    def test_detect_pitch_stereo(self):
        """Detect pitch converts stereo to mono."""
        sample_rate = 22050
        duration = 0.5
        freq = 440.0
        
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        mono = np.sin(2 * np.pi * freq * t).astype(np.float32)
        stereo = np.column_stack([mono, mono])
        
        detected = detect_pitch(stereo, sample_rate)
        
        assert detected is not None
    
    def test_detect_pitch_silence(self):
        """Silence returns None."""
        sample_rate = 22050
        audio = np.zeros(sample_rate, dtype=np.float32)
        
        detected = detect_pitch(audio, sample_rate)
        
        assert detected is None


class TestPitchModels:
    """Test pitch data models."""
    
    def test_analysis_result_success(self):
        """PitchAnalysisResult can represent success."""
        result = PitchAnalysisResult(
            path=Path("test.mp3"),
            success=True,
            detected_pitch_hz=440.0,
            nearest_note="A4",
            deviation_cents=2.5,
            needs_correction=False,
        )
        
        assert result.success
        assert result.detected_pitch_hz == 440.0
        assert not result.needs_correction
    
    def test_analysis_result_needs_correction(self):
        """PitchAnalysisResult flags files needing correction."""
        result = PitchAnalysisResult(
            path=Path("test.mp3"),
            success=True,
            detected_pitch_hz=442.0,
            nearest_note="A4",
            deviation_cents=15.0,
            needs_correction=True,
        )
        
        assert result.needs_correction
    
    def test_correction_result_success(self):
        """PitchCorrectionResult can represent successful correction."""
        result = PitchCorrectionResult(
            path=Path("test.mp3"),
            success=True,
            original_pitch_hz=442.0,
            corrected_pitch_hz=440.0,
            shift_cents=-7.8,
            nearest_note="A4",
        )
        
        assert result.success
        assert result.shift_cents < 0  # Pitch was shifted down
    
    def test_correction_request_defaults(self):
        """PitchCorrectionRequest has Platinum Notes defaults."""
        request = PitchCorrectionRequest(paths=[Path("test.mp3")])
        
        assert request.mode == PitchCorrectionMode.ANALYZE
        assert request.threshold_cents == 10.0  # Platinum Notes default
        assert request.recursive is True


class TestPitchAPI:
    """Test the pitch correction API layer."""
    
    def test_api_initialization(self):
        """PitchCorrectionAPI initializes correctly."""
        api = PitchCorrectionAPI(max_workers=2)
        
        assert api.max_workers == 2
    
    @patch('crate.api.pitch_correction.correct_pitch')
    @patch('crate.api.pitch_correction.collect_audio_files')
    def test_api_process_files(self, mock_collect, mock_correct):
        """API processes collected files."""
        mock_collect.return_value = [Path("a.mp3"), Path("b.mp3")]
        mock_correct.return_value = PitchCorrectionResult(
            path=Path("test.mp3"),
            success=True,
            original_pitch_hz=440.0,
            corrected_pitch_hz=440.0,
            shift_cents=0,
            nearest_note="A4",
        )
        
        api = PitchCorrectionAPI()
        request = PitchCorrectionRequest(paths=[Path("/music")])
        status = api.process(request)
        
        assert status.total == 2
        assert status.succeeded == 2
        assert mock_correct.call_count == 2


class TestCollectAudioFiles:
    """Test audio file collection."""
    
    def test_collect_from_directory(self, tmp_path):
        """Collect audio files from a directory."""
        (tmp_path / "track1.mp3").touch()
        (tmp_path / "track2.wav").touch()
        (tmp_path / "readme.txt").touch()
        
        files = collect_audio_files(tmp_path, recursive=False)
        
        assert len(files) == 2
        assert all(f.suffix in {'.mp3', '.wav'} for f in files)
    
    def test_collect_recursive(self, tmp_path):
        """Collect audio files recursively."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "track1.mp3").touch()
        (subdir / "track2.mp3").touch()
        
        files = collect_audio_files(tmp_path, recursive=True)
        
        assert len(files) == 2
    
    def test_collect_single_file(self, tmp_path):
        """Collect works with a single file."""
        file_path = tmp_path / "track.mp3"
        file_path.touch()
        
        files = collect_audio_files(file_path)
        
        assert len(files) == 1
        assert files[0] == file_path


class TestPitchIntegration:
    """Integration tests with real audio files."""
    
    @pytest.fixture
    def smoke_test_dir(self):
        """Path to smoke test directory if it exists."""
        path = Path.home() / "Music" / "DJ" / "CrateSmokeTest"
        if not path.exists():
            pytest.skip("Smoke test directory not found")
        return path
    
    def test_analyze_real_file(self, smoke_test_dir):
        """Analyze pitch of a real audio file."""
        files = list(smoke_test_dir.glob("*.mp3"))
        if not files:
            pytest.skip("No MP3 files in smoke test directory")
        
        result = analyze_pitch(files[0])
        
        assert result.success
        # Real music should have a detectable pitch
        # (or None if the track has no clear pitch)
