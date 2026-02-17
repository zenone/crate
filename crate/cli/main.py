"""
Command-line interface (thin wrapper around API).
"""

import argparse
import shutil
import subprocess
import sys
import warnings
from pathlib import Path
from typing import List, Optional

from ..api import RenamerAPI, RenameRequest
from ..api.cue_detection import CueDetectionAPI, CueDetectionRequest
from ..api.normalization import NormalizationAPI, NormalizationMode, NormalizationRequest
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

    # Phase 1: Normalization
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="Analyze/normalize volume levels (LUFS measurement)."
    )
    parser.add_argument(
        "--normalize-mode",
        choices=["analyze", "tag", "apply"],
        default="analyze",
        help="Normalization mode: analyze (measure only), tag (write ReplayGain), apply (modify audio). Default: analyze."
    )
    parser.add_argument(
        "--target-lufs",
        type=float,
        default=-14.0,
        help="Target loudness in LUFS (default: -14.0, streaming standard)."
    )

    # Phase 2: Cue Detection
    parser.add_argument(
        "--detect-cues",
        action="store_true",
        help="Detect hot cue points (intro, drops, breakdowns)."
    )
    parser.add_argument(
        "--export-cues",
        type=Path,
        default=None,
        help="Export detected cues to Rekordbox XML file."
    )
    parser.add_argument(
        "--cue-sensitivity",
        type=float,
        default=0.5,
        help="Cue detection sensitivity (0.0-1.0). Higher = more cues. Default: 0.5."
    )

    return parser.parse_args(argv)


def _preflight_optional_deps_for_analyze(logger, console) -> None:
    """Preflight optional system dependencies for analyze mode.

    Goal: premium UX. If a user requests analyze mode and optional tooling is
    missing, tell them clearly up-front (before progress UI starts).

    This is best-effort and should never block rename functionality.
    """
    if sys.platform != "darwin":
        return

    if shutil.which("fpcalc") is not None:
        return

    brew = shutil.which("brew")
    cmd = "brew install chromaprint"

    # If we can't install automatically, at least show exact command.
    if not brew:
        msg = (
            "Optional dependency missing: fpcalc (Chromaprint). "
            "Fingerprint lookup is disabled.\n"
            "Install Homebrew, then run: brew install chromaprint"
        )
        if console:
            console.print(f"[yellow]{msg}[/yellow]")
        else:
            logger.warning(msg)
        return

    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if not interactive:
        msg = (
            "Optional dependency missing: fpcalc (Chromaprint). "
            "Fingerprint lookup is disabled in this run.\n"
            f"To enable it, run: {cmd}"
        )
        if console:
            console.print(f"[yellow]{msg}[/yellow]")
        else:
            logger.warning(msg)
        return

    # Interactive: ask once, before any progress UI.
    if console:
        console.print(
            "[yellow]Optional dependency missing: fpcalc (Chromaprint).[/yellow]\n"
            "This enables audio fingerprint lookups."
        )
        console.print(f"Run now? [bold]{cmd}[/bold]")
    else:
        logger.warning("Optional dependency missing: fpcalc (Chromaprint).")
        logger.warning(f"To enable fingerprint lookup, run: {cmd}")

    try:
        ans = input("Install Chromaprint now? [Y/n] ").strip().lower()
    except Exception:
        ans = "n"

    if ans not in ("", "y", "yes"):
        return

    try:
        # Use explicit brew path from which(); do not assume PATH inside subprocess.
        r = subprocess.run([brew, "install", "chromaprint"], check=False)
        if r.returncode != 0:
            if console:
                console.print("[red]Chromaprint install failed.[/red]")
            else:
                logger.warning("Chromaprint install failed")
    except Exception as e:
        if console:
            console.print(f"[red]Chromaprint install failed: {e}[/red]")
        else:
            logger.warning(f"Chromaprint install failed: {e}")


def _run_normalize(args, logger, console, path: Path) -> int:
    """Run normalization mode.

    Args:
        args: Parsed arguments
        logger: Logger instance
        console: Rich console (or None)
        path: Path to process

    Returns:
        Exit code
    """
    api = NormalizationAPI(logger=logger)

    # Map mode string to enum
    mode_map = {
        "analyze": NormalizationMode.ANALYZE,
        "tag": NormalizationMode.TAG,
        "apply": NormalizationMode.APPLY,
    }
    mode = mode_map[args.normalize_mode]

    request = NormalizationRequest(
        paths=[path],
        mode=mode,
        target_lufs=args.target_lufs,
        prevent_clipping=True,
        recursive=args.recursive,
    )

    if console:
        console.print(f"[bold blue]Analyzing loudness...[/bold blue] (target: {args.target_lufs} LUFS)")
    else:
        logger.info(f"Analyzing loudness (target: {args.target_lufs} LUFS)")

    status = api.normalize(request)

    if status.total == 0:
        if console:
            console.print("[bold red]No audio files found[/bold red]")
        else:
            logger.error("No audio files found")
        return 1

    # Print results
    if RICH_AVAILABLE and console:
        from rich.panel import Panel
        from rich.table import Table

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("File", style="cyan")
        table.add_column("LUFS", justify="right")
        table.add_column("Peak dB", justify="right")
        table.add_column("Adjustment", justify="right")
        table.add_column("Status")

        for result in status.results:
            if result.success:
                lufs_str = f"{result.original_lufs:.1f}" if result.original_lufs else "?"
                peak_str = f"{result.original_peak_db:.1f}" if result.original_peak_db else "?"
                adj_str = f"{result.adjustment_db:+.1f} dB" if result.adjustment_db else "N/A"
                clip_note = " [yellow](limited)[/yellow]" if result.clipping_prevented else ""
                status_str = f"[green]✅{clip_note}[/green]"
            else:
                lufs_str = "?"
                peak_str = "?"
                adj_str = "?"
                status_str = f"[red]❌ {result.error}[/red]"

            table.add_row(
                result.path.name[:40],
                lufs_str,
                peak_str,
                adj_str,
                status_str
            )

        console.print(table)

        mode_desc = {
            NormalizationMode.ANALYZE: "Analyzed (no changes)",
            NormalizationMode.TAG: "ReplayGain tags written",
            NormalizationMode.APPLY: "Audio modified",
        }

        summary = (
            f"[bold]Files:[/bold] {status.total}\n"
            f"[green]Succeeded:[/green] {status.succeeded}\n"
            f"[red]Failed:[/red] {status.failed}\n"
            f"[bold]Mode:[/bold] {mode_desc[mode]}"
        )
        color = "green" if status.failed == 0 else "red"
        console.print(Panel(summary, title=f"[bold {color}]Normalization Results[/]", border_style=color))
    else:
        logger.info(f"Processed {status.total} files: {status.succeeded} succeeded, {status.failed} failed")

    return 0 if status.failed == 0 else 1


