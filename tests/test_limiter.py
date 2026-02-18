"""Tests for peak limiter functionality."""

import numpy as np
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from crate.core.limiter import (
    LimiterResult,
    db_to_linear,
    linear_to_db,
    percent_to_db,
    analyze_peaks,
    apply_limiter,
    limit_file,
    collect_audio_files,
    DEFAULT_CEILING_PERCENT,
    DEFAULT_CEILING_DB,
)
from crate.api.limiter import (
    LimiterAPI,
    LimiterMode,
    LimiterRequest,
    LimiterStatus,
)


class TestLimiterConversions:
    """Test audio level conversion functions."""
    
    def test_db_to_linear_unity(self):
        """0 dB equals linear 1.0."""
        assert db_to_linear(0) == pytest.approx(1.0)
    
    def test_db_to_linear_minus6(self):
        """-6 dB is approximately 0.5 linear."""
        assert db_to_linear(-6) == pytest.approx(0.501, rel=0.01)
    
    def test_linear_to_db_unity(self):
        """Linear 1.0 equals 0 dB."""
        assert linear_to_db(1.0) == pytest.approx(0.0)
    
    def test_linear_to_db_half(self):
        """Linear 0.5 is approximately -6 dB."""
        assert linear_to_db(0.5) == pytest.approx(-6.02, rel=0.01)
    
    def test_linear_to_db_zero(self):
        """Linear 0 returns negative infinity."""
        result = linear_to_db(0)
        assert result == -np.inf
    
    def test_percent_to_db_100(self):
        """100% equals 0 dB."""
        assert percent_to_db(100) == pytest.approx(0.0)
    
    def test_percent_to_db_997(self):
        """99.7% equals approximately -0.026 dB."""
        result = percent_to_db(99.7)
        assert result == pytest.approx(-0.026, rel=0.1)
    
    def test_default_ceiling_matches(self):
        """Default ceiling percent and dB are consistent."""
        calculated_db = percent_to_db(DEFAULT_CEILING_PERCENT)
        assert calculated_db == pytest.approx(DEFAULT_CEILING_DB, rel=0.01)


