"""
Command-line interface (thin wrapper around API).
"""

import argparse
import sys
import warnings
from pathlib import Path
from typing import List, Optional

from ..api import RenamerAPI, RenameRequest
from ..core.template import DEFAULT_TEMPLATE
from .logging_config import configure_logging

# Suppress urllib3/LibreSSL warning on macOS
warnings.filterwarnings("ignore", message=".*LibreSSL.*")

# Rich for Supreme UX
try:
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeRemainingColumn,
    )

    RICH_AVAILABLE = True
except ImportError:  # pragma: no cover
    RICH_AVAILABLE = False


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
    parser.add_argument(
        "--no-recursive", action="store_false", dest="recursive", help="Do not recurse into subfolders"
    )
    # Default recursive to True
    parser.set_defaults(recursive=True)
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
            "Filename template. Available variables: {artist} {title} {mix} {bpm} {key} {camelot} "
            "{year} {label} {album} {track}. "
            f"Default: '{DEFAULT_TEMPLATE}'"
        ),
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze audio for BPM/Key (slower, reads entire file). Default: Tags only."
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

    # Initialize Console
    console = Console() if RICH_AVAILABLE else None

    # Clean path: remove shell escape characters (backslashes before spaces)
    path_str = str(args.path).replace("\\ ", " ")
    cleaned_path = Path(path_str)

    # Create API
    api = RenamerAPI(workers=args.workers, logger=logger)

    # Determine auto-detect mode (Default off, enabled by flag)
    auto_detect = args.analyze

    if RICH_AVAILABLE and args.verbosity < 2:
        # SUPREME UX: Rich Progress Bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),  # ETA
            TextColumn("[dim]{task.completed}/{task.total} files"),  # Count
            console=console,
        ) as progress:

            task_id = progress.add_task("Scanning...", total=None)

            def progress_callback(count: int, current_file: str):
                # Update progress
                if current_file == "Starting...":
                    return

                # If API sends "total", use it
                # For now, rely on API finding files first
                # But we can update description to show elapsed

                # Truncate filename for better UX
                display_name = Path(current_file).name
                if len(display_name) > 40:
                    display_name = display_name[:37] + "..."

                description = f"Processing [cyan]{display_name}[/cyan]"
                progress.update(task_id, completed=count, description=description)

                # If we have a count, we can guess total? No, safely leave total=None
                # until we figure out how to get total from API efficiently
                # without scanning twice.
                # Actually, RenamerAPI scans first.
                # Let's trust the user sees the spinner/bar growing.

            request = RenameRequest(
                path=cleaned_path,
                recursive=args.recursive,
                dry_run=args.dry_run,
                template=args.template,
                progress_callback=progress_callback,
                auto_detect=auto_detect,  # Respect --fast flag
            )

            # Execute
            status = api.rename_files(request)

            # Force 100% at end
            progress.update(task_id, total=status.total, completed=status.total, description="Done!")

    else:
        # Standard Mode (No Rich or Verbose)
        request = RenameRequest(
            path=cleaned_path,
            recursive=args.recursive,
            dry_run=args.dry_run,
            template=args.template,
            auto_detect=auto_detect,  # Respect --analyze flag
        )
        status = api.rename_files(request)

    if status.total == 0:
        if RICH_AVAILABLE and console:
            console.print("[bold red]No .mp3 files found[/bold red]")
        else:
            logger.error("No .mp3 files found")
        return 1

    # Print summary
    if RICH_AVAILABLE and console:
        # Beautiful Summary Table
        from rich.panel import Panel
        from rich.table import Table

        # Show detailed file changes if dry-run or verbose
        if args.dry_run or args.verbosity >= 1:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Status", width=8)
            table.add_column("Original", style="dim")
            table.add_column("New Name", style="green")

            for res in status.results:
                src_name = res.src.name if res.src else "?"
                dst_name = res.dst.name if res.dst else "?"
                if res.status == "renamed":
                    icon = "✅" if not args.dry_run else "🔍"
                    table.add_row(icon, src_name, dst_name)
                elif res.status == "skipped":
                    table.add_row("⏭️", src_name, f"[yellow]{res.message}[/yellow]")
                elif res.status == "error":
                    table.add_row("❌", src_name, f"[red]{res.message}[/red]")

            console.print(table)

        # Summary Panel
        summary = (
            f"[bold]Total Files:[/bold] {status.total}\n"
            f"[green]Renamed:[/green] {status.renamed}\n"
            f"[yellow]Skipped:[/yellow] {status.skipped}\n"
            f"[red]Errors:[/red]  {status.errors}"
        )
        color = "green" if status.errors == 0 else "red"
        title = "Crate Dry Run" if args.dry_run else "Crate Results"
        console.print(Panel(summary, title=f"[bold {color}]{title}[/]", border_style=color))

    elif args.verbosity >= 1:
        print(f"Done. Renamed: {status.renamed} | Skipped: {status.skipped} | Errors: {status.errors}")
        if args.dry_run:
            print("(Dry run - no files changed)")

    return 0 if status.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
