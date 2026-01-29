"""
Tests for config management API.

Tests verify:
- Config operations accessible via RenamerAPI
- get_config() returns current configuration
- update_config() persists changes
- get_config_value() returns specific value
- set_config_value() updates single value
- get_default_config() returns defaults
- Config changes affect API instance
"""

from pathlib import Path
import pytest
from unittest.mock import patch

from dj_mp3_renamer.api import RenamerAPI


# Test Fixtures
@pytest.fixture
def api_instance():
    """Create RenamerAPI instance for testing."""
    return RenamerAPI(workers=2)


@pytest.fixture
def mock_config_path(tmp_path, monkeypatch):
    """Mock get_config_path to use temp directory."""
    config_file = tmp_path / "config.json"

    def mock_get_config_path():
        return config_file

    monkeypatch.setattr("dj_mp3_renamer.core.config.get_config_path", mock_get_config_path)

    # Clear cache before each test
    from dj_mp3_renamer.core.config import clear_config_cache
    clear_config_cache()

    return config_file


# Test: Get Config
class TestGetConfig:
    """Test get_config() method."""

    def test_get_config_returns_dict(self, api_instance, mock_config_path):
        """Should return configuration dictionary."""
        config = api_instance.get_config()

        assert isinstance(config, dict)
        assert len(config) > 0

    def test_get_config_includes_defaults(self, api_instance, mock_config_path):
        """Should include default configuration values."""
        config = api_instance.get_config()

        # Check for known default keys
        assert "acoustid_api_key" in config
        assert "auto_detect_bpm" in config
        assert "auto_detect_key" in config
        assert "default_template" in config

    def test_get_config_includes_user_overrides(self, api_instance, mock_config_path):
        """Should include user configuration overrides."""
        # Set a custom value
        api_instance.update_config({"custom_key": "custom_value"})

        # Get config
        config = api_instance.get_config()

        assert "custom_key" in config
        assert config["custom_key"] == "custom_value"


# Test: Update Config
class TestUpdateConfig:
    """Test update_config() method."""

    def test_update_config_persists_changes(self, api_instance, mock_config_path):
        """Should persist configuration changes."""
        updates = {
            "auto_detect_bpm": False,
            "default_template": "{bpm} - {artist}"
        }

        success = api_instance.update_config(updates)
        assert success is True

        # Verify persisted (create new instance)
        from dj_mp3_renamer.core.config import clear_config_cache
        clear_config_cache()

        new_api = RenamerAPI()
        config = new_api.get_config()

        assert config["auto_detect_bpm"] is False
        assert config["default_template"] == "{bpm} - {artist}"

    def test_update_config_updates_instance(self, api_instance, mock_config_path):
        """Should update API instance config."""
        original_value = api_instance.config.get("auto_detect_bpm")

        api_instance.update_config({"auto_detect_bpm": not original_value})

        # Instance config should be updated
        assert api_instance.config["auto_detect_bpm"] == (not original_value)

    def test_update_config_merges_with_existing(self, api_instance, mock_config_path):
        """Should merge updates with existing config."""
        # Set initial value
        api_instance.update_config({"key1": "value1"})

        # Update with different key
        api_instance.update_config({"key2": "value2"})

        # Both should exist
        config = api_instance.get_config()
        assert config["key1"] == "value1"
        assert config["key2"] == "value2"

    def test_update_config_overwrites_existing_keys(self, api_instance, mock_config_path):
        """Should overwrite existing keys."""
        api_instance.update_config({"key": "value1"})
        api_instance.update_config({"key": "value2"})

        config = api_instance.get_config()
        assert config["key"] == "value2"


# Test: Get Config Value
class TestGetConfigValue:
    """Test get_config_value() method."""

    def test_get_config_value_returns_value(self, api_instance, mock_config_path):
        """Should return specific config value."""
        value = api_instance.get_config_value("auto_detect_bpm")

        assert value is not None
        assert isinstance(value, bool)

    def test_get_config_value_returns_default_if_missing(self, api_instance, mock_config_path):
        """Should return default if key missing."""
        value = api_instance.get_config_value("nonexistent_key", default="fallback")

        assert value == "fallback"

    def test_get_config_value_returns_none_if_missing_no_default(self, api_instance, mock_config_path):
        """Should return None if key missing and no default."""
        value = api_instance.get_config_value("nonexistent_key")

        assert value is None


