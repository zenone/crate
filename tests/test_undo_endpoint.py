"""
Tests for undo rename functionality.

Tests verify:
- /api/rename/undo endpoint creates undo sessions
- Session expiration after 30 seconds
- Undo reverts file renames correctly
- Error handling for missing/expired sessions
- Error handling for file conflicts
"""

import time
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from web.main import app, undo_sessions, undo_sessions_created


# Test Fixtures
@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def test_files(tmp_path):
    """Create test MP3 files with actual content."""
    files = []
    for i in range(3):
        file_path = tmp_path / f"test_{i:02d}.mp3"
        file_path.write_bytes(b"FAKE MP3 DATA")
        files.append(file_path)
    return tmp_path, files


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


@pytest.fixture(autouse=True)
def cleanup_sessions():
    """Clean up undo sessions before/after each test."""
    undo_sessions.clear()
    undo_sessions_created.clear()
    yield
    undo_sessions.clear()
    undo_sessions_created.clear()


# Test: Undo Session Creation
class TestUndoSessionCreation:
    """Test that undo sessions are created automatically."""

    def test_operation_status_creates_undo_session(self, client, test_files, mock_metadata):
        """Should create undo session when operation completes successfully."""
        tmp_path, files = test_files

        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            # Start rename operation
            file_paths = [str(f) for f in files]
            response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(tmp_path),
                    "file_paths": file_paths,
                    "dry_run": False,  # Actually rename files
                    "template": "{artist} - {title}"
                }
            )

            assert response.status_code == 200
            operation_id = response.json()["operation_id"]

            # Poll until operation completes
            max_attempts = 20
            for _ in range(max_attempts):
                status_response = client.get(f"/api/operation/{operation_id}")
                assert status_response.status_code == 200
                status = status_response.json()

                if status["status"] == "completed":
                    # Check that undo session was created
                    assert "undo_session_id" in status
                    assert "undo_expires_at" in status

                    session_id = status["undo_session_id"]
                    assert session_id in undo_sessions
                    assert operation_id in undo_sessions_created

                    # Verify session has renamed files
                    session = undo_sessions[session_id]
                    assert len(session.pairs) > 0
                    break

                time.sleep(0.1)
            else:
                pytest.fail("Operation did not complete in time")

    def test_undo_session_only_includes_renamed_files(self, client, test_files, mock_metadata):
        """Should only include successfully renamed files in undo session."""
        tmp_path, files = test_files

        # Mock to make some files fail
        call_count = [0]

        def mock_read_with_failures(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 2 == 0:
                # Every other file fails
                raise Exception("Metadata read failed")
            return (mock_metadata, None)

        with patch("crate.core.io.read_mp3_metadata", side_effect=mock_read_with_failures):
            file_paths = [str(f) for f in files]
            response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(tmp_path),
                    "file_paths": file_paths,
                    "dry_run": False,
                }
            )

            operation_id = response.json()["operation_id"]

            # Poll until complete
            for _ in range(20):
                status_response = client.get(f"/api/operation/{operation_id}")
                status = status_response.json()

                if status["status"] == "completed":
                    if "undo_session_id" in status:
                        session_id = status["undo_session_id"]
                        session = undo_sessions[session_id]

                        # Should only have successfully renamed files
                        renamed_count = status["results"]["renamed"]
                        assert len(session.pairs) == renamed_count
                    break

                time.sleep(0.1)


# Test: Undo Endpoint
class TestUndoEndpoint:
    """Test /api/rename/undo endpoint."""

    def test_undo_reverts_renamed_files(self, client, test_files, mock_metadata):
        """Should revert files to original names."""
        tmp_path, files = test_files
        original_names = {f.name for f in files}

        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            # Execute rename
            file_paths = [str(f) for f in files]
            response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(tmp_path),
                    "file_paths": file_paths,
                    "dry_run": False,
                    "template": "{artist} - {title}"
                }
            )

            operation_id = response.json()["operation_id"]

            # Wait for completion and get undo session
            session_id = None
            for _ in range(20):
                status_response = client.get(f"/api/operation/{operation_id}")
                status = status_response.json()

                if status["status"] == "completed" and "undo_session_id" in status:
                    session_id = status["undo_session_id"]
                    break

                time.sleep(0.1)

            assert session_id is not None, "Undo session not created"

            # Verify files were renamed
            current_names = {f.name for f in tmp_path.iterdir() if f.suffix == ".mp3"}
            assert current_names != original_names

            # Execute undo
            undo_response = client.post(
                f"/api/rename/undo?session_id={session_id}"
            )

            assert undo_response.status_code == 200
            undo_data = undo_response.json()

            assert undo_data["success"] is True
            assert undo_data["reverted_count"] > 0
            assert undo_data["error_count"] == 0

            # Verify files reverted to original names
            final_names = {f.name for f in tmp_path.iterdir() if f.suffix == ".mp3"}
            assert final_names == original_names

    def test_undo_with_nonexistent_session_returns_404(self, client):
        """Should return 404 for nonexistent session ID."""
        response = client.post(
            "/api/rename/undo?session_id=nonexistent-session-id"
        )

        assert response.status_code == 404
        assert "not found or expired" in response.json()["detail"].lower()

    def test_undo_with_expired_session_returns_404(self, client, test_files, mock_metadata):
        """Should return 404 for expired session."""
        tmp_path, files = test_files

        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            # Execute rename
            file_paths = [str(f) for f in files]
            response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(tmp_path),
                    "file_paths": file_paths,
                    "dry_run": False,
                }
            )

            operation_id = response.json()["operation_id"]

            # Get session ID
            session_id = None
            for _ in range(20):
                status_response = client.get(f"/api/operation/{operation_id}")
                status = status_response.json()

                if status["status"] == "completed" and "undo_session_id" in status:
                    session_id = status["undo_session_id"]
                    break

                time.sleep(0.1)

            assert session_id is not None

            # Manually expire the session
            if session_id in undo_sessions:
                session = undo_sessions[session_id]
                # Set expiration to past
                from datetime import datetime, timedelta
                session.expires_at = datetime.utcnow() - timedelta(seconds=1)

            # Try to undo expired session
            undo_response = client.post(
                f"/api/rename/undo?session_id={session_id}"
            )

            assert undo_response.status_code == 404
            assert "expired" in undo_response.json()["detail"].lower()

    def test_undo_removes_session_after_use(self, client, test_files, mock_metadata):
        """Should remove session from memory after successful undo."""
        tmp_path, files = test_files

        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            # Execute rename
            file_paths = [str(f) for f in files]
            response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(tmp_path),
                    "file_paths": file_paths,
                    "dry_run": False,
                }
            )

            operation_id = response.json()["operation_id"]

            # Get session ID
            session_id = None
            for _ in range(20):
                status_response = client.get(f"/api/operation/{operation_id}")
                status = status_response.json()

                if status["status"] == "completed" and "undo_session_id" in status:
                    session_id = status["undo_session_id"]
                    break

                time.sleep(0.1)

            assert session_id is not None
            assert session_id in undo_sessions

            # Execute undo
            undo_response = client.post(
                f"/api/rename/undo?session_id={session_id}"
            )

            assert undo_response.status_code == 200

            # Session should be removed
            assert session_id not in undo_sessions

            # Second undo attempt should fail
            undo_response_2 = client.post(
                f"/api/rename/undo?session_id={session_id}"
            )

            assert undo_response_2.status_code == 404


