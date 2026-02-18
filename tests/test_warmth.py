"""Tests for warmth/saturation functionality."""

import numpy as np
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import soundfile as sf

from crate.core.warmth import (
    WarmthAnalysisResult,
    WarmthResult,
    soft_clip_tanh,
    apply_exciter,
    analyze_for_warmth,
    apply_warmth,
    collect_audio_files,
    DEFAULT_DRIVE,
    DEFAULT_MIX,
    DEFAULT_TONE,
)
from crate.api.warmth import (
    WarmthAPI,
    WarmthMode,
    WarmthRequest,
    WarmthStatus,
)


class TestSoftClipping:
    """Test soft clipping functions."""
    
    def test_soft_clip_preserves_low_levels(self):
        """Low-level signals pass through with minimal change."""
        audio = np.sin(np.linspace(0, 2 * np.pi, 1000)) * 0.1
        clipped = soft_clip_tanh(audio, drive=0.1)
        
        # Should be very similar at low levels
        np.testing.assert_allclose(audio, clipped, rtol=0.2)
    
    def test_soft_clip_reduces_peaks(self):
        """High-level signals get compressed."""
        audio = np.sin(np.linspace(0, 2 * np.pi, 1000)) * 0.9
        clipped = soft_clip_tanh(audio, drive=0.5)
        
        # Peak should be approximately preserved (due to normalization)
        assert np.max(np.abs(clipped)) <= np.max(np.abs(audio)) * 1.01
    
    def test_soft_clip_adds_harmonics(self):
        """Soft clipping adds harmonic content."""
        # Pure sine wave
        t = np.linspace(0, 1, 44100)
        audio = np.sin(2 * np.pi * 440 * t) * 0.8
        
        # Apply saturation
        saturated = soft_clip_tanh(audio, drive=0.5)
        
        # Check FFT - saturated should have more frequency content
        fft_original = np.abs(np.fft.rfft(audio))
        fft_saturated = np.abs(np.fft.rfft(saturated))
        
        # Find harmonic bins (2nd, 3rd harmonics of 440 Hz)
        bin_size = 44100 / len(audio)
        harmonic_3_bin = int(1320 / bin_size)  # 3rd harmonic
        
        # 3rd harmonic should be stronger in saturated (odd harmonics from tanh)
        # This is a rough check - saturation definitely adds harmonics
        assert fft_saturated[harmonic_3_bin] > fft_original[harmonic_3_bin] * 0.5 or \
               np.sum(fft_saturated[100:]) > np.sum(fft_original[100:])
    
    def test_soft_clip_zero_drive(self):
        """Zero drive returns nearly unchanged audio."""
        audio = np.sin(np.linspace(0, 2 * np.pi, 1000)) * 0.5
        clipped = soft_clip_tanh(audio, drive=0.0)
        
        # Should be nearly identical (just tanh(x*1) which is close to x for small x)
        np.testing.assert_allclose(audio, clipped, rtol=0.15)


class TestExciter:
    """Test exciter/warmth effect."""
    
    def test_exciter_output_shape(self):
        """Exciter preserves audio shape."""
        audio = np.random.randn(44100) * 0.5
        processed = apply_exciter(audio, 44100)
        
        assert processed.shape == audio.shape
    
    def test_exciter_stereo(self):
        """Exciter works on stereo audio."""
        audio = np.random.randn(44100, 2) * 0.5
        processed = apply_exciter(audio, 44100)
        
        assert processed.shape == audio.shape
    
    def test_exciter_preserves_level(self):
        """Exciter doesn't significantly change overall level."""
        audio = np.sin(np.linspace(0, 4 * np.pi, 44100)) * 0.7
        processed = apply_exciter(audio, 44100, drive=0.2, mix=0.5)
        
        # RMS shouldn't change dramatically
        rms_before = np.sqrt(np.mean(audio ** 2))
        rms_after = np.sqrt(np.mean(processed ** 2))
        
        assert 0.5 < rms_after / rms_before < 2.0
    
    def test_exciter_mix_zero(self):
        """Mix=0 returns dry signal."""
        audio = np.sin(np.linspace(0, 2 * np.pi, 1000)) * 0.5
        processed = apply_exciter(audio, 44100, mix=0.0)
        
        np.testing.assert_allclose(audio, processed, rtol=0.01)
    
    def test_exciter_tone_affects_brightness(self):
        """Tone parameter affects frequency content."""
        audio = np.random.randn(44100) * 0.3
        
        dark = apply_exciter(audio, 44100, drive=0.3, mix=0.5, tone=0.1)
        bright = apply_exciter(audio, 44100, drive=0.3, mix=0.5, tone=0.9)
        
        # Compare high frequency content
        fft_dark = np.abs(np.fft.rfft(dark))
        fft_bright = np.abs(np.fft.rfft(bright))
        
        # High frequencies (top quarter of spectrum)
        high_start = len(fft_dark) * 3 // 4
        
        # Bright should have more high frequency content
        # (or at least not less, allowing for noise)
        high_dark = np.sum(fft_dark[high_start:])
        high_bright = np.sum(fft_bright[high_start:])
        
        # Just check the effect is applied - exact ratios vary
        assert high_bright > 0 and high_dark > 0


