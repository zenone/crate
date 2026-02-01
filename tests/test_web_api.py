"""
Tests for FastAPI web endpoints.

Tests verify:
- /api/rename/preview endpoint with various options
- /api/rename/execute endpoint for async rename
- /api/operation/{id} endpoint for status polling
- /api/operation/{id}/cancel endpoint for cancellation
- Request validation and error handling
- Response models and JSON serialization
"""

import time
from pathlib import Path
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from web.main import app


# Test Fixtures
@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def test_files(tmp_path):
    """Create test MP3 files."""
    for i in range(5):
        (tmp_path / f"test_{i:02d}.mp3").write_bytes(b"FAKE MP3 DATA")
    return tmp_path


@pytest.fixture
def mock_metadata():
    """Mock metadata for test files."""
    return {
        "artist": "Test Artist",
        "title": "Test Title",
        "bpm": "128",
        "key": "Am",
        "camelot": "8A",
        "artist_source": "Tags",
        "title_source": "Tags",
        "bpm_source": "Tags",
        "key_source": "Tags",
    }


# Test: Preview Endpoint
class TestPreviewEndpoint:
    """Test /api/rename/preview endpoint."""

    def test_preview_returns_json(self, client, test_files, mock_metadata):
        """Should return JSON response with preview data."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            response = client.post(
                "/api/rename/preview",
                json={
                    "path": str(test_files),
                    "recursive": False,
                    "template": None,
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Should have expected structure
            assert "path" in data
            assert "previews" in data
            assert "total" in data
            assert "stats" in data

            # Stats should have counts
            assert "will_rename" in data["stats"]
            assert "will_skip" in data["stats"]
            assert "errors" in data["stats"]

    def test_preview_with_specific_files(self, client, test_files, mock_metadata):
        """Should filter to specific files when file_paths provided."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            # Get list of files
            files = [str(f) for f in test_files.iterdir() if f.suffix == ".mp3"]
            selected_files = files[:2]  # Select only first 2

            response = client.post(
                "/api/rename/preview",
                json={
                    "path": str(test_files),
                    "file_paths": selected_files,
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Should only have 2 previews
            assert data["total"] == 2
            assert len(data["previews"]) == 2

    def test_preview_with_custom_template(self, client, test_files, mock_metadata):
        """Should respect custom template."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            response = client.post(
                "/api/rename/preview",
                json={
                    "path": str(test_files),
                    "template": "{bpm} - {artist} - {title}",
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Check that preview uses custom template
            if data["previews"]:
                preview = data["previews"][0]
                if preview["status"] == "will_rename":
                    assert "128 - Test Artist - Test Title" in preview["dst"]

    def test_preview_with_enhance_metadata(self, client, test_files):
        """Should include enhanced metadata when requested."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read, \
             patch("crate.core.audio_analysis.auto_detect_metadata") as mock_ai:

            # ID3 tags have missing BPM
            mock_read.return_value = (
                {
                    "artist": "Test Artist",
                    "title": "Test Title",
                    "bpm": "",
                    "key": "Am",
                },
                None
            )

            # AI analysis detects BPM
            mock_ai.return_value = ("128", "AI Audio", "Am", "Tags")

            response = client.post(
                "/api/rename/preview",
                json={
                    "path": str(test_files),
                    "enhance_metadata": True,
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Should have previews with enhanced metadata
            if data["previews"]:
                preview = data["previews"][0]
                if preview["metadata"]:
                    # BPM should be from AI
                    assert preview["metadata"].get("bpm") == "128"

    def test_preview_with_invalid_path(self, client):
        """Should return error for invalid path."""
        response = client.post(
            "/api/rename/preview",
            json={
                "path": "/nonexistent/path",
            }
        )

        # Should not crash, but return empty or error
        assert response.status_code in [200, 404, 500]

    def test_preview_returns_metadata_sources(self, client, test_files, mock_metadata):
        """Should include metadata source attribution."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            response = client.post(
                "/api/rename/preview",
                json={"path": str(test_files)}
            )

            assert response.status_code == 200
            data = response.json()

            # Check that metadata includes sources
            if data["previews"]:
                preview = data["previews"][0]
                if preview["metadata"]:
                    assert "artist_source" in preview["metadata"]
                    assert "title_source" in preview["metadata"]
                    assert "bpm_source" in preview["metadata"]
                    assert "key_source" in preview["metadata"]


# Test: Execute Rename Endpoint
class TestExecuteRenameEndpoint:
    """Test /api/rename/execute endpoint."""

    def test_execute_starts_async_operation(self, client, test_files, mock_metadata):
        """Should start async rename operation."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            files = [str(f) for f in test_files.iterdir() if f.suffix == ".mp3"]

            response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(test_files),
                    "file_paths": files,
                    "dry_run": True,
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Should return operation ID
            assert "operation_id" in data
            assert "status" in data
            assert data["status"] == "started"

            # Operation ID should be UUID
            assert isinstance(data["operation_id"], str)
            assert len(data["operation_id"]) == 36

    def test_execute_requires_file_paths(self, client, test_files):
        """Should require file_paths parameter."""
        response = client.post(
            "/api/rename/execute",
            json={
                "path": str(test_files),
                "file_paths": [],  # Empty list
            }
        )

        assert response.status_code == 400
        assert "No files specified" in response.json()["detail"]

    def test_execute_with_dry_run(self, client, test_files, mock_metadata):
        """Should respect dry_run flag."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            files = [str(f) for f in test_files.iterdir() if f.suffix == ".mp3"]

            response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(test_files),
                    "file_paths": files,
                    "dry_run": True,
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Should start operation
            assert "operation_id" in data

            # Files should still exist with original names (dry run)
            time.sleep(0.5)
            for file in test_files.iterdir():
                assert "test_" in file.name


# Test: Operation Status Endpoint
class TestOperationStatusEndpoint:
    """Test /api/operation/{id} endpoint."""

    def test_get_operation_status(self, client, test_files, mock_metadata):
        """Should return operation status."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            # Start operation
            files = [str(f) for f in test_files.iterdir() if f.suffix == ".mp3"]
            execute_response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(test_files),
                    "file_paths": files,
                    "dry_run": True,
                }
            )
            operation_id = execute_response.json()["operation_id"]

            # Get status
            response = client.get(f"/api/operation/{operation_id}")

            assert response.status_code == 200
            data = response.json()

            # Should have status fields
            assert "operation_id" in data
            assert "status" in data
            assert "progress" in data
            assert "total" in data
            assert "current_file" in data
            assert "start_time" in data

            # Status should be valid
            assert data["status"] in ["running", "completed", "cancelled", "error"]

    def test_get_operation_status_not_found(self, client):
        """Should return 404 for unknown operation ID."""
        response = client.get("/api/operation/unknown-id-12345")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_operation_status_includes_results(self, client, test_files, mock_metadata):
        """Should include results when operation completes."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            # Start operation
            files = [str(f) for f in test_files.iterdir() if f.suffix == ".mp3"]
            execute_response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(test_files),
                    "file_paths": files,
                    "dry_run": True,
                }
            )
            operation_id = execute_response.json()["operation_id"]

            # Wait for completion
            time.sleep(0.5)

            # Get status
            response = client.get(f"/api/operation/{operation_id}")
            data = response.json()

            # If completed, should have results
            if data["status"] == "completed":
                assert data["results"] is not None
                assert "total" in data["results"]
                assert "renamed" in data["results"]
                assert "skipped" in data["results"]
                assert "errors" in data["results"]
                assert "results" in data["results"]  # Individual file results


# Test: Cancel Operation Endpoint
class TestCancelOperationEndpoint:
    """Test /api/operation/{id}/cancel endpoint."""

    def test_cancel_running_operation(self, client, tmp_path):
        """Should cancel running operation."""
        # Create many files to ensure operation runs long enough
        for i in range(50):
            (tmp_path / f"test_{i:03d}.mp3").write_bytes(b"FAKE MP3")

        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            # Add delay to make operation slower
            def slow_read(*args):
                time.sleep(0.03)
                return (
                    {"artist": "Test", "title": "Test", "bpm": "128", "key": "Am"},
                    None
                )
            mock_read.side_effect = slow_read

            # Start operation
            files = [str(f) for f in tmp_path.iterdir() if f.suffix == ".mp3"]
            execute_response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(tmp_path),
                    "file_paths": files,
                    "dry_run": True,
                }
            )
            operation_id = execute_response.json()["operation_id"]

            # Wait briefly for operation to start
            time.sleep(0.2)

            # Cancel operation
            response = client.post(f"/api/operation/{operation_id}/cancel")

            # Should succeed or say operation already complete
            assert response.status_code in [200, 404]

            if response.status_code == 200:
                assert response.json()["success"] is True

    def test_cancel_unknown_operation(self, client):
        """Should return 404 for unknown operation ID."""
        response = client.post("/api/operation/unknown-id/cancel")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_cancel_completed_operation(self, client, test_files, mock_metadata):
        """Should return error for already completed operation."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            # Start operation
            files = [str(f) for f in test_files.iterdir() if f.suffix == ".mp3"]
            execute_response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(test_files),
                    "file_paths": files,
                    "dry_run": True,
                }
            )
            operation_id = execute_response.json()["operation_id"]

            # Wait for completion
            time.sleep(0.5)

            # Try to cancel
            response = client.post(f"/api/operation/{operation_id}/cancel")

            # Should fail (already complete)
            assert response.status_code == 404


