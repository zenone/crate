"""
Tests for context detection module.

Tests album vs singles classification, track number extraction,
sequential detection, and confidence scoring.
"""

from crate.core.context_detection import (
    ContextType,
    analyze_context,
    extract_track_number,
    get_default_suggestion,
    is_sequential,
)


class TestTrackNumberExtraction:
    """Test track number extraction from various formats."""

    def test_simple_number(self):
        """Test simple numeric strings."""
        assert extract_track_number("1") == 1
        assert extract_track_number("5") == 5
        assert extract_track_number("12") == 12

    def test_zero_padded(self):
        """Test zero-padded track numbers."""
        assert extract_track_number("01") == 1
        assert extract_track_number("05") == 5
        assert extract_track_number("12") == 12

    def test_slash_format(self):
        """Test '1/12' format (track/total)."""
        assert extract_track_number("1/12") == 1
        assert extract_track_number("5/12") == 5
        assert extract_track_number("12/12") == 12

    def test_zero_padded_slash(self):
        """Test '01/12' format."""
        assert extract_track_number("01/12") == 1
        assert extract_track_number("05/12") == 5

    def test_invalid_formats(self):
        """Test non-numeric or empty strings."""
        assert extract_track_number("A") is None
        assert extract_track_number("B") is None
        assert extract_track_number("") is None
        assert extract_track_number(None) is None

    def test_with_whitespace(self):
        """Test strings with whitespace."""
        assert extract_track_number(" 1 ") == 1
        assert extract_track_number(" 01/12 ") == 1


class TestSequentialDetection:
    """Test sequential track number detection."""

    def test_perfect_sequence(self):
        """Test perfectly sequential tracks."""
        assert is_sequential([1, 2, 3, 4, 5], allow_gaps=False) is True
        assert is_sequential([1, 2, 3], allow_gaps=False) is True

    def test_perfect_sequence_unsorted_input(self):
        """Test sequential detection with unsorted input."""
        assert is_sequential([3, 1, 2, 5, 4], allow_gaps=False) is True

    def test_sequence_with_gaps_strict(self):
        """Test that gaps fail strict sequential check."""
        assert is_sequential([1, 2, 4, 5], allow_gaps=False) is False
        assert is_sequential([1, 3, 5], allow_gaps=False) is False

    def test_sequence_with_gaps_loose(self):
        """Test that gaps pass loose sequential check."""
        assert is_sequential([1, 2, 4, 5], allow_gaps=True) is True
        assert is_sequential([1, 3, 5, 7], allow_gaps=True) is True

    def test_not_starting_at_one(self):
        """Test sequences not starting at 1."""
        assert is_sequential([2, 3, 4], allow_gaps=False) is False
        assert is_sequential([5, 6, 7], allow_gaps=True) is True  # Loose allows higher start

    def test_empty_list(self):
        """Test empty track list."""
        assert is_sequential([], allow_gaps=False) is False
        assert is_sequential([], allow_gaps=True) is False

    def test_single_track(self):
        """Test single track."""
        assert is_sequential([1], allow_gaps=False) is True
        assert is_sequential([5], allow_gaps=True) is True  # Loose is lenient


