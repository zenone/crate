"""
Command-line interface (thin wrapper around API).
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

try:
    from mutagen import File as MutagenFile  # type: ignore
except Exception:  # pragma: no cover
    MutagenFile = None  # type: ignore

try:
    from tqdm import tqdm  # type: ignore
except Exception:  # pragma: no cover
    tqdm = None  # type: ignore

from ..api import RenamerAPI, RenameRequest
from ..core.template import DEFAULT_TEMPLATE
from .logging_config import configure_logging


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        argv: Optional argument list (for testing)

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Rename MP3 files using metadata into DJ-friendly filenames."
    )
    parser.add_argument("path", type=Path, help="File or directory to process")
    parser.add_argument("--recursive", action="store_true", help="Recurse into subfolders")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would change, but do not rename files"
    )
    parser.add_argument(
        "--workers", type=int, default=4, help="Number of worker threads (default: 4)"
    )
    parser.add_argument("-l", "--log", type=Path, default=None, help="Write detailed log to a file")
    parser.add_argument(
        "-v", "--verbosity", action="count", default=0, help="Increase verbosity (-v, -vv)"
    )
    parser.add_argument(
        "--template",
        type=str,
        default=DEFAULT_TEMPLATE,
        help=(
            "Filename template. Tokens: {artist} {title} {mix} {mix_paren} {bpm} {key} {camelot} "
            "{year} {label} {album} {track} {kb}. "
            "Default: '{artist} - {title}{mix_paren}{kb}'"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for CLI.

    Args:
        argv: Optional argument list (for testing)

    Returns:
        Exit code (0 = success, 1 = errors, 2 = missing dependencies)
    """
    args = parse_args(argv)
    logger = configure_logging(args.log, args.verbosity)

    if MutagenFile is None:
        logger.error("Missing dependency: mutagen. Install with: pip3 install mutagen")
        return 2

    if tqdm is None:
        logger.error("Missing dependency: tqdm. Install with: pip3 install tqdm")
        return 2

    # Create API and request
    api = RenamerAPI(workers=args.workers, logger=logger)
    request = RenameRequest(
        path=args.path,
        recursive=args.recursive,
        dry_run=args.dry_run,
        template=args.template,
    )

    # Execute rename
    status = api.rename_files(request)

    if status.total == 0:
        logger.error("No .mp3 files found")
        return 1

    # Show progress bar if tqdm available and not too verbose
    if tqdm and args.verbosity < 2:
        # Progress bar is handled by showing results at end
        pass

    # Print summary
    if args.verbosity >= 1:
        print(f"Done. Renamed: {status.renamed} | Skipped: {status.skipped} | Errors: {status.errors}")
        if args.dry_run:
            print("(Dry run - no files changed)")

    return 0 if status.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