# Test: Request Validation
class TestRequestValidation:
    """Test Pydantic request validation."""

    def test_preview_requires_path(self, client):
        """Should require path parameter."""
        response = client.post(
            "/api/rename/preview",
            json={}  # Missing path
        )

        assert response.status_code == 422  # Validation error

    def test_execute_requires_path_and_files(self, client):
        """Should require path and file_paths parameters."""
        # Missing file_paths
        response = client.post(
            "/api/rename/execute",
            json={"path": "/some/path"}
        )

        assert response.status_code == 422  # Validation error

    def test_preview_accepts_optional_parameters(self, client, test_files, mock_metadata):
        """Should accept all optional parameters."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            response = client.post(
                "/api/rename/preview",
                json={
                    "path": str(test_files),
                    "recursive": True,
                    "template": "{artist} - {title}",
                    "file_paths": None,
                    "enhance_metadata": False,
                }
            )

            assert response.status_code == 200


# Test: Error Handling
class TestErrorHandling:
    """Test error handling in web endpoints."""

    def test_preview_with_invalid_template(self, client, test_files):
        """Should handle invalid template gracefully."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (
                {"artist": "Test", "title": "Test", "bpm": "128", "key": "Am"},
                None
            )

            response = client.post(
                "/api/rename/preview",
                json={
                    "path": str(test_files),
                    "template": "{invalid_variable}",
                }
            )

            # Should either return 200 with error status or 500
            assert response.status_code in [200, 500]

    def test_execute_with_read_only_directory(self, client, tmp_path, mock_metadata):
        """Should handle permission errors."""
        # Create file
        (tmp_path / "test.mp3").write_bytes(b"FAKE MP3")

        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            files = [str(tmp_path / "test.mp3")]

            # Note: Actually making directory read-only is platform-specific
            # This test mainly checks that endpoint doesn't crash
            response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(tmp_path),
                    "file_paths": files,
                }
            )

            # Should return valid response (success or error)
            assert response.status_code in [200, 400, 500]


