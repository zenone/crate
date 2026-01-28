#!/usr/bin/env python3
"""
Launch script for DJ MP3 Renamer Terminal UI.

Usage:
    python run_tui.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dj_mp3_renamer.tui import run_tui

if __name__ == "__main__":
    run_tui()
