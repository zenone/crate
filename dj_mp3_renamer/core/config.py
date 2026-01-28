"""
Configuration management for DJ MP3 Renamer.

Stores user preferences securely in home directory.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


# Default configuration values
DEFAULT_CONFIG = {
    "acoustid_api_key": "8XaBELgH",  # Free public key for open-source projects
    "enable_musicbrainz": False,  # Disabled by default (limited data coverage)
    "auto_detect_bpm": True,
    "auto_detect_key": True,
    "default_template": "{artist} - {title} [{camelot} {bpm}]",
    "recursive_default": True,
}


def get_config_dir() -> Path:
    """
    Get configuration directory path.

    Returns:
        Path to config directory (creates if not exists)

    Examples:
        >>> config_dir = get_config_dir()
        >>> print(config_dir)
        /Users/username/.config/dj_mp3_renamer
    """
    # Use XDG Base Directory specification on Unix, AppData on Windows
    if os.name == "nt":  # Windows
        config_home = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:  # Unix-like (macOS, Linux)
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    config_dir = config_home / "dj_mp3_renamer"
    config_dir.mkdir(parents=True, exist_ok=True)

    return config_dir


def get_config_path() -> Path:
    """
    Get path to configuration file.

    Returns:
        Path to config.json file
    """
    return get_config_dir() / "config.json"


def load_config() -> Dict[str, Any]:
    """
    Load configuration from file.

    Returns:
        Configuration dictionary with defaults for missing keys

    Examples:
        >>> config = load_config()
        >>> print(config["acoustid_api_key"])
    """
    config_path = get_config_path()

    # Start with defaults
    config = DEFAULT_CONFIG.copy()

    # Load user overrides if file exists
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception:
            # If config is corrupted, use defaults
            pass

    return config


def save_config(config: Dict[str, Any]) -> bool:
    """
    Save configuration to file.

    Args:
        config: Configuration dictionary

    Returns:
        True if successful, False otherwise

    Examples:
        >>> config = load_config()
        >>> config["acoustid_api_key"] = "my_key"
        >>> save_config(config)
        True
    """
    config_path = get_config_path()

    try:
        # Write config file
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        # Set secure permissions (Unix-like systems only)
        if os.name != "nt":
            os.chmod(config_path, 0o600)  # User read/write only

        return True
    except Exception:
        return False


def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get a single configuration value.

    Args:
        key: Configuration key
        default: Default value if key not found

    Returns:
        Configuration value or default

    Examples:
        >>> api_key = get_config_value("acoustid_api_key")
        >>> print(api_key)
    """
    config = load_config()
    return config.get(key, default)


def set_config_value(key: str, value: Any) -> bool:
    """
    Set a single configuration value.

    Args:
        key: Configuration key
        value: Value to set

    Returns:
        True if successful, False otherwise

    Examples:
        >>> set_config_value("acoustid_api_key", "my_new_key")
        True
    """
    config = load_config()
    config[key] = value
    return save_config(config)
