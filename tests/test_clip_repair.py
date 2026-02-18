"""Tests for clipped peak repair functionality."""

import numpy as np
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import soundfile as sf

from crate.core.clip_repair import (
    ClipAnalysisResult,
    ClipRepairResult,
    detect_clipping_regions,
    repair_clip_region,
    repair_clipping,
    analyze_clipping,
    repair_file,
    collect_audio_files,
    DEFAULT_CLIP_THRESHOLD,
    DEFAULT_MIN_CLIP_SAMPLES,
)
from crate.api.clip_repair import (
    ClipRepairAPI,
    ClipRepairMode,
    ClipRepairRequest,
    ClipRepairStatus,
)


class TestClippingDetection:
    """Test clipping detection functions."""
    
    def test_detect_no_clipping(self):
        """Audio with no clipping returns empty list."""
        audio = np.sin(np.linspace(0, 4 * np.pi, 1000)) * 0.5
        regions = detect_clipping_regions(audio)
        assert regions == []
    
    def test_detect_positive_clipping(self):
        """Detect positive clipped regions."""
        audio = np.sin(np.linspace(0, 2 * np.pi, 1000))
        # Create clipping at peak
        audio[240:260] = 1.0  # Flat top at peak
        
        regions = detect_clipping_regions(audio, threshold=0.99, min_samples=3)
        assert len(regions) >= 1
        
        # Check we found a region that covers the clipped area (240-260)
        # The region may be larger due to natural sine peak above threshold
        positive_regions = [r for r in regions if r[2] == 1]  # polarity +1
        assert len(positive_regions) >= 1
        
        # The clipped area (240-260) should be within one of the detected regions
        found = any(start <= 240 and end >= 260 for start, end, _ in positive_regions)
        assert found, f"Expected region covering 240-260, found: {positive_regions}"
    
    def test_detect_negative_clipping(self):
        """Detect negative clipped regions."""
        audio = np.sin(np.linspace(0, 2 * np.pi, 1000))
        # Create clipping at trough
        audio[740:760] = -1.0  # Flat bottom at trough
        
        regions = detect_clipping_regions(audio, threshold=0.99, min_samples=3)
        assert len(regions) >= 1
        
        # Check polarity
        polarities = [r[2] for r in regions]
        assert -1 in polarities
    
    def test_detect_minimum_samples_filter(self):
        """Short clips below min_samples are ignored."""
        audio = np.zeros(1000)
        audio[100:102] = 1.0  # Only 2 samples
        
        regions = detect_clipping_regions(audio, threshold=0.99, min_samples=3)
        assert len(regions) == 0
        
        regions = detect_clipping_regions(audio, threshold=0.99, min_samples=2)
        assert len(regions) == 1


class TestClipRepair:
    """Test clip repair functions."""
    
    def test_repair_single_region(self):
        """Repair smooths out a clipped region."""
        # Create a sine wave with a clipped peak
        audio = np.sin(np.linspace(0, 2 * np.pi, 1000))
        original_clipped = audio.copy()
        audio[245:255] = 1.0  # Flat clipped region
        
        # Repair the region
        repair_clip_region(audio, 245, 255, 1)
        
        # The repaired region should no longer be flat
        repaired_section = audio[245:255]
        assert not np.all(repaired_section == 1.0)
        
        # Should have variation
        assert np.std(repaired_section) > 0
    
    def test_repair_clipping_full_audio(self):
        """Repair all clipped regions in audio."""
        # Create audio with multiple clips
        audio = np.sin(np.linspace(0, 4 * np.pi, 2000)) * 1.1
        audio = np.clip(audio, -1.0, 1.0)  # Hard clip
        
        # Count original clips
        original_clips = len(detect_clipping_regions(audio))
        assert original_clips > 0
        
        # Repair
        repaired, clips_fixed, samples_fixed = repair_clipping(audio, 44100)
        
        assert clips_fixed > 0
        assert samples_fixed > 0
    
    def test_repair_stereo_audio(self):
        """Repair works on stereo audio."""
        # Create stereo audio with clipping
        left = np.sin(np.linspace(0, 2 * np.pi, 1000))
        right = np.sin(np.linspace(0, 2 * np.pi, 1000))
        left[245:255] = 1.0
        right[745:755] = -1.0
        
        stereo = np.column_stack([left, right])
        
        repaired, clips_fixed, samples_fixed = repair_clipping(stereo, 44100)
        
        assert repaired.shape == stereo.shape
        assert clips_fixed >= 2


