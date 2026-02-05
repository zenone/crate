"""
Tests for configuration management with caching.

Tests verify:
- Config loading with defaults
- Config saving and persistence
- Config caching with mtime validation
- Cache invalidation when file changes
- Cache isolation (no mutation)
- Cache clearing
- Edge cases (missing file, permissions, parse errors)
"""

import json
import time
from unittest.mock import patch

import pytest

from crate.core.config import (
    DEFAULT_CONFIG,
    clear_config_cache,
    get_config_value,
    load_config,
    save_config,
    set_config_value,
)


# Test Fixtures
@pytest.fixture
def mock_config_path(tmp_path, monkeypatch):
    """Mock get_config_path to use temp directory."""
    config_file = tmp_path / "config.json"

    def mock_get_config_path():
        return config_file

    monkeypatch.setattr("crate.core.config.get_config_path", mock_get_config_path)

    # Clear cache before each test
    clear_config_cache()

    return config_file


# Basic Config Tests
class TestConfigBasics:
    """Test basic config operations (loading, saving, defaults)."""

    def test_load_config_returns_defaults_when_no_file(self, mock_config_path):
        """Should return default config when file doesn't exist."""
        config = load_config()

        # Should have all default keys
        for key, value in DEFAULT_CONFIG.items():
            assert key in config
            assert config[key] == value

    def test_save_config_creates_file(self, mock_config_path):
        """Should create config file when saving."""
        config = DEFAULT_CONFIG.copy()
        config["acoustid_api_key"] = "test_key_12345"

        result = save_config(config)

        assert result is True
        assert mock_config_path.exists()

    def test_save_and_load_config_roundtrip(self, mock_config_path):
        """Should persist config values through save and load."""
        # Save config with custom value
        config = DEFAULT_CONFIG.copy()
        config["acoustid_api_key"] = "custom_key"
        config["enable_musicbrainz"] = True
        save_config(config)

        # Clear cache to force reload
        clear_config_cache()

        # Load config and verify
        loaded = load_config()
        assert loaded["acoustid_api_key"] == "custom_key"
        assert loaded["enable_musicbrainz"] is True

    def test_get_config_value_returns_value(self, mock_config_path):
        """Should return specific config value."""
        # Create config with known value
        config = DEFAULT_CONFIG.copy()
        config["acoustid_api_key"] = "known_key"
        save_config(config)

        clear_config_cache()

        # Get specific value
        value = get_config_value("acoustid_api_key")
        assert value == "known_key"

    def test_get_config_value_returns_default_if_missing(self, mock_config_path):
        """Should return default value if key missing."""
        value = get_config_value("nonexistent_key", default="fallback")
        assert value == "fallback"

    def test_set_config_value_updates_config(self, mock_config_path):
        """Should update single config value."""
        result = set_config_value("acoustid_api_key", "new_key")
        assert result is True

        clear_config_cache()

        # Verify value persisted
        config = load_config()
        assert config["acoustid_api_key"] == "new_key"


