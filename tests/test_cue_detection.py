"""
Tests for cue detection module.

TDD approach: These tests define expected behavior.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from crate.api.cue_detection import (
    REKORDBOX_COLORS,
    CueDetectionAPI,
    CueDetectionRequest,
    CueDetectionResult,
    CuePoint,
    CueType,
)


class TestCueDetectionModels:
    """Test data models."""

    def test_cue_type_enum(self):
        """CueType has expected values."""
        assert CueType.INTRO.value == "intro"
        assert CueType.DROP.value == "drop"
        assert CueType.BREAKDOWN.value == "breakdown"
        assert CueType.BUILD.value == "build"
        assert CueType.OUTRO.value == "outro"
        assert CueType.MEMORY.value == "memory"

    def test_cue_point_creation(self):
        """CuePoint can be created with all attributes."""
        cue = CuePoint(
            position_ms=30000,
            cue_type=CueType.DROP,
            confidence=0.85,
            label="Drop 1",
            color=0xE81414,
            hot_cue_index=1
        )

        assert cue.position_ms == 30000
        assert cue.cue_type == CueType.DROP
        assert cue.confidence == 0.85
        assert cue.label == "Drop 1"
        assert cue.hot_cue_index == 1

    def test_cue_point_defaults(self):
        """CuePoint has sensible defaults."""
        cue = CuePoint(
            position_ms=0,
            cue_type=CueType.INTRO
        )

        assert cue.confidence == 1.0
        assert cue.label is None
        assert cue.color is None
        assert cue.hot_cue_index is None

    def test_cue_detection_request_defaults(self):
        """CueDetectionRequest has sensible defaults."""
        request = CueDetectionRequest(paths=[Path("test.mp3")])

        assert request.detect_intro is True
        assert request.detect_drops is True
        assert request.detect_breakdowns is True
        assert request.max_cues == 8
        assert request.sensitivity == 0.5
        assert request.recursive is False

    def test_rekordbox_colors_defined(self):
        """Rekordbox colors are defined for all cue types."""
        assert CueType.INTRO in REKORDBOX_COLORS
        assert CueType.DROP in REKORDBOX_COLORS
        assert CueType.BREAKDOWN in REKORDBOX_COLORS
        assert CueType.BUILD in REKORDBOX_COLORS
        assert CueType.OUTRO in REKORDBOX_COLORS


class TestCueDetectionCore:
    """Test core cue detection functions."""

    def test_detect_first_beat_returns_cue(self):
        """detect_first_beat returns a CuePoint."""
        from crate.core.cue_detection import detect_first_beat

        logger = Mock()
        test_file = Path("tests/fixtures/test_track.mp3")
        if not test_file.exists():
            pytest.skip("No test fixture available")

        cue = detect_first_beat(test_file, logger)

        assert cue is not None
        assert isinstance(cue, CuePoint)
        assert cue.cue_type == CueType.INTRO
        assert cue.position_ms >= 0

    def test_detect_energy_peaks_returns_list(self):
        """detect_energy_peaks returns list of CuePoints."""
        from crate.core.cue_detection import detect_energy_peaks

        logger = Mock()
        test_file = Path("tests/fixtures/test_track.mp3")
        if not test_file.exists():
            pytest.skip("No test fixture available")

        peaks = detect_energy_peaks(test_file, logger, sensitivity=0.5)

        assert isinstance(peaks, list)
        for peak in peaks:
            assert isinstance(peak, CuePoint)
            assert peak.cue_type == CueType.DROP

    def test_detect_energy_dips_returns_list(self):
        """detect_energy_dips returns list of CuePoints."""
        from crate.core.cue_detection import detect_energy_dips

        logger = Mock()
        test_file = Path("tests/fixtures/test_track.mp3")
        if not test_file.exists():
            pytest.skip("No test fixture available")

        dips = detect_energy_dips(test_file, logger, sensitivity=0.5)

        assert isinstance(dips, list)
        for dip in dips:
            assert isinstance(dip, CuePoint)
            assert dip.cue_type == CueType.BREAKDOWN

    def test_assign_hot_cue_slots_limits_count(self):
        """assign_hot_cue_slots limits to max_cues."""
        from crate.core.cue_detection import assign_hot_cue_slots

        # Create 10 cues
        cues = [
            CuePoint(position_ms=i * 10000, cue_type=CueType.DROP)
            for i in range(10)
        ]

        # Limit to 8
        result = assign_hot_cue_slots(cues, max_cues=8)

        assert len(result) == 8
        # Should have hot cue indices 0-7
        indices = [c.hot_cue_index for c in result]
        assert sorted(indices) == list(range(8))

    def test_assign_hot_cue_slots_preserves_order(self):
        """assign_hot_cue_slots assigns slots in position order."""
        from crate.core.cue_detection import assign_hot_cue_slots

        cues = [
            CuePoint(position_ms=30000, cue_type=CueType.DROP),
            CuePoint(position_ms=10000, cue_type=CueType.INTRO),
            CuePoint(position_ms=60000, cue_type=CueType.BREAKDOWN),
        ]

        result = assign_hot_cue_slots(cues, max_cues=8)

        # Should be sorted by position
        positions = [c.position_ms for c in result]
        assert positions == sorted(positions)

        # First cue (earliest) should be hot cue 0
        assert result[0].position_ms == 10000
        assert result[0].hot_cue_index == 0

    def test_get_audio_duration(self):
        """get_audio_duration returns duration in ms."""
        from crate.core.cue_detection import get_audio_duration

        logger = Mock()
        test_file = Path("tests/fixtures/test_track.mp3")
        if not test_file.exists():
            pytest.skip("No test fixture available")

        duration = get_audio_duration(test_file, logger)

        assert isinstance(duration, int)
        assert duration > 0

    def test_collect_audio_files(self):
        """collect_audio_files finds audio files."""
        from crate.core.cue_detection import collect_audio_files

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "track.mp3").touch()
            (Path(tmpdir) / "track.wav").touch()
            (Path(tmpdir) / "cover.jpg").touch()

            files = collect_audio_files([Path(tmpdir)], recursive=False)

            assert len(files) == 2
            extensions = {f.suffix for f in files}
            assert extensions == {".mp3", ".wav"}


class TestRekordboxExport:
    """Test Rekordbox XML export."""

    def test_write_rekordbox_xml_creates_file(self):
        """write_rekordbox_xml creates valid XML file."""
        from crate.core.cue_detection import write_rekordbox_xml

        results = [
            CueDetectionResult(
                path=Path("/music/track.mp3"),
                success=True,
                cues=[
                    CuePoint(
                        position_ms=0,
                        cue_type=CueType.INTRO,
                        hot_cue_index=0,
                        color=0x28E214
                    ),
                    CuePoint(
                        position_ms=30000,
                        cue_type=CueType.DROP,
                        hot_cue_index=1,
                        color=0xE81414
                    ),
                ],
                duration_ms=180000,
                bpm=128.0
            )
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "export.xml"
            logger = Mock()

            write_rekordbox_xml(results, output_path, logger)

            assert output_path.exists()
            content = output_path.read_text()

            # Check XML structure
            assert '<?xml' in content
            assert 'DJ_PLAYLISTS' in content or 'COLLECTION' in content
            assert 'track.mp3' in content

    def test_rekordbox_xml_cue_format(self):
        """Rekordbox XML has correct cue point format."""
        from crate.core.cue_detection import write_rekordbox_xml

        results = [
            CueDetectionResult(
                path=Path("/music/track.mp3"),
                success=True,
                cues=[
                    CuePoint(
                        position_ms=15000,  # 15 seconds
                        cue_type=CueType.DROP,
                        hot_cue_index=0,
                        color=0xE81414
                    ),
                ],
                duration_ms=180000,
                bpm=128.0
            )
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "export.xml"
            logger = Mock()

            write_rekordbox_xml(results, output_path, logger)

            content = output_path.read_text()

            # Rekordbox uses milliseconds for position
            assert '15000' in content or 'Start="15' in content


class TestCueDetectionAPI:
    """Test the CueDetectionAPI class."""

    def test_api_initialization(self):
        """API initializes with optional logger."""
        api = CueDetectionAPI()
        assert api.logger is not None

        custom_logger = Mock()
        api2 = CueDetectionAPI(logger=custom_logger)
        assert api2.logger is custom_logger

    @patch('crate.api.cue_detection.CueDetectionAPI._process_file')
    @patch('crate.core.cue_detection.collect_audio_files')
    def test_api_detect_processes_files(self, mock_collect, mock_process):
        """API.detect processes each file."""
        mock_collect.return_value = [Path("a.mp3"), Path("b.mp3")]
        mock_process.return_value = CueDetectionResult(
            path=Path("test.mp3"),
            success=True,
            cues=[CuePoint(position_ms=0, cue_type=CueType.INTRO)]
        )

        api = CueDetectionAPI()
        request = CueDetectionRequest(paths=[Path(".")])
        status = api.detect(request)

        assert status.total == 2
        assert status.processed == 2
        assert status.succeeded == 2

    @patch('crate.core.cue_detection.write_rekordbox_xml')
    def test_api_export_rekordbox(self, mock_write):
        """API.export_rekordbox calls write function."""
        api = CueDetectionAPI()
        results = [
            CueDetectionResult(
                path=Path("track.mp3"),
                success=True,
                cues=[]
            )
        ]

        success = api.export_rekordbox(results, Path("export.xml"))

        assert success is True
        mock_write.assert_called_once()


class TestCueDetectionIntegration:
    """Integration tests with real audio files."""

    @pytest.fixture
    def smoke_test_dir(self):
        """Get the canonical smoke test directory."""
        path = Path.home() / "Music" / "DJ" / "CrateSmokeTest"
        if not path.exists():
            pytest.skip("Smoke test directory not available")
        return path

    @pytest.fixture
    def test_file(self, smoke_test_dir):
        """Get a test MP3 file."""
        mp3_files = list(smoke_test_dir.glob("*.mp3"))
        if not mp3_files:
            pytest.skip("No MP3 files in smoke test directory")
        return mp3_files[0]

    def test_detect_cues_real_file(self, test_file):
        """Can detect cues in a real MP3 file."""
        api = CueDetectionAPI()
        request = CueDetectionRequest(paths=[test_file])

        status = api.detect(request)

        assert status.total == 1
        assert status.succeeded == 1

        result = status.results[0]
        assert result.success is True
        assert len(result.cues) > 0  # Should detect at least intro
        assert result.duration_ms is not None
        assert result.duration_ms > 0

    def test_export_and_verify_xml(self, test_file):
        """Can export cues to Rekordbox XML."""
        api = CueDetectionAPI()
        request = CueDetectionRequest(paths=[test_file])
        status = api.detect(request)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "export.xml"
            success = api.export_rekordbox(status.results, output_path)

            assert success is True
            assert output_path.exists()

            # Verify XML is parseable
            import xml.etree.ElementTree as ET
            tree = ET.parse(output_path)
            root = tree.getroot()
            assert root is not None