class TestClipRepairFile:
    """Test file-level clip repair."""
    
    def test_analyze_clean_file(self, tmp_path):
        """Analyzing a clean file reports no clipping."""
        # Create clean test file
        audio = np.sin(np.linspace(0, 4 * np.pi, 44100)) * 0.5
        test_file = tmp_path / "clean.wav"
        sf.write(test_file, audio, 44100)
        
        result = analyze_clipping(test_file)
        
        assert result.success
        assert result.clip_count == 0
        assert result.needs_repair is False
    
    def test_analyze_clipped_file(self, tmp_path):
        """Analyzing a clipped file detects clipping."""
        # Create clipped test file
        audio = np.sin(np.linspace(0, 4 * np.pi, 44100)) * 1.2
        audio = np.clip(audio, -1.0, 1.0)
        test_file = tmp_path / "clipped.wav"
        sf.write(test_file, audio, 44100)
        
        result = analyze_clipping(test_file)
        
        assert result.success
        assert result.clip_count > 0
        assert result.needs_repair is True
    
    def test_repair_file_dry_run(self, tmp_path):
        """Dry run reports what would be repaired without changing file."""
        # Create clipped test file
        audio = np.sin(np.linspace(0, 4 * np.pi, 44100)) * 1.2
        audio = np.clip(audio, -1.0, 1.0)
        test_file = tmp_path / "clipped.wav"
        sf.write(test_file, audio, 44100)
        
        # Get file content before
        original, _ = sf.read(test_file)
        
        result = repair_file(test_file, dry_run=True)
        
        assert result.success
        assert result.clips_repaired > 0
        
        # File should be unchanged
        after, _ = sf.read(test_file)
        np.testing.assert_array_equal(original, after)
    
    def test_repair_file_apply(self, tmp_path):
        """Apply mode repairs the file."""
        # Create clipped test file
        audio = np.sin(np.linspace(0, 4 * np.pi, 44100)) * 1.2
        audio = np.clip(audio, -1.0, 1.0)
        test_file = tmp_path / "clipped.wav"
        sf.write(test_file, audio, 44100)
        
        result = repair_file(test_file, dry_run=False)
        
        assert result.success
        assert result.clips_repaired > 0
        
        # File should be modified
        after, _ = sf.read(test_file)
        assert not np.array_equal(audio, after)
    
    def test_repair_missing_file(self):
        """Repairing a missing file returns error."""
        result = repair_file(Path("/nonexistent/file.wav"))
        
        assert not result.success
        assert result.error is not None


class TestClipRepairAPI:
    """Test the clip repair API layer."""
    
    def test_api_analyze_mode(self, tmp_path):
        """API analyze mode doesn't modify files."""
        # Create test files
        for i in range(3):
            audio = np.sin(np.linspace(0, 4 * np.pi, 44100)) * 1.2
            audio = np.clip(audio, -1.0, 1.0)
            sf.write(tmp_path / f"test{i}.wav", audio, 44100)
        
        api = ClipRepairAPI()
        request = ClipRepairRequest(
            paths=[tmp_path],
            mode=ClipRepairMode.ANALYZE,
        )
        
        status = api.repair(request)
        
        assert status.total == 3
        assert status.succeeded == 3
        assert status.needed_repair > 0
    
    def test_api_apply_mode(self, tmp_path):
        """API apply mode modifies files."""
        # Create test file
        audio = np.sin(np.linspace(0, 4 * np.pi, 44100)) * 1.2
        audio = np.clip(audio, -1.0, 1.0)
        test_file = tmp_path / "test.wav"
        sf.write(test_file, audio, 44100)
        
        original, _ = sf.read(test_file)
        
        api = ClipRepairAPI()
        request = ClipRepairRequest(
            paths=[test_file],
            mode=ClipRepairMode.APPLY,
        )
        
        status = api.repair(request)
        
        assert status.succeeded == 1
        
        # File should be modified
        after, _ = sf.read(test_file)
        assert not np.array_equal(original, after)
    
    def test_api_empty_directory(self, tmp_path):
        """API handles empty directories gracefully."""
        api = ClipRepairAPI()
        request = ClipRepairRequest(
            paths=[tmp_path],
            mode=ClipRepairMode.ANALYZE,
        )
        
        status = api.repair(request)
        
        assert status.total == 0
        assert status.succeeded == 0
