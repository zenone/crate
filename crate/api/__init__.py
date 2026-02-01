"""High-level API layer for DJ MP3 Renamer.

This module exposes all public API functions. UI layers (TUI, CLI) should
ONLY import from this module, never directly from core/.
"""

from .models import RenameRequest, RenameResult, RenameStatus
from .renamer import RenamerAPI

# Re-export commonly needed core utilities through API layer
# (maintains API-first architecture - UI should not import core directly)
from ..core.template import DEFAULT_TEMPLATE
from ..core.config import load_config, save_config, get_config_path
from ..core.io import find_mp3s

__all__ = [
    # Primary API
    "RenamerAPI",
    "RenameRequest",
    "RenameResult",
    "RenameStatus",
    # Configuration
    "load_config",
    "save_config",
    "get_config_path",
    # File Operations
    "find_mp3s",
    # Constants
    "DEFAULT_TEMPLATE",
]
