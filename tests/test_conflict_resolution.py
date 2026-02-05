"""
Tests for metadata conflict resolution.
"""

from crate.core.conflict_resolution import (
    compare_bpm_values,
    compare_key_values,
    resolve_metadata_conflict,
    should_use_musicbrainz_value,
)


class TestBPMComparison:
    """Test BPM conflict detection."""

    def test_bpm_match(self):
        """Identical BPM values should match."""
        result = compare_bpm_values("128", "128")
        assert result["matches"] is True
        assert result["difference_percent"] == 0

    def test_bpm_small_difference(self):
        """Small BPM differences should be flagged."""
        result = compare_bpm_values("128", "127")
        assert result["matches"] is False
        assert 0 < result["difference_percent"] < 2

    def test_bpm_large_difference(self):
        """Large BPM differences should be flagged."""
        result = compare_bpm_values("128", "140")
        assert result["matches"] is False
        assert result["difference_percent"] > 5

    def test_bpm_double_tempo(self):
        """Double tempo detection (128 vs 64)."""
        result = compare_bpm_values("128", "64")
        assert result["matches"] is False
        assert result["possible_double_tempo"] is True

    def test_bpm_half_tempo(self):
        """Half tempo detection (64 vs 128)."""
        result = compare_bpm_values("64", "128")
        assert result["matches"] is False
        assert result["possible_half_tempo"] is True


class TestKeyComparison:
    """Test musical key conflict detection."""

    def test_key_match(self):
        """Identical keys should match."""
        result = compare_key_values("C maj", "C maj")
        assert result["matches"] is True

    def test_key_different(self):
        """Different keys should not match."""
        result = compare_key_values("C maj", "C min")
        assert result["matches"] is False

    def test_key_enharmonic(self):
        """Enharmonic equivalents should match."""
        result = compare_key_values("C# maj", "Db maj")
        assert result["matches"] is True
        assert result["enharmonic"] is True


class TestConflictResolution:
    """Test overall conflict resolution logic."""

    def test_resolve_with_tags_only(self):
        """Tags only, no conflict."""
        result = resolve_metadata_conflict(
            field="bpm",
            tag_value="128",
            mb_value=None,
            ai_value=None,
            mb_confidence=0.0
        )
        assert result["final_value"] == "128"
        assert result["source"] == "Tags"
        assert result["conflicts"] == []

    def test_resolve_tag_vs_ai_match(self):
        """Tags and AI agree."""
        result = resolve_metadata_conflict(
            field="bpm",
            tag_value="128",
            mb_value=None,
            ai_value="128",
            mb_confidence=0.0
        )
        assert result["final_value"] == "128"
        assert result["source"] == "Tags"
        assert result["validated_by"] == "AI Audio"

    def test_resolve_tag_vs_ai_conflict(self):
        """Tags and AI disagree."""
        result = resolve_metadata_conflict(
            field="bpm",
            tag_value="128",
            mb_value=None,
            ai_value="126",
            mb_confidence=0.0
        )
        assert result["final_value"] == "128"  # Trust tags by default
        assert result["source"] == "Tags"
        assert len(result["conflicts"]) > 0
        assert result["conflicts"][0]["disagreement"] == "AI Audio suggests: 126"

    def test_resolve_mb_high_confidence_overrides(self):
        """MusicBrainz with high confidence overrides bad tags."""
        result = resolve_metadata_conflict(
            field="artist",
            tag_value="Unknown",
            mb_value="Daft Punk",
            ai_value=None,
            mb_confidence=0.95
        )
        assert result["final_value"] == "Daft Punk"
        assert result["source"] == "MusicBrainz"
        assert result["overridden"] == "Tags (Unknown) replaced by high-confidence match"

    def test_resolve_mb_low_confidence_ignored(self):
        """MusicBrainz with low confidence should not override."""
        result = resolve_metadata_conflict(
            field="artist",
            tag_value="Artist Name",
            mb_value="Different Artist",
            ai_value=None,
            mb_confidence=0.50
        )
        assert result["final_value"] == "Artist Name"
        assert result["source"] == "Tags"


class TestMusicBrainzDecision:
    """Test MusicBrainz value usage decision logic."""

    def test_use_mb_high_confidence_missing_tags(self):
        """Use MB when tags missing and confidence high."""
        assert should_use_musicbrainz_value(
            tag_value="",
            mb_value="Daft Punk",
            mb_confidence=0.90
        ) is True

    def test_use_mb_high_confidence_unknown_tags(self):
        """Use MB when tags say 'Unknown' and confidence high."""
        assert should_use_musicbrainz_value(
            tag_value="Unknown Artist",
            mb_value="Daft Punk",
            mb_confidence=0.95
        ) is True

    def test_dont_use_mb_low_confidence(self):
        """Don't use MB when confidence low."""
        assert should_use_musicbrainz_value(
            tag_value="Artist Name",
            mb_value="Different Artist",
            mb_confidence=0.50
        ) is False

    def test_dont_use_mb_good_tags(self):
        """Don't use MB when tags are already good."""
        assert should_use_musicbrainz_value(
            tag_value="Daft Punk",
            mb_value="Daft Punk",
            mb_confidence=0.95
        ) is False  # No need to override if they match
