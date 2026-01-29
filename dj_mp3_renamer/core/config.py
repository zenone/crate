"""
Configuration management for DJ MP3 Renamer.

Stores user preferences securely in home directory.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


# Module-level cache for config file
_config_cache: Optional[Dict[str, Any]] = None
_config_mtime: Optional[float] = None


# Default configuration values
DEFAULT_CONFIG = {
    "acoustid_api_key": "8XaBELgH",  # Free public key for open-source projects
    "enable_musicbrainz": False,  # Disabled by default (limited data coverage)
    "auto_detect_bpm": True,
    "auto_detect_key": True,
    "verify_mode": False,  # If True, re-analyze even if tags exist (validation mode)
    "use_mb_for_all_fields": True,  # Use MusicBrainz to correct artist/title/album/year
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
    Load configuration from file with intelligent caching.

    Implements mtime-based caching to avoid redundant file reads:
    - Caches config in memory after first read
    - Tracks file modification time (mtime)
    - Invalidates cache if file is modified
    - Returns cached config if file is unchanged

    Performance:
    - Without cache: ~0.1ms per read (N reads for N calls)
    - With cache: ~0.001ms per cached read (10-100x speedup)
    - Significant for batch operations (1000+ files)

    Returns:
        Configuration dictionary with defaults for missing keys

    Examples:
        >>> config = load_config()
        >>> print(config["acoustid_api_key"])
    """
    global _config_cache, _config_mtime

    config_path = get_config_path()

    # Start with defaults
    config = DEFAULT_CONFIG.copy()

    # If config file doesn't exist, return defaults (no caching needed)
    if not config_path.exists():
        return config

    try:
        # Get current file modification time
        current_mtime = config_path.stat().st_mtime

        # Cache hit: File unchanged since last read
        if _config_cache is not None and _config_mtime == current_mtime:
            return _config_cache.copy()  # Return copy to prevent mutation

        # Cache miss: Read file and update cache
        with open(config_path, "r") as f:
            user_config = json.load(f)
            config.update(user_config)

        # Update cache
        _config_cache = config.copy()
        _config_mtime = current_mtime

    except (OSError, PermissionError, json.JSONDecodeError):
        # File exists but can't read/parse - return defaults without caching
        pass

    return config


def clear_config_cache() -> None:
    """
    Clear the configuration cache.

    Forces the next load_config() call to read from disk, even if the file
    hasn't been modified.

    Useful for:
    - Testing (reset between tests)
    - Force reload after programmatic config changes
    - Memory management (though cache is negligible ~1KB)

    Examples:
        >>> clear_config_cache()
        >>> config = load_config()  # Forces file read
    """
    global _config_cache, _config_mtime
    _config_cache = None
    _config_mtime = None


def save_config(config: Dict[str, Any]) -> bool:
    """
    Save configuration to file.

    Automatically clears the config cache after saving to ensure the next
    load_config() call reads the updated file.

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

        # Clear cache to ensure next load reads the updated file
        clear_config_cache()

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
