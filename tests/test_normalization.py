"""
Tests for audio normalization module.

TDD approach: These tests define expected behavior.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from crate.api.normalization import (
    NormalizationAPI,
    NormalizationMode,
    NormalizationRequest,
    NormalizationResult,
    NormalizationStatus,
)


class TestNormalizationModels:
    """Test data models."""

    def test_normalization_mode_enum(self):
        """NormalizationMode has correct values."""
        assert NormalizationMode.ANALYZE.value == "analyze"
        assert NormalizationMode.TAG.value == "tag"
        assert NormalizationMode.APPLY.value == "apply"

    def test_normalization_request_defaults(self):
        """NormalizationRequest has sensible defaults."""
        request = NormalizationRequest(paths=[Path("test.mp3")])

        assert request.mode == NormalizationMode.ANALYZE
        assert request.target_lufs == -14.0
        assert request.prevent_clipping is True
        assert request.recursive is False

    def test_normalization_result_success(self):
        """NormalizationResult can represent success."""
        result = NormalizationResult(
            path=Path("test.mp3"),
            success=True,
            original_lufs=-8.5,
            original_peak_db=-0.3,
            adjustment_db=-5.5,
            clipping_prevented=False
        )

        assert result.success is True
        assert result.original_lufs == -8.5
        assert result.adjustment_db == -5.5
        assert result.error is None

    def test_normalization_result_failure(self):
        """NormalizationResult can represent failure."""
        result = NormalizationResult(
            path=Path("test.mp3"),
            success=False,
            error="File not found"
        )

        assert result.success is False
        assert result.error == "File not found"

    def test_normalization_status_tracking(self):
        """NormalizationStatus tracks progress correctly."""
        status = NormalizationStatus()
        assert status.total == 0
        assert status.processed == 0
        assert status.succeeded == 0
        assert status.failed == 0
        assert status.results == []


class TestNormalizationCore:
    """Test core normalization functions."""

    def test_analyze_loudness_returns_tuple(self):
        """analyze_loudness returns (lufs, peak_db) tuple."""
        from crate.core.normalization import analyze_loudness

        # This will fail until we implement the module
        # The test defines the expected interface
        logger = Mock()

        # Use a real test file if available, otherwise mock
        test_file = Path("tests/fixtures/test_track.mp3")
        if not test_file.exists():
            pytest.skip("No test fixture available")

        lufs, peak_db = analyze_loudness(test_file, logger)

        assert isinstance(lufs, float)
        assert isinstance(peak_db, float)
        assert -70.0 <= lufs <= 0.0  # Typical LUFS range
        assert -70.0 <= peak_db <= 0.0  # Peak should be <= 0 dB

    def test_calculate_adjustment_basic(self):
        """calculate_adjustment computes correct gain."""
        from crate.core.normalization import calculate_adjustment

        # Track at -10 LUFS, target -14 LUFS → need -4 dB adjustment
        adjustment, clipping = calculate_adjustment(
            current_lufs=-10.0,
            target_lufs=-14.0,
            peak_db=-6.0,
            prevent_clipping=False
        )

        assert adjustment == pytest.approx(-4.0, abs=0.1)
        assert clipping is False

    def test_calculate_adjustment_prevents_clipping(self):
        """calculate_adjustment reduces gain to prevent clipping."""
        from crate.core.normalization import calculate_adjustment

        # Track at -10 LUFS with -1 dB peak
        # Target -14 LUFS would need -4 dB adjustment
        # But applying -4 dB leaves headroom, so no clipping issue here

        # Track at -18 LUFS with -1 dB peak
        # Target -14 LUFS would need +4 dB adjustment
        # But peak is at -1 dB, so +4 dB would push to +3 dB → clip!
        adjustment, clipping = calculate_adjustment(
            current_lufs=-18.0,
            target_lufs=-14.0,
            peak_db=-1.0,
            prevent_clipping=True
        )

        # Should limit adjustment to +1 dB (peak would hit 0 dB)
        assert adjustment <= 1.0
        assert clipping is True

    def test_collect_audio_files_mp3(self):
        """collect_audio_files finds MP3 files."""
        from crate.core.normalization import collect_audio_files

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "track1.mp3").touch()
            (Path(tmpdir) / "track2.mp3").touch()
            (Path(tmpdir) / "cover.jpg").touch()  # Should be ignored

            files = collect_audio_files([Path(tmpdir)], recursive=False)

            assert len(files) == 2
            assert all(f.suffix == ".mp3" for f in files)

    def test_collect_audio_files_recursive(self):
        """collect_audio_files handles recursive mode."""
        from crate.core.normalization import collect_audio_files

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / "track1.mp3").touch()
            (base / "subdir").mkdir()
            (base / "subdir" / "track2.mp3").touch()

            # Non-recursive
            files_flat = collect_audio_files([base], recursive=False)
            assert len(files_flat) == 1

            # Recursive
            files_recursive = collect_audio_files([base], recursive=True)
            assert len(files_recursive) == 2


class TestNormalizationAPI:
    """Test the NormalizationAPI class."""

    def test_api_initialization(self):
        """API initializes with optional logger."""
        api = NormalizationAPI()
        assert api.logger is not None

        custom_logger = Mock()
        api2 = NormalizationAPI(logger=custom_logger)
        assert api2.logger is custom_logger

    @patch('crate.api.normalization.NormalizationAPI._process_file')
    @patch('crate.core.normalization.collect_audio_files')
    def test_api_normalize_calls_process_file(self, mock_collect, mock_process):
        """API.normalize processes each file."""
        mock_collect.return_value = [Path("a.mp3"), Path("b.mp3")]
        mock_process.return_value = NormalizationResult(
            path=Path("test.mp3"),
            success=True,
            original_lufs=-10.0,
            adjustment_db=-4.0
        )

        api = NormalizationAPI()
        request = NormalizationRequest(paths=[Path(".")])
        status = api.normalize(request)

        assert status.total == 2
        assert status.processed == 2
        assert status.succeeded == 2
        assert mock_process.call_count == 2

    def test_api_normalize_tracks_failures(self):
        """API.normalize correctly tracks failed files."""
        api = NormalizationAPI()

        with patch.object(api, '_process_file') as mock_process:
            with patch('crate.core.normalization.collect_audio_files') as mock_collect:
                mock_collect.return_value = [Path("a.mp3"), Path("b.mp3")]
                mock_process.side_effect = [
                    NormalizationResult(path=Path("a.mp3"), success=True),
                    NormalizationResult(path=Path("b.mp3"), success=False, error="Failed"),
                ]

                request = NormalizationRequest(paths=[Path(".")])
                status = api.normalize(request)

                assert status.succeeded == 1
                assert status.failed == 1


class TestNormalizationIntegration:
    """Integration tests with real audio files."""

    @pytest.fixture
    def smoke_test_dir(self):
        """Get the canonical smoke test directory."""
        path = Path.home() / "Music" / "DJ" / "CrateSmokeTest"
        if not path.exists():
            pytest.skip("Smoke test directory not available")
        return path

    @pytest.fixture
    def temp_copy(self, smoke_test_dir):
        """Create a temporary copy for safe testing."""
        tmpdir = Path(tempfile.mkdtemp(prefix="crate_norm_test_"))
        # Copy first MP3 file
        mp3_files = list(smoke_test_dir.glob("*.mp3"))
        if not mp3_files:
            pytest.skip("No MP3 files in smoke test directory")

        test_file = tmpdir / mp3_files[0].name
        shutil.copy2(mp3_files[0], test_file)

        yield test_file

        # Cleanup
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_analyze_real_file(self, temp_copy):
        """Can analyze a real MP3 file."""
        api = NormalizationAPI()
        request = NormalizationRequest(
            paths=[temp_copy],
            mode=NormalizationMode.ANALYZE
        )

        status = api.normalize(request)

        assert status.total == 1
        assert status.succeeded == 1
        assert status.results[0].original_lufs is not None
        assert -30.0 <= status.results[0].original_lufs <= 0.0
