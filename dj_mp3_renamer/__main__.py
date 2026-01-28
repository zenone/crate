"""
Allow running as python -m dj_mp3_renamer
"""

import sys
from .cli.main import main

if __name__ == "__main__":
    sys.exit(main())