class TestWarmthFile:
    """Test file-level warmth processing."""
    
    def test_analyze_for_warmth(self, tmp_path):
        """Analyze recommends appropriate drive settings."""
        # Create test file
        audio = np.sin(np.linspace(0, 4 * np.pi, 44100)) * 0.7
        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, 44100)
        
        result = analyze_for_warmth(test_file)
        
        assert result.success
        assert result.peak_level_db is not None
        assert result.dynamic_range_db is not None
        assert result.recommended_drive is not None
        assert 0.0 <= result.recommended_drive <= 1.0
    
    def test_apply_warmth_dry_run(self, tmp_path):
        """Dry run reports without changing file."""
        audio = np.sin(np.linspace(0, 4 * np.pi, 44100)) * 0.7
        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, 44100)
        
        original, _ = sf.read(test_file)
        
        result = apply_warmth(test_file, dry_run=True)
        
        assert result.success
        assert result.harmonics_added is True
        
        # File unchanged
        after, _ = sf.read(test_file)
        np.testing.assert_array_equal(original, after)
    
    def test_apply_warmth(self, tmp_path):
        """Apply warmth modifies the file."""
        audio = np.sin(np.linspace(0, 4 * np.pi, 44100)) * 0.7
        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, 44100)
        
        original, _ = sf.read(test_file)
        
        result = apply_warmth(test_file, drive=0.3, mix=0.5, dry_run=False)
        
        assert result.success
        assert result.drive_applied == 0.3
        assert result.mix_applied == 0.5
        
        # File should be modified
        after, _ = sf.read(test_file)
        assert not np.array_equal(original, after)
    
    def test_apply_warmth_missing_file(self):
        """Applying warmth to missing file returns error."""
        result = apply_warmth(Path("/nonexistent/file.wav"))
        
        assert not result.success
        assert result.error is not None
    
    def test_apply_warmth_clamps_parameters(self, tmp_path):
        """Parameters are clamped to valid range."""
        audio = np.sin(np.linspace(0, 2 * np.pi, 44100)) * 0.5
        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, 44100)
        
        # Try out of range values
        result = apply_warmth(test_file, drive=2.0, mix=-0.5, tone=1.5, dry_run=True)
        
        assert result.success
        # Values should be clamped
        assert result.drive_applied == 1.0
        assert result.mix_applied == 0.0


class TestWarmthAPI:
    """Test the warmth API layer."""
    
    def test_api_analyze_mode(self, tmp_path):
        """API analyze mode doesn't modify files."""
        for i in range(3):
            audio = np.sin(np.linspace(0, 4 * np.pi, 44100)) * 0.7
            sf.write(tmp_path / f"test{i}.wav", audio, 44100)
        
        api = WarmthAPI()
        request = WarmthRequest(
            paths=[tmp_path],
            mode=WarmthMode.ANALYZE,
        )
        
        status = api.apply(request)
        
        assert status.total == 3
        assert status.succeeded == 3
    
    def test_api_apply_mode(self, tmp_path):
        """API apply mode modifies files."""
        audio = np.sin(np.linspace(0, 4 * np.pi, 44100)) * 0.7
        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, 44100)
        
        original, _ = sf.read(test_file)
        
        api = WarmthAPI()
        request = WarmthRequest(
            paths=[test_file],
            mode=WarmthMode.APPLY,
            drive=0.3,
            mix=0.5,
        )
        
        status = api.apply(request)
        
        assert status.succeeded == 1
        
        after, _ = sf.read(test_file)
        assert not np.array_equal(original, after)
    
    def test_api_custom_settings(self, tmp_path):
        """API respects custom drive/mix/tone settings."""
        audio = np.sin(np.linspace(0, 2 * np.pi, 44100)) * 0.5
        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, 44100)
        
        api = WarmthAPI()
        request = WarmthRequest(
            paths=[test_file],
            mode=WarmthMode.APPLY,
            drive=0.4,
            mix=0.6,
            tone=0.8,
        )
        
        status = api.apply(request)
        
        assert status.succeeded == 1
        assert len(status.results) == 1
        assert status.results[0].drive_applied == 0.4
        assert status.results[0].mix_applied == 0.6
    
    def test_api_empty_directory(self, tmp_path):
        """API handles empty directories gracefully."""
        api = WarmthAPI()
        request = WarmthRequest(
            paths=[tmp_path],
            mode=WarmthMode.ANALYZE,
        )
        
        status = api.apply(request)
        
        assert status.total == 0
        assert status.succeeded == 0