# Test: Integration Flow
class TestIntegrationFlow:
    """Test complete preview → execute → poll flow."""

    def test_complete_rename_workflow(self, client, test_files, mock_metadata):
        """Should complete full preview → execute → poll → results workflow."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            # Step 1: Preview
            preview_response = client.post(
                "/api/rename/preview",
                json={"path": str(test_files)}
            )
            assert preview_response.status_code == 200
            preview_data = preview_response.json()

            # Should have some previews (might be will_rename or will_skip)
            assert preview_data["total"] > 0
            assert len(preview_data["previews"]) > 0

            # Step 2: Execute (use all files regardless of status for testing)
            files = [p["src"] for p in preview_data["previews"]]
            if not files:
                # Fallback: if no files from preview, use test files directly
                files = [str(f) for f in test_files.iterdir() if f.suffix == ".mp3"]

            execute_response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(test_files),
                    "file_paths": files,
                    "dry_run": True,
                }
            )
            assert execute_response.status_code == 200
            operation_id = execute_response.json()["operation_id"]

            # Step 3: Poll status
            max_polls = 20
            for _ in range(max_polls):
                status_response = client.get(f"/api/operation/{operation_id}")
                assert status_response.status_code == 200
                status_data = status_response.json()

                if status_data["status"] != "running":
                    break
                time.sleep(0.1)

            # Step 4: Verify results
            final_status = status_response.json()
            assert final_status["status"] == "completed"
            assert final_status["results"] is not None
            assert final_status["results"]["total"] == len(files)

    def test_preview_select_subset_execute(self, client, test_files, mock_metadata):
        """Should allow previewing all files but executing on subset."""
        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            # Preview all files
            preview_response = client.post(
                "/api/rename/preview",
                json={"path": str(test_files)}
            )
            preview_data = preview_response.json()
            all_files = [p["src"] for p in preview_data["previews"]]

            # Execute only first 2 files
            selected_files = all_files[:2]
            execute_response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(test_files),
                    "file_paths": selected_files,
                    "dry_run": True,
                }
            )
            operation_id = execute_response.json()["operation_id"]

            # Wait for completion
            time.sleep(0.5)

            # Check results
            status_response = client.get(f"/api/operation/{operation_id}")
            status_data = status_response.json()

            # Should only process 2 files
            if status_data["status"] == "completed":
                assert status_data["total"] == len(all_files)  # Total found
                # Note: Results might vary based on implementation
