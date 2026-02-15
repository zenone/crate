"""
Golden Path Integration Tests for Crate Web UI.

Tests the full rename workflow with REAL MP3 files from the smoke test fixture.
This ensures the Web API works correctly end-to-end with actual metadata.

Fixture: /Users/szenone/Music/DJ/CrateSmokeTest
Safe Copy: /tmp/CrateSmokeTestCopy

Run:
    pytest tests/test_golden_path.py -v
    pytest tests/test_golden_path.py -v -k "preview" --no-header -q  # Just preview
    pytest tests/test_golden_path.py -v --golden-path  # Full suite (marker)
"""

import hashlib
import json
import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from web.main import app

# ============================================================================
# Configuration
# ============================================================================

CANONICAL_FIXTURE = Path("/Users/szenone/Music/DJ/CrateSmokeTest")
SAFE_COPY_DIR = Path("/tmp/CrateSmokeTestCopy")


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture(scope="function")
def smoke_test_copy():
    """
    Create a fresh copy of the smoke test fixture for each test.

    Returns the path to the copy. Automatically cleaned up after each test.
    """
    if not CANONICAL_FIXTURE.exists():
        pytest.skip(f"Smoke test fixture not found: {CANONICAL_FIXTURE}")

    # Clean up any previous copy
    if SAFE_COPY_DIR.exists():
        shutil.rmtree(SAFE_COPY_DIR)

    # Create fresh copy
    shutil.copytree(CANONICAL_FIXTURE, SAFE_COPY_DIR)

    yield SAFE_COPY_DIR

    # Cleanup after test
    if SAFE_COPY_DIR.exists():
        shutil.rmtree(SAFE_COPY_DIR)


def get_file_checksums(directory: Path) -> dict[str, str]:
    """Get MD5 checksums for all MP3 files in directory (recursive)."""
    checksums = {}
    for mp3 in directory.rglob("*.mp3"):
        with open(mp3, "rb") as f:
            checksums[str(mp3.relative_to(directory))] = hashlib.md5(f.read()).hexdigest()
    return checksums


def get_filenames(directory: Path) -> set[str]:
    """Get all MP3 filenames (relative paths) in directory."""
    return {str(f.relative_to(directory)) for f in directory.rglob("*.mp3")}


# ============================================================================
# Golden Path Tests
# ============================================================================


