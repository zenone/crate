"""
Configuration management for DJ MP3 Renamer.

Stores user preferences securely in home directory.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Module-level cache for config file
_config_cache: Optional[Dict[str, Any]] = None
_config_mtime: Optional[float] = None


# Default configuration values
DEFAULT_CONFIG = {
    "acoustid_api_key": "8XaBELgH",  # Free public key for open-source projects
    "enable_musicbrainz": False,  # Disabled by default (limited data coverage)
    "auto_detect_bpm": False,  # Disabled by default for speed (use --analyze to enable)
    "auto_detect_key": False,  # Disabled by default for speed (use --analyze to enable)
    "verify_mode": False,  # If True, re-analyze even if tags exist (validation mode)
    "use_mb_for_all_fields": True,  # Use MusicBrainz to correct artist/title/album/year
    "default_template": "{artist} - {title} [{camelot} {bpm}]",
    "recursive_default": True,
    "track_number_padding": 2,  # Zero-pad track numbers (2 = "01", "02", etc.)
    "first_run_complete": False,  # Set to True after user completes initial setup
    "enable_smart_detection": False,  # Smart Track Detection (Beta) - off by default (opt-in)
    "enable_per_album_detection": False,  # Task #108: Per-album smart detection - off by default (opt-in)
    "last_directory": "",  # Task #84: Last browsed directory path (empty = not set)
    "remember_last_directory": True,  # Task #84: Enable/disable feature (default: enabled)
    "parallel_audio_workers": 0,  # Task #123: Parallel audio analysis workers (0 = auto-detect, 1 = sequential)
    "audio_analysis_timeout": 30,  # Task #123: Timeout per file in seconds (prevent hangs)
    # Task #1: Feature flags for auto-apply behavior
    "enable_auto_apply": True,  # Auto-apply template for high confidence (≥threshold)
    "enable_auto_select_albums": True,  # Auto-select albums in per-album mode
    "enable_toast_notifications": True,  # Show toast notifications for actions
    "confidence_threshold": 0.9,  # Confidence threshold for auto-apply (0.7-0.95)

    # Web UI preference: how to display musical key
    # - "musical": C, Am, Gm, etc.
    # - "camelot": 8A, 9B, etc.
    # - "both": 8A (Am)
    "key_display_mode": "musical",
}


def get_config_dir() -> Path:
    """
    Get configuration directory path with automatic migration from old location.

    Migrates config from older installs (e.g., ~/.config/dj-mp3-renamer/) to ~/.config/crate/ if needed.

    Returns:
        Path to config directory (creates if not exists)

    Examples:
        >>> config_dir = get_config_dir()
        >>> print(config_dir)
        /Users/username/.config/crate
    """
    # Use XDG Base Directory specification on Unix, AppData on Windows
    if os.name == "nt":  # Windows
        config_home = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:  # Unix-like (macOS, Linux)
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    new_config_dir = config_home / "crate"
    old_config_dir = config_home / "dj-mp3-renamer"

    # Migrate from old location if it exists and new doesn't
    if old_config_dir.exists() and not new_config_dir.exists():
        import logging
        import shutil
        logger = logging.getLogger(__name__)
        try:
            # Copy entire directory to preserve all files
            shutil.copytree(old_config_dir, new_config_dir)
            logger.info(f"Migrated config from {old_config_dir} to {new_config_dir}")
        except Exception as e:
            logger.warning(f"Failed to migrate config: {e}")
            # Create new directory anyway
            new_config_dir.mkdir(parents=True, exist_ok=True)
    else:
        new_config_dir.mkdir(parents=True, exist_ok=True)

    config_dir = new_config_dir

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


def is_first_run() -> bool:
    """
    Check if this is the first run of the application.

    Returns True if:
    - Config file doesn't exist, OR
    - first_run_complete is False

    Returns:
        True if first run, False otherwise

    Examples:
        >>> if is_first_run():
        ...     show_welcome_dialog()
    """
    config_path = get_config_path()

    # If config file doesn't exist, it's definitely first run
    if not config_path.exists():
        return True

    # Check first_run_complete flag
    config = load_config()
    return not config.get("first_run_complete", False)


def mark_first_run_complete() -> bool:
    """
    Mark first run as complete.

    Sets first_run_complete=True in config file.

    Returns:
        True if successful, False otherwise

    Examples:
        >>> mark_first_run_complete()
        True
    """
    return set_config_value("first_run_complete", True)


def get_valid_directory_with_fallback(saved_path: str) -> str:
    """
    Get valid directory with intelligent fallback strategy (Task #84).

    Strategy:
    1. Try saved path directly
    2. Walk up parent directories until valid dir found
    3. Ultimate fallback: home directory (~)

    Args:
        saved_path: Last saved directory path (can be empty)

    Returns:
        Valid directory path that exists

    Examples:
        >>> get_valid_directory_with_fallback("/Users/dj/Music/Deleted")
        "/Users/dj/Music"  # If Deleted doesn't exist but Music does

        >>> get_valid_directory_with_fallback("")
        "/Users/dj"  # Falls back to home
    """
    from pathlib import Path

    # If no saved path, return home
    if not saved_path:
        return str(Path.home())

    try:
        # Expand ~ and resolve path
        path = Path(saved_path).expanduser().resolve()

        # Try saved path directly
        if path.exists() and path.is_dir():
            return str(path)

        # Walk up parent directories
        current = path
        while current != current.parent:  # Not at root
            parent = current.parent
            if parent.exists() and parent.is_dir():
                return str(parent)
            current = parent

    except Exception:
        # Any error in path handling - fall back to home
        pass

    # Ultimate fallback: home directory
    return str(Path.home())
