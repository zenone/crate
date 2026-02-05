"""
Tests for /api/analyze-context endpoint.

Tests the FastAPI endpoint for context analysis.
"""

from fastapi.testclient import TestClient

from web.main import app

client = TestClient(app)


class TestAnalyzeContextEndpoint:
    """Test the analyze-context API endpoint."""

    def test_empty_files(self):
        """Test with no files."""
        response = client.post("/api/analyze-context", json={"files": []})

        assert response.status_code == 200
        data = response.json()
        assert data["contexts"] == []
        assert data["has_multiple_contexts"] is False
        assert data["default_suggestion"] is None

    def test_singles_no_album_tag(self):
        """Test singles detection (no album metadata)."""
        files = [
            {
                "path": f"/test/file{i}.mp3",
                "name": f"file{i}.mp3",
                "size": 1000,
                "is_mp3": True,
                "metadata": {
                    "artist": "Test Artist",
                    "title": f"Track {i}",
                    "album": ""
                }
            }
            for i in range(1, 6)
        ]

        response = client.post("/api/analyze-context", json={"files": files})

        assert response.status_code == 200
        data = response.json()
        assert len(data["contexts"]) == 1
        assert data["contexts"][0]["type"] == "SINGLES"
        assert data["contexts"][0]["confidence"] == 1.0
        assert len(data["contexts"][0]["suggested_templates"]) > 0

    def test_complete_album(self):
        """Test complete album detection."""
        files = [
            {
                "path": f"/test/track{i}.mp3",
                "name": f"track{i}.mp3",
                "size": 1000,
                "is_mp3": True,
                "metadata": {
                    "artist": "Test Artist",
                    "title": f"Track {i}",
                    "album": "Test Album",
                    "track": str(i)
                }
            }
            for i in range(1, 13)
        ]

        response = client.post("/api/analyze-context", json={"files": files})

        assert response.status_code == 200
        data = response.json()
        assert len(data["contexts"]) == 1
        assert data["contexts"][0]["type"] == "ALBUM"
        assert data["contexts"][0]["confidence"] > 0.9
        assert data["contexts"][0]["album_name"] == "Test Album"
        assert data["contexts"][0]["track_range"] == "1-12"
        assert data["has_multiple_contexts"] is False

        # Check default suggestion
        assert data["default_suggestion"] is not None
        assert "{track}" in data["default_suggestion"]["template"]

    def test_mixed_albums(self):
        """Test directory with multiple albums."""
        files = []

        # Album A
        for i in range(1, 4):
            files.append({
                "path": f"/test/album_a_track{i}.mp3",
                "name": f"album_a_track{i}.mp3",
                "size": 1000,
                "is_mp3": True,
                "metadata": {
                    "artist": "Artist A",
                    "title": f"Track {i}",
                    "album": "Album A",
                    "track": str(i)
                }
            })

        # Album B
        for i in range(1, 4):
            files.append({
                "path": f"/test/album_b_track{i}.mp3",
                "name": f"album_b_track{i}.mp3",
                "size": 1000,
                "is_mp3": True,
                "metadata": {
                    "artist": "Artist B",
                    "title": f"Track {i}",
                    "album": "Album B",
                    "track": str(i)
                }
            })

        response = client.post("/api/analyze-context", json={"files": files})

        assert response.status_code == 200
        data = response.json()
        assert len(data["contexts"]) == 2
        assert data["has_multiple_contexts"] is True

        # Both should be detected as albums
        for context in data["contexts"]:
            assert context["type"] == "ALBUM"
            assert context["file_count"] == 3

    def test_partial_album_with_gaps(self):
        """Test album with gaps in track sequence."""
        files = [
            {
                "path": f"/test/track{i}.mp3",
                "name": f"track{i}.mp3",
                "size": 1000,
                "is_mp3": True,
                "metadata": {
                    "artist": "Test Artist",
                    "title": f"Track {i}",
                    "album": "Test Album",
                    "track": str(i)
                }
            }
            for i in [1, 2, 4, 5, 7, 8]
        ]

        response = client.post("/api/analyze-context", json={"files": files})

        assert response.status_code == 200
        data = response.json()
        assert len(data["contexts"]) == 1
        assert data["contexts"][0]["type"] == "PARTIAL_ALBUM"
        assert 0.7 <= data["contexts"][0]["confidence"] <= 0.8
        assert len(data["contexts"][0]["warnings"]) > 0

    def test_template_suggestions_format(self):
        """Test that template suggestions have correct format."""
        files = [
            {
                "path": f"/test/track{i}.mp3",
                "name": f"track{i}.mp3",
                "size": 1000,
                "is_mp3": True,
                "metadata": {
                    "artist": "Test Artist",
                    "title": f"Track {i}",
                    "album": "Test Album",
                    "track": str(i)
                }
            }
            for i in range(1, 6)
        ]

        response = client.post("/api/analyze-context", json={"files": files})

        assert response.status_code == 200
        data = response.json()
        templates = data["contexts"][0]["suggested_templates"]

        assert len(templates) > 0

        for template in templates:
            assert "template" in template
            assert "reason" in template
            assert isinstance(template["template"], str)
            assert isinstance(template["reason"], str)
            assert len(template["template"]) > 0
            assert len(template["reason"]) > 0

    def test_missing_metadata(self):
        """Test files with missing metadata dict."""
        files = [
            {
                "path": "/test/file1.mp3",
                "name": "file1.mp3",
                "size": 1000,
                "is_mp3": True,
                "metadata": None
            },
            {
                "path": "/test/file2.mp3",
                "name": "file2.mp3",
                "size": 1000,
                "is_mp3": True,
                "metadata": {}
            }
        ]

        response = client.post("/api/analyze-context", json={"files": files})

        assert response.status_code == 200
        data = response.json()
        assert len(data["contexts"]) == 1
        assert data["contexts"][0]["type"] == "SINGLES"

    def test_performance_100_files(self):
        """Test performance with 100 files."""
        import time

        files = [
            {
                "path": f"/test/track{i}.mp3",
                "name": f"track{i}.mp3",
                "size": 1000,
                "is_mp3": True,
                "metadata": {
                    "artist": "Test Artist",
                    "title": f"Track {i}",
                    "album": "",
                    "track": None
                }
            }
            for i in range(1, 101)
        ]

        start = time.time()
        response = client.post("/api/analyze-context", json={"files": files})
        duration = time.time() - start

        assert response.status_code == 200
        # Should complete in reasonable time (< 1 second for API call)
        assert duration < 1.0, f"Took {duration*1000:.1f}ms (target: <1000ms)"