class TestLimiterCore:
    """Test core limiter functions."""
    
    def test_analyze_peaks_mono(self):
        """Analyze peaks works with mono audio."""
        audio = np.array([0.5, -0.8, 0.3, -0.2])
        peak_linear, peak_db = analyze_peaks(audio)
        
        assert peak_linear == pytest.approx(0.8)
        assert peak_db == pytest.approx(linear_to_db(0.8))
    
    def test_analyze_peaks_stereo(self):
        """Analyze peaks works with stereo audio."""
        audio = np.array([[0.5, 0.3], [-0.8, 0.9], [0.3, -0.2]])
        peak_linear, peak_db = analyze_peaks(audio)
        
        assert peak_linear == pytest.approx(0.9)
    
    def test_apply_limiter_reduces_peaks(self):
        """Limiter reduces peaks above ceiling."""
        # Create audio with peaks above 99.7%
        audio = np.array([0.5, 1.0, -1.0, 0.3])  # Has peaks at +/- 1.0
        sample_rate = 44100
        
        limited, samples_affected = apply_limiter(audio, sample_rate, ceiling_db=-0.03)
        
        # Peak should be reduced
        assert np.max(np.abs(limited)) <= 1.0
        assert samples_affected > 0
    
    def test_apply_limiter_preserves_quiet(self):
        """Limiter doesn't affect audio below ceiling."""
        # Create quiet audio
        audio = np.array([0.1, 0.2, -0.15, 0.05])
        sample_rate = 44100
        
        limited, samples_affected = apply_limiter(audio, sample_rate, ceiling_db=-0.03)
        
        # Should be essentially unchanged
        assert samples_affected == 0
        np.testing.assert_array_almost_equal(audio, limited, decimal=5)
    
    def test_collect_audio_files_directory(self, tmp_path):
        """Collect audio files from a directory."""
        # Create test files
        (tmp_path / "track1.mp3").touch()
        (tmp_path / "track2.wav").touch()
        (tmp_path / "readme.txt").touch()
        
        files = collect_audio_files(tmp_path, recursive=False)
        
        assert len(files) == 2
        assert all(f.suffix in {'.mp3', '.wav'} for f in files)
    
    def test_collect_audio_files_recursive(self, tmp_path):
        """Collect audio files recursively."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "track1.mp3").touch()
        (subdir / "track2.mp3").touch()
        
        files = collect_audio_files(tmp_path, recursive=True)
        
        assert len(files) == 2
    
    def test_collect_audio_files_single_file(self, tmp_path):
        """Collect works with a single file."""
        file_path = tmp_path / "track.mp3"
        file_path.touch()
        
        files = collect_audio_files(file_path)
        
        assert len(files) == 1
        assert files[0] == file_path


class TestLimiterModels:
    """Test limiter data models."""
    
    def test_limiter_result_success(self):
        """LimiterResult can represent success."""
        result = LimiterResult(
            path=Path("test.mp3"),
            success=True,
            original_peak_db=-0.5,
            limited_peak_db=-0.5,
            reduction_db=0.0,
            samples_limited=0,
        )
        
        assert result.success
        assert result.error is None
    
    def test_limiter_result_failure(self):
        """LimiterResult can represent failure."""
        result = LimiterResult(
            path=Path("missing.mp3"),
            success=False,
            error="File not found",
        )
        
        assert not result.success
        assert "File not found" in result.error
    
    def test_limiter_request_defaults(self):
        """LimiterRequest has Platinum Notes defaults."""
        request = LimiterRequest(paths=[Path("test.mp3")])
        
        assert request.mode == LimiterMode.ANALYZE
        assert request.ceiling_percent == 99.7  # Platinum Notes default
        assert request.release_ms == 100.0
        assert request.recursive is True
    
    def test_limiter_status_tracking(self):
        """LimiterStatus tracks results correctly."""
        status = LimiterStatus()
        status.total = 3
        status.succeeded = 2
        status.failed = 1
        status.needed_limiting = 1
        
        assert status.total == 3
        assert status.succeeded == 2


class TestLimiterAPI:
    """Test the limiter API layer."""
    
    def test_api_initialization(self):
        """LimiterAPI initializes correctly."""
        api = LimiterAPI(max_workers=2)
        
        assert api.max_workers == 2
    
    @patch('crate.api.limiter.limit_file')
    @patch('crate.api.limiter.collect_audio_files')
    def test_api_limit_processes_files(self, mock_collect, mock_limit):
        """API processes collected files."""
        mock_collect.return_value = [Path("a.mp3"), Path("b.mp3")]
        mock_limit.return_value = LimiterResult(
            path=Path("test.mp3"),
            success=True,
            original_peak_db=-1.0,
            limited_peak_db=-1.0,
            reduction_db=0.0,
            samples_limited=0,
        )
        
        api = LimiterAPI()
        request = LimiterRequest(paths=[Path("/music")])
        status = api.limit(request)
        
        assert status.total == 2
        assert status.succeeded == 2
        assert mock_limit.call_count == 2


class TestLimiterIntegration:
    """Integration tests with real audio files."""
    
    @pytest.fixture
    def smoke_test_dir(self):
        """Path to smoke test directory if it exists."""
        path = Path.home() / "Music" / "DJ" / "CrateSmokeTest"
        if not path.exists():
            pytest.skip("Smoke test directory not found")
        return path
    
    def test_analyze_real_file(self, smoke_test_dir):
        """Analyze a real audio file."""
        files = list(smoke_test_dir.glob("*.mp3"))
        if not files:
            pytest.skip("No MP3 files in smoke test directory")
        
        result = limit_file(files[0], dry_run=True)
        
        assert result.success
        assert result.original_peak_db is not None
        assert result.original_peak_db <= 0  # Should be at or below 0 dBFS