class TestGoldenPathPreview:
    """Test preview with real MP3 files."""

    def test_preview_loads_real_metadata(self, client, smoke_test_copy):
        """Preview should read actual ID3 tags from real MP3 files."""
        response = client.post(
            "/api/rename/preview",
            json={
                "path": str(smoke_test_copy),
                "recursive": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should find the MP3 files
        assert data["total"] > 0, "Should find MP3 files in fixture"
        assert len(data["previews"]) > 0

        # Check we got real metadata (not mocked)
        preview = data["previews"][0]
        assert preview["metadata"] is not None

        # Big Audio Dynamite files should have artist metadata
        metadata = preview["metadata"]
        assert metadata.get("artist") or metadata.get("title"), (
            f"Expected real metadata, got: {metadata}"
        )

        print(f"\n✓ Found {data['total']} MP3 files")
        print(f"✓ Sample metadata: {json.dumps(metadata, indent=2)[:200]}...")

    def test_preview_shows_will_rename(self, client, smoke_test_copy):
        """Preview should identify files that will be renamed."""
        response = client.post(
            "/api/rename/preview",
            json={
                "path": str(smoke_test_copy),
                "recursive": True,
                "template": "{artist} - {title} [{camelot} {bpm}]",
            },
        )

        assert response.status_code == 200
        data = response.json()

        stats = data["stats"]
        will_rename = stats["will_rename"]
        will_skip = stats["will_skip"]
        errors = stats["errors"]

        print(f"\n✓ Preview stats: rename={will_rename}, skip={will_skip}, errors={errors}")

        # Should have some files to rename (smoke test has valid metadata)
        assert will_rename > 0 or will_skip > 0, "Should have processable files"

    def test_preview_with_custom_template(self, client, smoke_test_copy):
        """Different templates should produce different preview results."""
        templates = [
            "{artist} - {title}",
            "{bpm} {artist} - {title}",
            "{title} [{camelot}]",
        ]

        results = []
        for template in templates:
            response = client.post(
                "/api/rename/preview",
                json={
                    "path": str(smoke_test_copy),
                    "recursive": True,
                    "template": template,
                },
            )
            assert response.status_code == 200
            results.append(response.json())

        # Verify different templates produce different destinations
        if results[0]["previews"] and results[0]["previews"][0]["status"] == "will_rename":
            dst0 = results[0]["previews"][0]["dst"]
            dst1 = results[1]["previews"][0]["dst"]
            dst2 = results[2]["previews"][0]["dst"]

            # At least some should differ
            destinations = {dst0, dst1, dst2}
            assert len(destinations) > 1, "Different templates should produce different results"
            print(f"\n✓ Templates produce unique results: {len(destinations)} unique")


class TestGoldenPathExecute:
    """Test execute + undo with real MP3 files."""

    def test_execute_renames_files(self, client, smoke_test_copy):
        """Execute should actually rename files on disk."""
        original_names = get_filenames(smoke_test_copy)
        original_checksums = get_file_checksums(smoke_test_copy)

        # Preview first with simple template that will produce changes
        preview_response = client.post(
            "/api/rename/preview",
            json={
                "path": str(smoke_test_copy),
                "recursive": True,
                "template": "{artist} - {title}",  # Simple template
            },
        )
        assert preview_response.status_code == 200
        preview_data = preview_response.json()

        # Get files that will be renamed
        will_rename_files = [
            p["src"] for p in preview_data["previews"] if p["status"] == "will_rename"
        ]

        if not will_rename_files:
            pytest.skip("No files to rename in preview")

        print(f"\n✓ {len(will_rename_files)} files will be renamed")

        # Execute
        execute_response = client.post(
            "/api/rename/execute",
            json={
                "path": str(smoke_test_copy),
                "file_paths": will_rename_files,
                "dry_run": False,  # REAL execution
                "template": "{artist} - {title}",
            },
        )
        assert execute_response.status_code == 200
        operation_id = execute_response.json()["operation_id"]

        # Poll for completion
        for _ in range(30):
            status_response = client.get(f"/api/operation/{operation_id}")
            assert status_response.status_code == 200
            status = status_response.json()

            if status["status"] in ("completed", "error", "cancelled"):
                break
            time.sleep(0.2)

        assert status["status"] == "completed", f"Operation failed: {status}"

        # Verify files were actually renamed
        new_names = get_filenames(smoke_test_copy)
        new_checksums = get_file_checksums(smoke_test_copy)

        # Filenames should have changed
        assert new_names != original_names, "Filenames should have changed"

        # But file count should be the same
        assert len(new_names) == len(original_names), "File count should remain the same"

        # Content checksums should be identical (files not corrupted)
        original_hash_set = set(original_checksums.values())
        new_hash_set = set(new_checksums.values())
        assert original_hash_set == new_hash_set, "File contents should be unchanged"

        print(f"✓ Renamed {status['results']['renamed']} files")
        print("✓ File integrity verified (checksums match)")

    def test_execute_and_undo(self, client, smoke_test_copy):
        """Undo should restore original filenames."""
        original_names = get_filenames(smoke_test_copy)

        # Preview with simple template that will produce changes
        preview_response = client.post(
            "/api/rename/preview",
            json={
                "path": str(smoke_test_copy),
                "recursive": True,
                "template": "{artist} - {title}",  # Simple template
            },
        )
        preview_data = preview_response.json()

        will_rename_files = [
            p["src"] for p in preview_data["previews"] if p["status"] == "will_rename"
        ]

        if not will_rename_files:
            pytest.skip("No files to rename")

        # Execute
        execute_response = client.post(
            "/api/rename/execute",
            json={
                "path": str(smoke_test_copy),
                "file_paths": will_rename_files,
                "dry_run": False,
                "template": "{artist} - {title}",
            },
        )
        operation_id = execute_response.json()["operation_id"]

        # Wait for completion and get undo session
        undo_session_id = None
        for _ in range(30):
            status = client.get(f"/api/operation/{operation_id}").json()
            if status["status"] != "running":
                undo_session_id = status.get("undo_session_id")
                break
            time.sleep(0.2)

        assert status["status"] == "completed"
        renamed_count = status["results"]["renamed"]

        # Verify names changed
        post_execute_names = get_filenames(smoke_test_copy)
        assert post_execute_names != original_names

        print(f"\n✓ Renamed {renamed_count} files")

        # UNDO - requires session_id from operation status
        assert undo_session_id is not None, "No undo session created"

        undo_response = client.post("/api/rename/undo", params={"session_id": undo_session_id})
        assert undo_response.status_code == 200
        undo_data = undo_response.json()

        assert undo_data["success"], f"Undo failed: {undo_data}"

        # Wait a moment for filesystem
        time.sleep(0.1)

        # Verify original names restored
        post_undo_names = get_filenames(smoke_test_copy)
        assert post_undo_names == original_names, (
            f"Undo should restore original names.\nExpected: {original_names}\nGot: {post_undo_names}"
        )

        print(f"✓ Undo successful: {undo_data.get('reverted_count', 'N/A')} files restored")

    def test_multiple_execute_undo_cycles(self, client, smoke_test_copy):
        """Multiple execute/undo cycles should work correctly."""
        original_names = get_filenames(smoke_test_copy)

        for cycle in range(3):
            # Preview with simple template
            preview = client.post(
                "/api/rename/preview",
                json={
                    "path": str(smoke_test_copy),
                    "recursive": True,
                    "template": "{artist} - {title}",
                },
            ).json()

            files = [p["src"] for p in preview["previews"] if p["status"] == "will_rename"]
            if not files:
                continue

            # Execute
            exec_resp = client.post(
                "/api/rename/execute",
                json={
                    "path": str(smoke_test_copy),
                    "file_paths": files,
                    "dry_run": False,
                    "template": "{artist} - {title}",
                },
            )
            op_id = exec_resp.json()["operation_id"]

            # Wait and get undo session
            undo_session_id = None
            for _ in range(30):
                status = client.get(f"/api/operation/{op_id}").json()
                if status["status"] != "running":
                    undo_session_id = status.get("undo_session_id")
                    break
                time.sleep(0.1)

            assert undo_session_id is not None, f"Cycle {cycle + 1}: no undo session"

            # Undo
            undo = client.post("/api/rename/undo", params={"session_id": undo_session_id}).json()
            assert undo["success"], f"Cycle {cycle + 1}: undo failed"

            # Verify restored
            current_names = get_filenames(smoke_test_copy)
            assert current_names == original_names, f"Cycle {cycle + 1}: names should be restored"

        print("\n✓ 3 execute/undo cycles completed successfully")


class TestGoldenPathEdgeCases:
    """Test edge cases with real files."""

    def test_preview_empty_directory(self, client, smoke_test_copy):
        """Preview on empty dir should return gracefully."""
        empty_dir = smoke_test_copy / "empty_test_dir"
        empty_dir.mkdir(exist_ok=True)

        response = client.post("/api/rename/preview", json={"path": str(empty_dir)})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["previews"] == []

    def test_preview_specific_file_selection(self, client, smoke_test_copy):
        """Preview with specific file_paths should filter correctly."""
        # Get all files
        all_files = list(smoke_test_copy.rglob("*.mp3"))
        if len(all_files) < 2:
            pytest.skip("Need at least 2 files for this test")

        # Select only first file
        selected = [str(all_files[0])]

        response = client.post(
            "/api/rename/preview",
            json={
                "path": str(smoke_test_copy),
                "file_paths": selected,
                "recursive": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1, f"Should process only 1 file, got {data['total']}"

    def test_execute_subset_of_files(self, client, smoke_test_copy):
        """Execute on subset should only rename selected files."""
        # Preview all with simple template
        preview = client.post(
            "/api/rename/preview",
            json={
                "path": str(smoke_test_copy),
                "recursive": True,
                "template": "{artist} - {title}",
            },
        ).json()

        will_rename = [p for p in preview["previews"] if p["status"] == "will_rename"]
        if len(will_rename) < 2:
            pytest.skip("Need at least 2 renameable files")

        # Execute only first file
        selected = [will_rename[0]["src"]]

        exec_resp = client.post(
            "/api/rename/execute",
            json={
                "path": str(smoke_test_copy),
                "file_paths": selected,
                "dry_run": False,
                "template": "{artist} - {title}",
            },
        )
        op_id = exec_resp.json()["operation_id"]

        # Wait
        for _ in range(30):
            status = client.get(f"/api/operation/{op_id}").json()
            if status["status"] != "running":
                break
            time.sleep(0.1)

        assert status["results"]["renamed"] == 1
        print(f"\n✓ Subset execution: only 1 of {len(will_rename)} files renamed")


class TestGoldenPathDataIntegrity:
    """Verify file integrity throughout operations."""

    def test_file_contents_preserved(self, client, smoke_test_copy):
        """File binary contents should never change during rename."""
        # Get checksums before
        before_checksums = get_file_checksums(smoke_test_copy)

        # Preview + Execute with simple template
        preview = client.post(
            "/api/rename/preview",
            json={
                "path": str(smoke_test_copy),
                "recursive": True,
                "template": "{artist} - {title}",
            },
        ).json()

        files = [p["src"] for p in preview["previews"] if p["status"] == "will_rename"]
        if not files:
            pytest.skip("No files to rename")

        exec_resp = client.post(
            "/api/rename/execute",
            json={
                "path": str(smoke_test_copy),
                "file_paths": files,
                "dry_run": False,
                "template": "{artist} - {title}",
            },
        )
        op_id = exec_resp.json()["operation_id"]

        undo_session_id = None
        for _ in range(30):
            status = client.get(f"/api/operation/{op_id}").json()
            if status["status"] != "running":
                undo_session_id = status.get("undo_session_id")
                break
            time.sleep(0.1)

        # Get checksums after
        after_checksums = get_file_checksums(smoke_test_copy)

        # Same checksums, different filenames
        assert set(before_checksums.values()) == set(after_checksums.values()), (
            "File contents should be identical after rename"
        )

        # Undo
        if undo_session_id:
            client.post("/api/rename/undo", params={"session_id": undo_session_id})

            # Final check
            final_checksums = get_file_checksums(smoke_test_copy)
            assert before_checksums == final_checksums, (
                "After undo, filenames AND checksums should match original"
            )

        print(f"\n✓ Data integrity verified for {len(before_checksums)} files")


# ============================================================================
# Standalone Runner
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