class TestAlbumDetection:
    """Test album vs singles classification."""

    def create_file(self, album="", track=None, artist="Test Artist", title="Test Song"):
        """Helper to create test file dict."""
        return {
            "path": f"/test/{title}.mp3",
            "name": f"{title}.mp3",
            "metadata": {
                "album": album,
                "track": track,
                "artist": artist,
                "title": title
            }
        }

    def test_complete_album(self):
        """Test album with complete sequential tracks."""
        files = [
            self.create_file(album="Test Album", track=str(i), title=f"Track {i}")
            for i in range(1, 13)
        ]

        result = analyze_context(files)

        assert len(result) == 1
        context = result[0]
        assert context.type == ContextType.ALBUM
        assert context.confidence > 0.9
        assert context.album_name == "Test Album"
        assert context.file_count == 12
        assert context.track_range == "1-12"
        assert len(context.suggested_templates) > 0
        assert "{track}" in context.suggested_templates[0].template

    def test_singles_no_album_tag(self):
        """Test files with no album metadata."""
        files = [
            self.create_file(album="", track=None, title=f"Single {i}")
            for i in range(1, 6)
        ]

        result = analyze_context(files)

        assert len(result) == 1
        context = result[0]
        assert context.type == ContextType.SINGLES
        assert context.confidence == 1.0
        assert context.album_name is None

    def test_album_too_few_files(self):
        """Test album with only 2 files (< 3 minimum)."""
        files = [
            self.create_file(album="Test Album", track="1", title="Track 1"),
            self.create_file(album="Test Album", track="2", title="Track 2")
        ]

        result = analyze_context(files)

        assert len(result) == 1
        context = result[0]
        assert context.type == ContextType.SINGLES
        assert context.file_count == 2
        assert len(context.warnings) > 0

    def test_partial_album_with_gaps(self):
        """Test album with gaps in track sequence."""
        files = [
            self.create_file(album="Test Album", track=str(i), title=f"Track {i}")
            for i in [1, 2, 4, 5, 7, 8]
        ]

        result = analyze_context(files)

        assert len(result) == 1
        context = result[0]
        assert context.type == ContextType.PARTIAL_ALBUM
        assert 0.7 <= context.confidence <= 0.8
        assert "gap" in context.warnings[0].lower()

    def test_incomplete_album_missing_tracks(self):
        """Test album with 30%+ missing track numbers."""
        files = [
            self.create_file(album="Test Album", track="1", title="Track 1"),
            self.create_file(album="Test Album", track="2", title="Track 2"),
            self.create_file(album="Test Album", track=None, title="Track 3"),
            self.create_file(album="Test Album", track=None, title="Track 4"),
            self.create_file(album="Test Album", track=None, title="Track 5")
        ]

        result = analyze_context(files)

        assert len(result) == 1
        context = result[0]
        assert context.type == ContextType.INCOMPLETE_ALBUM
        assert context.confidence < 0.6
        assert "track numbers" in context.warnings[0].lower()

    def test_mixed_albums(self):
        """Test directory with 2 different albums."""
        files = [
            self.create_file(album="Album A", track="1", title="A Track 1"),
            self.create_file(album="Album A", track="2", title="A Track 2"),
            self.create_file(album="Album A", track="3", title="A Track 3"),
            self.create_file(album="Album B", track="1", title="B Track 1"),
            self.create_file(album="Album B", track="2", title="B Track 2"),
            self.create_file(album="Album B", track="3", title="B Track 3")
        ]

        result = analyze_context(files)

        assert len(result) == 2
        # Both should be detected as albums
        for context in result:
            assert context.type == ContextType.ALBUM
            assert context.file_count == 3

    def test_track_format_variations(self):
        """Test various track number formats (1, 01, 1/12)."""
        files = [
            self.create_file(album="Test Album", track="1", title="Track 1"),
            self.create_file(album="Test Album", track="02", title="Track 2"),
            self.create_file(album="Test Album", track="3/12", title="Track 3")
        ]

        result = analyze_context(files)

        assert len(result) == 1
        context = result[0]
        assert context.type == ContextType.ALBUM
        assert context.track_range == "1-3"

    def test_no_files(self):
        """Test empty file list."""
        result = analyze_context([])
        assert result == []

    def test_non_sequential_tracks(self):
        """Test album with non-sequential track numbers."""
        files = [
            self.create_file(album="Test Album", track="5", title="Track 5"),
            self.create_file(album="Test Album", track="8", title="Track 8"),
            self.create_file(album="Test Album", track="12", title="Track 12")
        ]

        result = analyze_context(files)

        assert len(result) == 1
        context = result[0]
        # Should be treated as singles or partial
        assert context.type in [ContextType.SINGLES, ContextType.PARTIAL_ALBUM]