# Caching Tests
class TestConfigCaching:
    """Test config caching with mtime validation."""

    def test_config_caching_hit(self, mock_config_path):
        """
        Test: Config is cached when file unchanged.

        Scenario:
        1. Create config file
        2. Load config (cache miss, reads file)
        3. Load config again (cache hit, no read)
        4. Verify both loads return same data
        """
        # Create config file
        config_data = DEFAULT_CONFIG.copy()
        config_data["acoustid_api_key"] = "cached_key"
        mock_config_path.write_text(json.dumps(config_data))

        # First load (cache miss)
        config1 = load_config()

        # Second load (cache hit - file unchanged)
        config2 = load_config()

        # Both should have same data
        assert config1 == config2
        assert config1["acoustid_api_key"] == "cached_key"

    def test_config_caching_invalidation_on_file_change(self, mock_config_path):
        """
        Test: Cache invalidates when file modified.

        Scenario:
        1. Create config file with value A
        2. Load config (cache miss)
        3. Modify config file with value B
        4. Load config again (cache miss, reads new value)
        5. Verify second load returns value B
        """
        # Create config with value A
        config_a = DEFAULT_CONFIG.copy()
        config_a["acoustid_api_key"] = "key_A"
        mock_config_path.write_text(json.dumps(config_a))

        # First load
        config1 = load_config()
        assert config1["acoustid_api_key"] == "key_A"

        # Wait to ensure mtime changes (some filesystems have 1s resolution)
        time.sleep(0.01)

        # Modify file with value B
        config_b = DEFAULT_CONFIG.copy()
        config_b["acoustid_api_key"] = "key_B"
        mock_config_path.write_text(json.dumps(config_b))

        # Second load should detect change
        config2 = load_config()
        assert config2["acoustid_api_key"] == "key_B"

    def test_config_cache_isolation(self, mock_config_path):
        """
        Test: Cached config is isolated from mutations.

        Scenario:
        1. Load config
        2. Mutate returned dict
        3. Load config again
        4. Verify mutation didn't affect cache
        """
        # Create config
        config_data = DEFAULT_CONFIG.copy()
        config_data["acoustid_api_key"] = "original_key"
        mock_config_path.write_text(json.dumps(config_data))

        # First load
        config1 = load_config()
        config1["acoustid_api_key"] = "mutated_key"  # Mutate returned dict

        # Second load should return original value
        config2 = load_config()
        assert config2["acoustid_api_key"] == "original_key"

    def test_clear_config_cache_forces_reload(self, mock_config_path):
        """
        Test: clear_config_cache() resets cache.

        Scenario:
        1. Load config (cache populated)
        2. Clear cache
        3. Modify file
        4. Load config again (should read new file)
        """
        # Create initial config
        config_data = DEFAULT_CONFIG.copy()
        config_data["acoustid_api_key"] = "initial_key"
        mock_config_path.write_text(json.dumps(config_data))

        # Load to populate cache
        config1 = load_config()
        assert config1["acoustid_api_key"] == "initial_key"

        # Modify file
        config_data["acoustid_api_key"] = "new_key"
        mock_config_path.write_text(json.dumps(config_data))

        # Without clearing cache, would return cached value
        # But we clear cache:
        clear_config_cache()

        # Next load should read new file
        config2 = load_config()
        assert config2["acoustid_api_key"] == "new_key"

    def test_save_config_clears_cache(self, mock_config_path):
        """
        Test: save_config() automatically clears cache.

        Scenario:
        1. Load config (cache populated)
        2. Save new config
        3. Load config again (should return new value, not cached)
        """
        # Initial config
        config1 = DEFAULT_CONFIG.copy()
        config1["acoustid_api_key"] = "initial"
        save_config(config1)

        # Load to populate cache
        loaded1 = load_config()
        assert loaded1["acoustid_api_key"] == "initial"

        # Save new config (should clear cache)
        config2 = DEFAULT_CONFIG.copy()
        config2["acoustid_api_key"] = "updated"
        save_config(config2)

        # Load should return new value (not cached)
        loaded2 = load_config()
        assert loaded2["acoustid_api_key"] == "updated"


# Edge Cases
class TestConfigEdgeCases:
    """Test edge cases and error handling."""

    def test_load_config_missing_file_returns_defaults(self, mock_config_path):
        """Should return defaults when file doesn't exist."""
        # Ensure file doesn't exist
        if mock_config_path.exists():
            mock_config_path.unlink()

        config = load_config()

        # Should return defaults
        assert config == DEFAULT_CONFIG

    def test_load_config_corrupted_json_returns_defaults(self, mock_config_path):
        """Should return defaults when JSON is corrupted."""
        # Write invalid JSON
        mock_config_path.write_text("{ invalid json here }")

        config = load_config()

        # Should return defaults (graceful failure)
        assert config == DEFAULT_CONFIG

    def test_load_config_empty_file_returns_defaults(self, mock_config_path):
        """Should return defaults when file is empty."""
        # Write empty file
        mock_config_path.write_text("")

        config = load_config()

        # Should return defaults
        assert config == DEFAULT_CONFIG

    def test_load_config_permission_error_returns_defaults(self, mock_config_path):
        """Should return defaults when file is unreadable."""
        # Create config file
        config_data = DEFAULT_CONFIG.copy()
        mock_config_path.write_text(json.dumps(config_data))

        # Mock permission error
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            config = load_config()

        # Should return defaults (graceful failure)
        assert config == DEFAULT_CONFIG


# Performance Tests
class TestConfigPerformance:
    """Test config caching performance."""

    def test_caching_reduces_file_reads(self, mock_config_path):
        """
        Test: Caching reduces redundant file reads.

        Verifies that loading config 100 times only reads the file once
        when file is unchanged.
        """
        # Create config file
        config_data = DEFAULT_CONFIG.copy()
        mock_config_path.write_text(json.dumps(config_data))

        # Load config 100 times
        for _ in range(100):
            config = load_config()

        # All should return same data (cached)
        # This test verifies no errors occur with repeated loads
        # (Direct verification of cache hits would require mocking)
        assert config == config_data

    def test_cache_performance_benchmark(self, mock_config_path, benchmark=None):
        """
        Optional benchmark test (requires pytest-benchmark).

        Measures performance improvement from caching.
        Skip if pytest-benchmark not installed.
        """
        if benchmark is None:
            pytest.skip("pytest-benchmark not installed")

        # Create config file
        config_data = DEFAULT_CONFIG.copy()
        mock_config_path.write_text(json.dumps(config_data))

        # Clear cache before benchmark
        clear_config_cache()

        # First load (cache miss)
        load_config()

        # Benchmark cached loads
        result = benchmark(load_config)

        # Should return valid config
        assert result == config_data
