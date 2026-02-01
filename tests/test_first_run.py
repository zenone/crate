"""
Tests for first-run detection functionality.
"""

import pytest
from pathlib import Path
from crate.core.config import (
    is_first_run,
    mark_first_run_complete,
    get_config_path,
    save_config,
    load_config,
    clear_config_cache,
)


class TestFirstRunDetection:
    """Test first-run detection logic."""

    def test_is_first_run_when_no_config_file(self, tmp_path, monkeypatch):
        """Should return True when config file doesn't exist."""
        # Point to non-existent directory
        fake_config_path = tmp_path / "nonexistent" / "config.json"
        monkeypatch.setattr("crate.core.config.get_config_path", lambda: fake_config_path)

        assert is_first_run() is True

    def test_is_first_run_when_flag_is_false(self, tmp_path, monkeypatch):
        """Should return True when first_run_complete is False."""
        # Create config file with first_run_complete = False
        config_path = tmp_path / "config.json"
        monkeypatch.setattr("crate.core.config.get_config_path", lambda: config_path)

        config = {"first_run_complete": False, "acoustid_api_key": "test"}
        save_config(config)
        clear_config_cache()

        assert is_first_run() is True

    def test_is_not_first_run_when_flag_is_true(self, tmp_path, monkeypatch):
        """Should return False when first_run_complete is True."""
        # Create config file with first_run_complete = True
        config_path = tmp_path / "config.json"
        monkeypatch.setattr("crate.core.config.get_config_path", lambda: config_path)

        config = {"first_run_complete": True, "acoustid_api_key": "test"}
        save_config(config)
        clear_config_cache()

        assert is_first_run() is False

    def test_mark_first_run_complete_sets_flag(self, tmp_path, monkeypatch):
        """Should set first_run_complete to True."""
        config_path = tmp_path / "config.json"
        monkeypatch.setattr("crate.core.config.get_config_path", lambda: config_path)

        # Initially first run
        assert is_first_run() is True

        # Mark complete
        success = mark_first_run_complete()
        assert success is True

        # Should no longer be first run
        clear_config_cache()
        assert is_first_run() is False

        # Verify config file contains the flag
        config = load_config()
        assert config["first_run_complete"] is True

    def test_first_run_default_config_includes_flag(self):
        """Should include first_run_complete in default config."""
        from crate.core.config import DEFAULT_CONFIG

        assert "first_run_complete" in DEFAULT_CONFIG
        assert DEFAULT_CONFIG["first_run_complete"] is False