def _run_cue_detection(args, logger, console, path: Path) -> int:
    """Run cue detection mode.

    Args:
        args: Parsed arguments
        logger: Logger instance
        console: Rich console (or None)
        path: Path to process

    Returns:
        Exit code
    """
    api = CueDetectionAPI(logger=logger)

    request = CueDetectionRequest(
        paths=[path],
        detect_intro=True,
        detect_drops=True,
        detect_breakdowns=True,
        max_cues=8,
        sensitivity=args.cue_sensitivity,
        recursive=args.recursive,
    )

    if console:
        console.print(f"[bold blue]Detecting cue points...[/bold blue] (sensitivity: {args.cue_sensitivity})")
    else:
        logger.info(f"Detecting cue points (sensitivity: {args.cue_sensitivity})")

    status = api.detect(request)

    if status.total == 0:
        if console:
            console.print("[bold red]No audio files found[/bold red]")
        else:
            logger.error("No audio files found")
        return 1

    # Print results
    if RICH_AVAILABLE and console:
        from rich.panel import Panel
        from rich.table import Table

        for result in status.results:
            if not result.success:
                console.print(f"[red]❌ {result.path.name}: {result.error}[/red]")
                continue

            console.print(f"\n[bold cyan]{result.path.name}[/bold cyan]")
            if result.bpm:
                console.print(f"  BPM: {result.bpm:.1f}")
            if result.duration_ms:
                duration_sec = result.duration_ms / 1000
                console.print(f"  Duration: {int(duration_sec // 60)}:{int(duration_sec % 60):02d}")

            if result.cues:
                table = Table(show_header=True, header_style="bold")
                table.add_column("#", width=3)
                table.add_column("Type", width=12)
                table.add_column("Position", justify="right")
                table.add_column("Label")

                for cue in result.cues:
                    pos_sec = cue.position_ms / 1000
                    pos_str = f"{int(pos_sec // 60)}:{pos_sec % 60:05.2f}"

                    type_colors = {
                        "intro": "green",
                        "drop": "red",
                        "breakdown": "blue",
                        "build": "yellow",
                        "outro": "magenta",
                    }
                    color = type_colors.get(cue.cue_type.value, "white")

                    table.add_row(
                        str(cue.hot_cue_index or "-"),
                        f"[{color}]{cue.cue_type.value}[/{color}]",
                        pos_str,
                        cue.label or ""
                    )

                console.print(table)
            else:
                console.print("  [yellow]No cues detected[/yellow]")

        summary = (
            f"[bold]Files:[/bold] {status.total}\n"
            f"[green]Succeeded:[/green] {status.succeeded}\n"
            f"[red]Failed:[/red] {status.failed}"
        )
        color = "green" if status.failed == 0 else "red"
        console.print(Panel(summary, title=f"[bold {color}]Cue Detection Results[/]", border_style=color))
    else:
        logger.info(f"Processed {status.total} files: {status.succeeded} succeeded, {status.failed} failed")
        for result in status.results:
            if result.success:
                logger.info(f"{result.path.name}: {len(result.cues)} cues detected")

    # Export to Rekordbox if requested
    if args.export_cues:
        success = api.export_rekordbox(status.results, args.export_cues)
        if success:
            if console:
                console.print(f"[green]✅ Exported to {args.export_cues}[/green]")
            else:
                logger.info(f"Exported to {args.export_cues}")
        else:
            if console:
                console.print(f"[red]❌ Failed to export to {args.export_cues}[/red]")
            else:
                logger.error(f"Failed to export to {args.export_cues}")
            return 1

    return 0 if status.failed == 0 else 1


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

    # Handle normalization mode
    if args.normalize:
        return _run_normalize(args, logger, console, cleaned_path)

    # Handle cue detection mode
    if args.detect_cues:
        return _run_cue_detection(args, logger, console, cleaned_path)

    # Create API
    api = RenamerAPI(workers=args.workers, logger=logger)

    # Determine auto-detect mode (Default off, enabled by flag)
    auto_detect = args.analyze

    # Preflight optional dependencies for analyze mode (do this before Rich progress starts).
    if auto_detect:
        _preflight_optional_deps_for_analyze(logger, console)

    if RICH_AVAILABLE and args.verbosity < 2:
        # SUPREME UX: Rich Progress Bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),  # ETA
            # When total is unknown, Rich shows "None"; keep it clean.
            TextColumn("[dim]{task.completed} files"),  # Count
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