class TestDefaultSuggestion:
    """Test default suggestion selection."""

    def test_single_context(self):
        """Test getting default from single context."""
        from crate.core.context_detection import ContextAnalysis, TemplateSuggestion

        contexts = [
            ContextAnalysis(
                type=ContextType.ALBUM,
                confidence=0.95,
                album_name="Test Album",
                file_count=12,
                track_range="1-12",
                suggested_templates=[
                    TemplateSuggestion(
                        template="{track} - {artist} - {title}",
                        reason="Test reason",
                        preset_id="simple-album"
                    )
                ]
            )
        ]

        result = get_default_suggestion(contexts)

        assert result is not None
        assert result["template"] == "{track} - {artist} - {title}"
        assert result["confidence"] == 0.95

    def test_multiple_contexts_picks_highest_confidence(self):
        """Test that highest confidence context is selected."""
        from crate.core.context_detection import ContextAnalysis, TemplateSuggestion

        contexts = [
            ContextAnalysis(
                type=ContextType.PARTIAL_ALBUM,
                confidence=0.7,
                album_name="Album A",
                file_count=5,
                track_range="1-5",
                suggested_templates=[
                    TemplateSuggestion(
                        template="{artist} - {title}",
                        reason="Low confidence",
                        preset_id="simple"
                    )
                ]
            ),
            ContextAnalysis(
                type=ContextType.ALBUM,
                confidence=0.95,
                album_name="Album B",
                file_count=12,
                track_range="1-12",
                suggested_templates=[
                    TemplateSuggestion(
                        template="{track} - {artist} - {title}",
                        reason="High confidence",
                        preset_id="simple-album"
                    )
                ]
            )
        ]

        result = get_default_suggestion(contexts)

        assert result is not None
        assert result["confidence"] == 0.95
        assert result["template"] == "{track} - {artist} - {title}"

    def test_empty_contexts(self):
        """Test with no contexts."""
        result = get_default_suggestion([])
        assert result is None


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def create_file(self, album="", track=None, artist="Test Artist", title="Test Song"):
        """Helper to create test file dict."""
        return {
            "path": f"/test/{title}.mp3",
            "name": f"{title}.mp3",
            "metadata": {
                "album": album,
                "track": track,
                "artist": artist,
                "title": title
            }
        }

    def test_missing_metadata(self):
        """Test files with missing metadata dict."""
        files = [
            {"path": "/test/file1.mp3", "name": "file1.mp3"},
            {"path": "/test/file2.mp3", "name": "file2.mp3"}
        ]

        result = analyze_context(files)

        assert len(result) == 1
        assert result[0].type == ContextType.SINGLES

    def test_album_no_track_numbers(self):
        """Test album tag present but no track numbers at all."""
        files = [
            self.create_file(album="Test Album", track=None, title=f"Track {i}")
            for i in range(1, 6)
        ]

        result = analyze_context(files)

        assert len(result) == 1
        context = result[0]
        assert context.type == ContextType.INCOMPLETE_ALBUM
        assert "No track numbers found" in context.warnings

    def test_duplicate_track_numbers(self):
        """Test album with duplicate track numbers."""
        files = [
            self.create_file(album="Test Album", track="1", title="Track 1a"),
            self.create_file(album="Test Album", track="1", title="Track 1b"),
            self.create_file(album="Test Album", track="2", title="Track 2")
        ]

        result = analyze_context(files)

        assert len(result) == 1
        # Should still detect as album, duplicates are just in the sequence
        assert result[0].file_count == 3

    def test_large_track_numbers(self):
        """Test tracks starting at high numbers (not typical album)."""
        files = [
            self.create_file(album="Test Album", track=str(i), title=f"Track {i}")
            for i in range(50, 53)
        ]

        result = analyze_context(files)

        assert len(result) == 1
        # Should not be strict sequential (doesn't start at 1)
        context = result[0]
        assert context.type != ContextType.ALBUM or context.confidence < 0.9


class TestPerformance:
    """Test performance with large file sets."""

    def create_file(self, album="", track=None, title="Test Song"):
        """Helper to create test file dict."""
        return {
            "path": f"/test/{title}.mp3",
            "name": f"{title}.mp3",
            "metadata": {
                "album": album,
                "track": track,
                "artist": "Test Artist",
                "title": title
            }
        }

    def test_1000_files(self):
        """Test that 1000 files complete in reasonable time."""
        import time

        # Create 1000 singles (worst case for grouping)
        files = [
            self.create_file(album="", track=None, title=f"Single {i}")
            for i in range(1000)
        ]

        start = time.time()
        result = analyze_context(files)
        duration = time.time() - start

        assert len(result) == 1
        assert result[0].type == ContextType.SINGLES
        # Should complete in < 100ms (design requirement)
        assert duration < 0.1, f"Took {duration*1000:.1f}ms (target: <100ms)"

    def test_100_albums(self):
        """Test with 100 different albums (complex grouping)."""
        import time

        files = []
        for album_idx in range(100):
            for track_idx in range(1, 6):  # 5 tracks per album
                files.append(
                    self.create_file(
                        album=f"Album {album_idx}",
                        track=str(track_idx),
                        title=f"Album {album_idx} Track {track_idx}"
                    )
                )

        start = time.time()
        result = analyze_context(files)
        duration = time.time() - start

        assert len(result) == 100
        # Should still complete quickly
        assert duration < 0.2, f"Took {duration*1000:.1f}ms (target: <200ms)"
