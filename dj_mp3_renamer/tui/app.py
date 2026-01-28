"""
DJ MP3 Renamer - Terminal User Interface
Modern TUI using Textual framework - API-first architecture maintained
"""

from pathlib import Path
from typing import Optional
import time

from rich.syntax import Syntax
from rich.table import Table
from rich import box
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll, Center
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    Static,
    TabbedContent,
    TabPane,
)

# Import existing API (maintains API-first architecture)
from ..api import RenamerAPI, RenameRequest, RenameStatus
from ..core.template import DEFAULT_TEMPLATE


class StatsPanel(Static):
    """Display statistics panel."""

    def update_stats(self, total: int = 0, renamed: int = 0, skipped: int = 0, errors: int = 0):
        """Update statistics display."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="cyan")
        table.add_column("Value", style="bold white")

        table.add_row("Total Files:", str(total))
        table.add_row("To Rename:", f"[green]{renamed}[/green]")
        table.add_row("Skipped:", f"[yellow]{skipped}[/yellow]")
        table.add_row("Errors:", f"[red]{errors}[/red]")

        self.update(table)


class ResultsPanel(Static):
    """Display rename results."""

    def show_results(self, status: RenameStatus, is_preview: bool = True):
        """Display rename results with metadata."""
        mode = "PREVIEW" if is_preview else "COMPLETED"
        table = Table(
            title=f"Rename Results - {mode}",
            show_header=True,
            header_style="bold magenta",
            box=box.SIMPLE_HEAVY,  # Horizontal lines between rows for clarity
            row_styles=["", "dim"],  # Alternating row styles for better readability
        )

        table.add_column("Status", style="dim", width=8)
        table.add_column("Original", style="cyan", no_wrap=False)
        table.add_column("→", justify="center", width=3)
        table.add_column("New Name", style="green", no_wrap=False)
        table.add_column("BPM", justify="right", style="yellow", width=4)
        table.add_column("Key", justify="center", style="magenta", width=6)
        table.add_column("Year", justify="center", style="blue", width=4)
        table.add_column("Source", style="dim", width=6)

        # Show more results for better preview (increased from 50 to 200)
        display_limit = min(200, len(status.results))

        for result in status.results[:display_limit]:
            if result.status == "renamed":
                status_icon = "✓" if not is_preview else "→"
                status_style = "green"
            elif result.status == "skipped":
                status_icon = "⊘"
                status_style = "yellow"
            else:
                status_icon = "✗"
                status_style = "red"

            # Extract metadata for display
            meta = result.metadata or {}
            bpm = meta.get("bpm", "-")
            key = meta.get("key", "-")
            camelot = meta.get("camelot", "")
            key_display = f"{key} {camelot}" if camelot else key
            year = meta.get("year", "-")

            # Determine source (prioritize detection sources)
            bpm_source = meta.get("bpm_source", "ID3" if meta else "-")
            key_source = meta.get("key_source", "ID3" if meta else "-")

            # Show combined source or most relevant one
            if bpm_source == key_source:
                source = bpm_source
            elif bpm_source == "Analyzed" or key_source == "Analyzed":
                source = "Analyzed"
            elif bpm_source == "Database" or key_source == "Database":
                source = "Database"
            else:
                source = "ID3"

            table.add_row(
                f"[{status_style}]{status_icon}[/{status_style}]",
                result.src.name,
                "→" if result.dst else "",
                result.dst.name if result.dst else f"[dim]{result.message}[/dim]",
                bpm,
                key_display,
                year,
                source,
            )

        if len(status.results) > display_limit:
            table.add_row(
                "",
                f"[dim]... and {len(status.results) - display_limit} more files (scroll to see all)[/dim]",
                "", "", "", "", "", ""
            )

        self.update(table)


class ProgressOverlay(ModalScreen):
    """Modal overlay showing processing progress with real-time updates."""

    CSS = """
    ProgressOverlay {
        align: center middle;
    }

    #progress-container {
        width: 80;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 2;
    }

    #progress-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #progress-bar {
        margin: 1 0;
    }

    #progress-status {
        text-align: center;
        margin: 1 0;
    }

    #progress-current {
        text-align: center;
        color: $text-muted;
        text-style: italic;
        margin: 1 0;
    }

    #progress-time {
        text-align: center;
        color: $warning;
        margin: 1 0;
    }

    #progress-speed {
        text-align: center;
        color: $success;
        margin-top: 1;
    }
    """

    def __init__(self, title: str, total_files: int):
        super().__init__()
        self.title_text = title
        self.total_files = total_files
        self.processed = 0
        self.start_time = time.time()
        self.current_file = ""

    def compose(self) -> ComposeResult:
        """Create the progress overlay layout."""
        with Center():
            with Vertical(id="progress-container"):
                yield Label(self.title_text, id="progress-title")
                yield ProgressBar(total=self.total_files, show_eta=False, id="progress-bar")
                yield Label(f"Processing: 0 / {self.total_files} files", id="progress-status")
                yield Label("", id="progress-current")
                yield Label("Estimated time remaining: calculating...", id="progress-time")
                yield Label("", id="progress-speed")

    def update_progress(self, processed: int, current_file: str = ""):
        """Update progress bar and status text."""
        self.processed = processed
        self.current_file = current_file

        # Update progress bar
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.update(progress=processed)

        # Update status text
        status_label = self.query_one("#progress-status", Label)
        percentage = (processed / self.total_files * 100) if self.total_files > 0 else 0
        status_label.update(f"Processing: {processed} / {self.total_files} files ({percentage:.0f}%)")

        # Update current file
        current_label = self.query_one("#progress-current", Label)
        if current_file:
            # Truncate long filenames
            display_name = current_file if len(current_file) < 60 else current_file[:57] + "..."
            current_label.update(f"Current: {display_name}")
        else:
            current_label.update("")

        # Calculate time estimates
        elapsed = time.time() - self.start_time
        if processed > 0:
            files_per_second = processed / elapsed
            remaining_files = self.total_files - processed

            if files_per_second > 0:
                remaining_seconds = remaining_files / files_per_second
                remaining_minutes = remaining_seconds / 60

                time_label = self.query_one("#progress-time", Label)
                if remaining_minutes < 1:
                    time_label.update(f"Estimated time remaining: {int(remaining_seconds)} seconds")
                elif remaining_minutes < 60:
                    time_label.update(f"Estimated time remaining: {int(remaining_minutes)} minutes")
                else:
                    hours = int(remaining_minutes / 60)
                    minutes = int(remaining_minutes % 60)
                    time_label.update(f"Estimated time remaining: {hours}h {minutes}m")

                # Update speed
                speed_label = self.query_one("#progress-speed", Label)
                speed_label.update(f"Speed: {files_per_second:.1f} files/second")


class DJRenameTUI(App):
    """DJ MP3 Renamer Terminal User Interface."""

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        width: 100%;
        height: 100%;
    }

    #input-section {
        height: auto;
        padding: 1;
        border: solid $primary;
        margin: 1;
    }

    #results-section {
        height: 1fr;
        border: solid $accent;
        margin: 1;
        padding: 1;
    }

    #results-panel {
        width: 100%;
        height: auto;
        min-height: 10;
    }

    #stats-panel {
        height: auto;
        padding: 1;
        background: $boost;
        border: solid $primary;
        margin: 1;
    }

    Input {
        margin: 1 0;
    }

    Button {
        margin: 0 1;
    }

    DataTable {
        height: 1fr;
    }

    .section-title {
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }

    .help-text {
        color: $text-muted;
        text-style: italic;
    }

    #button-row {
        height: auto;
        width: 100%;
        align: center middle;
    }

    #browser-section {
        height: auto;
        max-height: 20;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }

    #browser-section.hidden {
        display: none;
    }

    DirectoryTree {
        height: 15;
        border: solid $accent;
    }

    #path-row {
        height: auto;
        width: 100%;
    }

    #path-input {
        width: 1fr;
    }

    #browse-btn {
        width: auto;
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("b", "browse", "Browse"),
        Binding("p", "preview", "Preview"),
        Binding("r", "rename", "Rename"),
        Binding("ctrl+r", "reset", "Reset"),
        ("?", "help", "Help"),
    ]

    def __init__(self):
        super().__init__()
        self.api = RenamerAPI(workers=4)
        self.current_path: Optional[Path] = None
        self.last_status: Optional[RenameStatus] = None

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()

        with Container(id="main-container"):
            # Input Section
            with Vertical(id="input-section"):
                yield Label("[bold cyan]🎵 DJ MP3 Renamer - Terminal UI[/bold cyan]", classes="section-title")

                yield Label("Directory Path (no backslashes needed):", classes="help-text")
                with Horizontal(id="path-row"):
                    yield Input(
                        placeholder="Enter path or use Browse button below",
                        id="path-input",
                    )
                    yield Button("Browse...", variant="default", id="browse-btn")

                # Directory Browser (hidden by default)
                with Vertical(id="browser-section", classes="hidden"):
                    yield Label("📁 Browse for directory (click to select):", classes="help-text")
                    yield DirectoryTree("/", id="dir-tree")

                yield Label("Template:", classes="help-text")
                yield Input(
                    value=DEFAULT_TEMPLATE,
                    placeholder="{artist} - {title}{mix_paren}{kb}",
                    id="template-input",
                )

                yield Checkbox("Recursive (include subfolders)", value=True, id="recursive-check")
                yield Checkbox("Auto-detect BPM/Key (if missing in ID3 tags)", value=True, id="autodetect-check")

                with Horizontal(id="button-row"):
                    yield Button("Preview (P)", variant="primary", id="preview-btn")
                    yield Button("Rename Files (R)", variant="success", id="rename-btn")
                    yield Button("Reset (Ctrl+R)", variant="default", id="reset-btn")
                    yield Button("Quit (Q)", variant="error", id="quit-btn")

            # Stats Panel
            yield StatsPanel(id="stats-panel")

            # Results Section
            with VerticalScroll(id="results-section"):
                yield ResultsPanel(id="results-panel")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app."""
        self.title = "DJ MP3 Renamer"
        self.sub_title = "API-First Terminal UI"

        # Focus the path input
        self.query_one("#path-input", Input).focus()

        # Show initial help
        stats = self.query_one("#stats-panel", StatsPanel)
        stats.update("[dim]Enter a directory path and press Preview (P) to see changes[/dim]")

        # Initialize results panel
        results = self.query_one("#results-panel", ResultsPanel)
        results.update("[dim]No preview yet - enter a path and press Preview to see what will change[/dim]")

    def action_browse(self) -> None:
        """Toggle directory browser (keyboard shortcut)."""
        self.toggle_browser()

    @on(Button.Pressed, "#browse-btn")
    def toggle_browser(self) -> None:
        """Toggle directory browser visibility."""
        browser = self.query_one("#browser-section")
        if "hidden" in browser.classes:
            browser.remove_class("hidden")
            self.notify("Browse and click on a directory to select it", timeout=3)
        else:
            browser.add_class("hidden")

    @on(DirectoryTree.DirectorySelected)
    def directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """Handle directory selection from browser."""
        path_input = self.query_one("#path-input", Input)
        path_input.value = str(event.path)

        # Keep browser open for easier navigation
        # User can close it by pressing B or clicking Browse button again
        self.notify(f"Selected: {event.path} (Browser stays open - press B to close)", severity="information", timeout=3)

    @on(Button.Pressed, "#preview-btn")
    async def action_preview(self) -> None:
        """Preview rename operation."""
        # Close browser if open to make room for results
        browser = self.query_one("#browser-section")
        if "hidden" not in browser.classes:
            browser.add_class("hidden")

        await self._process_files(dry_run=True)

        # Scroll to results section
        results_section = self.query_one("#results-section")
        results_section.scroll_visible()

    @on(Button.Pressed, "#rename-btn")
    async def action_rename(self) -> None:
        """Execute rename operation."""
        if not self.last_status:
            self.notify("Run Preview first to see what will change", severity="warning")
            return

        # Close browser if open to make room for results
        browser = self.query_one("#browser-section")
        if "hidden" not in browser.classes:
            browser.add_class("hidden")

        # Confirm
        self.notify("Renaming files...", severity="information")
        await self._process_files(dry_run=False)

        # Scroll to results section
        results_section = self.query_one("#results-section")
        results_section.scroll_visible()

    @on(Button.Pressed, "#reset-btn")
    def action_reset(self) -> None:
        """Reset the form."""
        self.query_one("#path-input", Input).value = ""
        self.query_one("#template-input", Input).value = DEFAULT_TEMPLATE
        self.query_one("#recursive-check", Checkbox).value = True
        self.query_one("#autodetect-check", Checkbox).value = True

        stats = self.query_one("#stats-panel", StatsPanel)
        stats.update("[dim]Ready for new directory[/dim]")

        results = self.query_one("#results-panel", ResultsPanel)
        results.update("[dim]No results yet[/dim]")

        self.last_status = None
        self.query_one("#path-input", Input).focus()

    @on(Button.Pressed, "#quit-btn")
    def handle_quit_button(self) -> None:
        """Handle quit button press."""
        self.exit()

    async def _process_files(self, dry_run: bool = True) -> None:
        """Process files using the API."""
        # Get inputs
        path_input = self.query_one("#path-input", Input).value.strip()
        template = self.query_one("#template-input", Input).value.strip()
        recursive = self.query_one("#recursive-check", Checkbox).value
        auto_detect = self.query_one("#autodetect-check", Checkbox).value

        if not path_input:
            self.notify("Please enter a directory path", severity="error")
            return

        # Expand and validate path
        try:
            path = Path(path_input).expanduser().resolve()
            if not path.exists():
                self.notify(f"Path does not exist: {path}", severity="error")
                return
            if not path.is_dir():
                self.notify(f"Path is not a directory: {path}", severity="error")
                return
        except Exception as e:
            self.notify(f"Invalid path: {e}", severity="error")
            return

        self.current_path = path

        # Quick file count estimation for progress
        from ..core.io import find_mp3s
        mp3_files = find_mp3s(path, recursive=recursive)
        file_count = len(mp3_files)

        if file_count == 0:
            self.notify("No MP3 files found in directory", severity="warning")
            return

        # Show progress overlay
        mode = "Previewing Changes" if dry_run else "Renaming Files"
        progress_screen = ProgressOverlay(mode, file_count)

        def progress_callback(processed: int, filename: str):
            """Update progress overlay from API callback."""
            try:
                if progress_screen in self.screen_stack:
                    progress_screen.update_progress(processed, filename)
            except Exception:
                pass  # Ignore errors updating progress

        # Push progress overlay
        await self.push_screen(progress_screen)

        # Call the API in background (maintains API-first architecture)
        try:
            request = RenameRequest(
                path=path,
                recursive=recursive,
                dry_run=dry_run,
                template=template or DEFAULT_TEMPLATE,
                auto_detect=auto_detect,
                progress_callback=progress_callback,
            )

            # Run API call (blocking but progress overlay remains responsive)
            status = await self.run_in_executor(None, self.api.rename_files, request)
            self.last_status = status

            # Dismiss progress overlay
            self.pop_screen()

            # Update UI
            stats = self.query_one("#stats-panel", StatsPanel)
            stats.update_stats(
                total=status.total,
                renamed=status.renamed,
                skipped=status.skipped,
                errors=status.errors,
            )

            results = self.query_one("#results-panel", ResultsPanel)
            results.show_results(status, is_preview=dry_run)

            # Notify
            if dry_run:
                self.notify(
                    f"Preview complete: {status.renamed} files will be renamed, {status.skipped} skipped",
                    severity="information",
                    timeout=5
                )
            else:
                self.notify(
                    f"✓ Successfully renamed {status.renamed} files!",
                    severity="success",
                    timeout=5
                )

        except Exception as e:
            # Dismiss progress overlay on error
            try:
                self.pop_screen()
            except Exception:
                pass

            self.notify(f"Error: {e}", severity="error")
            self.log.error(f"Processing error: {e}", exc_info=True)


def run_tui():
    """Launch the Terminal UI."""
    app = DJRenameTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