# Test: Set Config Value
class TestSetConfigValue:
    """Test set_config_value() method."""

    def test_set_config_value_updates_value(self, api_instance, mock_config_path):
        """Should update single config value."""
        success = api_instance.set_config_value("auto_detect_bpm", False)

        assert success is True
        assert api_instance.get_config_value("auto_detect_bpm") is False

    def test_set_config_value_persists(self, api_instance, mock_config_path):
        """Should persist value to disk."""
        api_instance.set_config_value("test_key", "test_value")

        # Verify persisted (create new instance)
        from dj_mp3_renamer.core.config import clear_config_cache
        clear_config_cache()

        new_api = RenamerAPI()
        value = new_api.get_config_value("test_key")

        assert value == "test_value"

    def test_set_config_value_updates_instance(self, api_instance, mock_config_path):
        """Should update instance config."""
        api_instance.set_config_value("new_key", "new_value")

        assert api_instance.config["new_key"] == "new_value"


# Test: Get Default Config
class TestGetDefaultConfig:
    """Test get_default_config() method."""

    def test_get_default_config_returns_defaults(self, api_instance, mock_config_path):
        """Should return default configuration."""
        defaults = api_instance.get_default_config()

        assert isinstance(defaults, dict)
        assert len(defaults) > 0

    def test_get_default_config_includes_known_defaults(self, api_instance, mock_config_path):
        """Should include known default values."""
        defaults = api_instance.get_default_config()

        assert "acoustid_api_key" in defaults
        assert "auto_detect_bpm" in defaults
        assert defaults["auto_detect_bpm"] is True  # Known default

    def test_get_default_config_unaffected_by_user_config(self, api_instance, mock_config_path):
        """Should return defaults regardless of user config."""
        # Change user config
        api_instance.update_config({"auto_detect_bpm": False})

        # Get defaults
        defaults = api_instance.get_default_config()

        # Should still have original default
        assert defaults["auto_detect_bpm"] is True

    def test_get_default_config_returns_copy(self, api_instance, mock_config_path):
        """Should return a copy (not mutate defaults)."""
        defaults1 = api_instance.get_default_config()
        defaults2 = api_instance.get_default_config()

        # Mutate first copy
        defaults1["test"] = "mutated"

        # Second copy should be unaffected
        assert "test" not in defaults2


# Test: Config Integration
class TestConfigIntegration:
    """Test config management integration."""

    def test_config_changes_affect_operations(self, api_instance, mock_config_path):
        """Should use updated config in operations."""
        # Change default template
        new_template = "{bpm} BPM - {artist}"
        api_instance.update_config({"default_template": new_template})

        # Config should be updated
        assert api_instance.config["default_template"] == new_template

    def test_multiple_api_instances_share_config(self, mock_config_path):
        """Should share config across API instances."""
        api1 = RenamerAPI()
        api1.update_config({"shared_key": "shared_value"})

        # Create new instance
        from dj_mp3_renamer.core.config import clear_config_cache
        clear_config_cache()

        api2 = RenamerAPI()
        value = api2.get_config_value("shared_key")

        assert value == "shared_value"

    def test_config_cache_cleared_after_update(self, api_instance, mock_config_path):
        """Should clear cache after config update."""
        # Update config
        api_instance.update_config({"test": "value1"})

        # Update again (cache should be cleared)
        api_instance.update_config({"test": "value2"})

        # Should have latest value
        value = api_instance.get_config_value("test")
        assert value == "value2"


# Test: Error Handling
class TestConfigErrorHandling:
    """Test config error handling."""

    def test_update_config_with_empty_dict(self, api_instance, mock_config_path):
        """Should handle empty updates."""
        config_before = api_instance.get_config()

        success = api_instance.update_config({})

        assert success is True
        config_after = api_instance.get_config()
        assert config_before == config_after

    def test_set_config_value_with_none(self, api_instance, mock_config_path):
        """Should handle None values."""
        success = api_instance.set_config_value("nullable_key", None)

        assert success is True
        value = api_instance.get_config_value("nullable_key")
        assert value is None

    def test_get_config_value_with_complex_types(self, api_instance, mock_config_path):
        """Should handle complex types."""
        complex_value = {"nested": {"key": "value"}, "list": [1, 2, 3]}

        api_instance.set_config_value("complex", complex_value)

        retrieved = api_instance.get_config_value("complex")
        assert retrieved == complex_value