# Test: Error Handling
class TestUndoErrorHandling:
    """Test error handling in undo functionality."""

    def test_undo_handles_missing_files(self, client, test_files, mock_metadata):
        """Should report error if renamed file no longer exists."""
        tmp_path, files = test_files

        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            # Execute rename
            file_paths = [str(f) for f in files]
            response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(tmp_path),
                    "file_paths": file_paths,
                    "dry_run": False,
                }
            )

            operation_id = response.json()["operation_id"]

            # Get session ID
            session_id = None
            for _ in range(20):
                status_response = client.get(f"/api/operation/{operation_id}")
                status = status_response.json()

                if status["status"] == "completed" and "undo_session_id" in status:
                    session_id = status["undo_session_id"]
                    break

                time.sleep(0.1)

            assert session_id is not None

            # Delete one of the renamed files
            renamed_files = list(tmp_path.iterdir())
            if renamed_files:
                renamed_files[0].unlink()

            # Execute undo
            undo_response = client.post(
                f"/api/rename/undo?session_id={session_id}"
            )

            assert undo_response.status_code == 200
            undo_data = undo_response.json()

            # Should have at least one error
            assert undo_data["error_count"] > 0
            assert len(undo_data["errors"]) > 0
            assert "no longer exists" in undo_data["errors"][0].lower()

    def test_undo_handles_filename_collision(self, client, test_files, mock_metadata):
        """Should report error if original filename is now occupied."""
        tmp_path, files = test_files

        with patch("crate.core.io.read_mp3_metadata") as mock_read:
            mock_read.return_value = (mock_metadata, None)

            # Execute rename
            file_paths = [str(f) for f in files]
            response = client.post(
                "/api/rename/execute",
                json={
                    "path": str(tmp_path),
                    "file_paths": file_paths,
                    "dry_run": False,
                }
            )

            operation_id = response.json()["operation_id"]

            # Get session ID
            session_id = None
            for _ in range(20):
                status_response = client.get(f"/api/operation/{operation_id}")
                status = status_response.json()

                if status["status"] == "completed" and "undo_session_id" in status:
                    session_id = status["undo_session_id"]
                    break

                time.sleep(0.1)

            assert session_id is not None

            # Get session and recreate one of the original files
            session = undo_sessions[session_id]
            if session.pairs:
                old_path, new_path = session.pairs[0]
                Path(old_path).write_bytes(b"COLLISION FILE")

            # Execute undo
            undo_response = client.post(
                f"/api/rename/undo?session_id={session_id}"
            )

            assert undo_response.status_code == 200
            undo_data = undo_response.json()

            # Should have at least one error
            assert undo_data["error_count"] > 0
            assert any("already exists" in err.lower() for err in undo_data["errors"])


# Test: Session Expiration
class TestUndoSessionExpiration:
    """Test session expiration behavior."""

    def test_cleanup_removes_expired_sessions(self, client):
        """Should remove expired sessions during cleanup."""
        from web.main import UndoSession, cleanup_expired_sessions
        from datetime import datetime, timedelta

        # Create an expired session
        session = UndoSession(
            session_id="test-session",
            pairs=[("/old.mp3", "/new.mp3")],
            created_at=datetime.utcnow() - timedelta(seconds=60),
            expires_at=datetime.utcnow() - timedelta(seconds=30)
        )

        undo_sessions["test-session"] = session

        # Run cleanup
        cleanup_expired_sessions()

        # Session should be removed
        assert "test-session" not in undo_sessions

    def test_cleanup_preserves_valid_sessions(self, client):
        """Should not remove valid unexpired sessions."""
        from web.main import UndoSession, cleanup_expired_sessions
        from datetime import datetime, timedelta

        # Create a valid session
        session = UndoSession(
            session_id="test-session",
            pairs=[("/old.mp3", "/new.mp3")],
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=30)
        )

        undo_sessions["test-session"] = session

        # Run cleanup
        cleanup_expired_sessions()

        # Session should still exist
        assert "test-session" in undo_sessions
