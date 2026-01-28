"""
Logging configuration for CLI.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def configure_logging(log_path: Optional[Path], verbosity: int) -> logging.Logger:
    """
    Configure logging for the CLI.

    Args:
        log_path: Optional path to log file
        verbosity: Verbosity level (0 = errors only, 1 = info, 2+ = debug)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("dj_mp3_renamer")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if run in an interactive session
    if logger.handlers:
        logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(
        logging.ERROR if verbosity <= 0 else (logging.INFO if verbosity == 1 else logging.DEBUG)
    )
    console.setFormatter(fmt)
    logger.addHandler(console)

    if log_path:
        fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger
