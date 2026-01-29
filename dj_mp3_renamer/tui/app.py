"""
DJ MP3 Renamer - Terminal User Interface
Modern TUI using Textual framework - API-first architecture maintained
"""

from pathlib import Path
from typing import Optional
import asyncio
import threading
import time

from rich.syntax import Syntax
from rich.table import Table
from rich import box
from textual import on, work
from textual.worker import get_current_worker
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

# Import ONLY from API layer (maintains API-first architecture)
# TUI should NEVER import from core/ directly
from ..api import (
    RenamerAPI,
    RenameRequest,
    RenameStatus,
    DEFAULT_TEMPLATE,
    load_config,
    save_config,
    get_config_path,
)


class OperationCancelled(Exception):
    """Raised when user cancels a long-running operation."""
    pass


class SettingsScreen(ModalScreen):
    """Modal screen for managing user settings."""

    CSS = """
    SettingsScreen {
        align: center middle;
    }

    #settings-container {
        width: 90;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 2;
    }

    #settings-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .setting-label {
        margin-top: 1;
        margin-bottom: 0;
        color: $text;
    }

    .setting-help {
        margin-bottom: 1;
        color: $text-muted;
        text-style: italic;
    }

    #settings-buttons {
        margin-top: 2;
        align: center middle;
    }

    .validation-error {
        color: $error;
        text-style: italic;
        margin-bottom: 1;
    }
    """

    def __init__(self, is_first_run: bool = False):
        super().__init__()
        self.config = load_config()
        self.is_first_run = is_first_run

    def compose(self) -> ComposeResult:
        """Create the settings layout."""
        with Center():
            with Vertical(id="settings-container"):
                if self.is_first_run:
                    yield Label("🎉 Welcome to DJ MP3 Renamer!", id="settings-title")
                    yield Static(
                        "[bold cyan]First-time setup - Let's configure your preferences[/bold cyan]\n"
                        "[dim]You can change these settings anytime from the Settings menu[/dim]",
                        classes="setting-help"
                    )
                else:
                    yield Label("⚙️ Settings", id="settings-title")

                # Validation error display (hidden by default)
                yield Static("", id="validation-error", classes="validation-error")

                yield Label("AcoustID API Key (Optional):", classes="setting-label")
                yield Static(
                    "[dim]For MusicBrainz database lookups to find metadata.\n"
                    "• Default: Public key (works but has rate limits)\n"
                    "• Your own key: Get free at https://acoustid.org/api-key (no limits)[/dim]",
                    classes="setting-help"
                )
                yield Input(
                    value=self.config.get("acoustid_api_key", ""),
                    placeholder="8XaBELgH (default public key - leave blank to use default)",
                    id="api-key-input"
                )

                yield Label("MusicBrainz Database Lookup:", classes="setting-label")
                yield Static(
                    "[dim]Try database before audio analysis (faster but limited BPM/Key coverage)[/dim]",
                    classes="setting-help"
                )
                yield Checkbox(
                    "Enable MusicBrainz lookup",
                    value=self.config.get("enable_musicbrainz", False),
                    id="musicbrainz-check"
                )
                yield Checkbox(
                    "Use MusicBrainz to correct Artist/Title/Album",
                    value=self.config.get("use_mb_for_all_fields", True),
                    id="mb-all-fields-check"
                )

                yield Label("Advanced Options:", classes="setting-label")
                yield Static(
                    "[dim]Verify mode re-analyzes even if tags exist (slower but validates data)[/dim]",
                    classes="setting-help"
                )
                yield Checkbox(
                    "Verify Mode (re-analyze all files)",
                    value=self.config.get("verify_mode", False),
                    id="verify-mode-check"
                )

                yield Label("Auto-Detection Preferences:", classes="setting-label")
                yield Static(
                    "[dim]Choose what to auto-detect when missing from ID3 tags[/dim]",
                    classes="setting-help"
                )
                yield Checkbox(
                    "Auto-detect BPM",
                    value=self.config.get("auto_detect_bpm", True),
                    id="auto-bpm-check"
                )
                yield Checkbox(
                    "Auto-detect Key",
                    value=self.config.get("auto_detect_key", True),
                    id="auto-key-check"
                )

                with Horizontal(id="settings-buttons"):
                    save_label = "Get Started" if self.is_first_run else "Save Settings"
                    cancel_label = "Set Defaults" if self.is_first_run else "Cancel"
                    yield Button(save_label, variant="success", id="save-settings-btn")
                    if not self.is_first_run:
                        yield Button(cancel_label, variant="default", id="cancel-settings-btn")

    @on(Button.Pressed, "#save-settings-btn")
    def save_settings(self) -> None:
        """Save settings to config file with validation."""
        # Get values from inputs
        api_key = self.query_one("#api-key-input", Input).value.strip()
        enable_mb = self.query_one("#musicbrainz-check", Checkbox).value
        use_mb_all = self.query_one("#mb-all-fields-check", Checkbox).value
        verify_mode = self.query_one("#verify-mode-check", Checkbox).value
        auto_bpm = self.query_one("#auto-bpm-check", Checkbox).value
        auto_key = self.query_one("#auto-key-check", Checkbox).value

        # Validation: At least one detection method should be enabled
        error_msg = ""
        if not auto_bpm and not auto_key and not enable_mb:
            error_msg = "⚠️  Warning: All auto-detection options are disabled. Files without metadata won't be renamed."
            if self.is_first_run:
                # For first-run, show error and don't save
                validation_error = self.query_one("#validation-error", Static)
                validation_error.update(error_msg)
                self.app.notify(error_msg, severity="warning", timeout=5)
                return

        # Clear validation error if all is good
        validation_error = self.query_one("#validation-error", Static)
        validation_error.update("")

        # Update config
        self.config["acoustid_api_key"] = api_key or "8XaBELgH"
        self.config["enable_musicbrainz"] = enable_mb
        self.config["use_mb_for_all_fields"] = use_mb_all
        self.config["verify_mode"] = verify_mode
        self.config["auto_detect_bpm"] = auto_bpm
        self.config["auto_detect_key"] = auto_key

        # Save to file
        if save_config(self.config):
            success_msg = "✓ Setup complete! You can now use the app." if self.is_first_run else "✓ Settings saved successfully!"
            self.app.notify(success_msg, severity="information", timeout=3)
            # Reload config in API
            self.app.api.config = load_config()
            self.dismiss()
        else:
            self.app.notify("Failed to save settings", severity="error", timeout=3)

    def action_dismiss(self) -> None:
        """Override dismiss action to prevent closing during first run."""
        if self.is_first_run:
            self.app.notify("⚠️  Please complete setup to use the app", severity="warning", timeout=3)
        else:
            self.dismiss()

    @on(Button.Pressed, "#cancel-settings-btn")
    def cancel_settings(self) -> None:
        """Close settings without saving."""
        if self.is_first_run:
            # First run - can't cancel, must configure
            self.app.notify("⚠️  Please complete setup to use the app", severity="warning", timeout=3)
        else:
            # Regular settings - can cancel
            self.dismiss()


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
            box=box.ROUNDED,  # Rounded box style
            show_lines=True,  # Show horizontal lines between every row
            row_styles=["", "dim"],  # Alternating row styles for better readability
            caption="[dim italic]Source Legend: Tags=ID3 metadata | AI Audio=Auto-detected via audio analysis | MusicBrainz=Database lookup[/dim italic]",
            caption_justify="left",
        )

        # Row number column for verification and accessibility
        table.add_column("#", justify="right", style="dim", width=4)
        table.add_column("Status", style="dim", width=3)
        table.add_column("Original", style="cyan", no_wrap=False)
        table.add_column("→", justify="center", width=3)
        table.add_column("New Name", style="green", no_wrap=False)
        table.add_column("BPM", justify="right", style="yellow", width=4)
        table.add_column("Key", justify="center", style="magenta", width=6)
        table.add_column("Year", justify="center", style="blue", width=4)
        table.add_column("Source", style="dim", width=10)

        # Show more results for better preview (increased from 50 to 200)
        display_limit = min(200, len(status.results))

        for idx, result in enumerate(status.results[:display_limit], start=1):
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
            bpm_source = meta.get("bpm_source", "Tags" if meta else "-")
            key_source = meta.get("key_source", "Tags" if meta else "-")

            # Map internal names to user-friendly display names
            source_map = {
                "Analyzed": "AI Audio",
                "Database": "MusicBrainz",
                "MusicBrainz": "MusicBrainz",  # Direct return from audio_analysis
                "ID3": "Tags",
                "Failed": "Failed",
                "Unavailable": "N/A",
            }

            # Show combined source or most relevant one
            if bpm_source == key_source:
                raw_source = bpm_source
            elif bpm_source == "Analyzed" or key_source == "Analyzed":
                raw_source = "Analyzed"
            elif bpm_source == "Database" or key_source == "Database":
                raw_source = "Database"
            else:
                raw_source = "ID3"

            # Convert to user-friendly name
            source = source_map.get(raw_source, raw_source)

            table.add_row(
                str(idx),  # Row number for verification
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

    BINDINGS = [
        Binding("c", "cancel", "Cancel", show=False),
    ]

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

    #cancel-btn {
        margin-top: 2;
    }
    """

    def __init__(self, title: str, total_files: int):
        super().__init__()
        self.title_text = title
        self.total_files = total_files
        self.processed = 0
        self.start_time = time.time()
        self.current_file = ""
        self.cancelled = threading.Event()  # Thread-safe cancellation flag

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
                with Center():
                    yield Button("Cancel (C)", variant="error", id="cancel-btn")

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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events (standard ModalScreen pattern)."""
        # AGGRESSIVE DEBUGGING - print to stdout AND log
        import sys
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"on_button_pressed CALLED!", file=sys.stderr)
        print(f"Button ID: {event.button.id}", file=sys.stderr)
        print(f"Looking for: cancel-btn", file=sys.stderr)
        print(f"Match: {event.button.id == 'cancel-btn'}", file=sys.stderr)
        print(f"{'='*60}\n", file=sys.stderr)

        self.app.log.warning(f"🔍 on_button_pressed called with button.id={event.button.id}")

        if event.button.id == "cancel-btn":
            print(f"\n🖱️  CANCEL BUTTON CLICKED - SETTING FLAG\n", file=sys.stderr)
            self.app.log.warning("🖱️  CANCEL BUTTON CLICKED - setting cancelled flag")
            self.cancelled.set()  # Signal cancellation
            self.app.notify("Cancelling operation...", severity="warning", timeout=2)
            # DO NOT dismiss here - let the exception handling in _process_files dismiss it
            # Dismissing immediately removes from screen_stack and breaks cancellation check
            event.stop()  # Stop event propagation

    def action_cancel(self) -> None:
        """Handle 'c' key press to cancel."""
        import sys
        print(f"\n⌨️  'C' KEY PRESSED - SETTING FLAG\n", file=sys.stderr)
        self.app.log.warning("⌨️  'C' KEY PRESSED - setting cancelled flag")
        self.cancelled.set()
        print(f"   Flag is_set: {self.cancelled.is_set()}\n", file=sys.stderr)
        self.app.notify("Cancelling operation...", severity="warning", timeout=2)


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

    #template-helper {
        color: $text-muted;
        text-style: italic;
        margin: 0 0 1 0;
        padding: 0 1;
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
                    placeholder="{artist} - {title} [{camelot} {bpm}]",
                    id="template-input",
                )

                # Template variable helper
                yield Static(
                    "[dim italic]Available variables: "
                    "{artist} {title} {bpm} {key} {camelot} {mix} {year} {album} {label} {track}"
                    "[/dim italic]",
                    id="template-helper"
                )

                yield Checkbox("Recursive (include subfolders)", value=True, id="recursive-check")
                yield Checkbox("Auto-detect BPM/Key (if missing in ID3 tags)", value=True, id="autodetect-check")

                with Horizontal(id="button-row"):
                    yield Button("Preview (P)", variant="primary", id="preview-btn")
                    yield Button("Rename Files (R)", variant="success", id="rename-btn")
                    yield Button("Settings", variant="default", id="settings-btn")
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

        # Check if this is first run (config file doesn't exist)
        config_path = get_config_path()
        is_first_run = not config_path.exists()

        if is_first_run:
            # Show first-run setup dialog
            self.push_screen(SettingsScreen(is_first_run=True))
        else:
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

    @on(Button.Pressed, "#settings-btn")
    async def handle_settings_button(self) -> None:
        """Handle settings button press."""
        await self.push_screen(SettingsScreen())

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

        # Remove shell escape characters (backslashes before spaces)
        # This allows users to paste paths like: /Volumes/Drive/Shared\ Music/Incoming
        # and have them work without manual editing
        path_input = path_input.replace("\\ ", " ")

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
        from ..api import find_mp3s
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
            # Check if user cancelled the operation
            is_cancelled = progress_screen.cancelled.is_set()

            # AGGRESSIVE DEBUGGING - check EVERY call
            import sys
            if processed % 5 == 0 or is_cancelled:  # More frequent logging
                print(f"📊 progress_callback: processed={processed}, cancelled={is_cancelled}", file=sys.stderr)
                self.log.debug(f"progress_callback: processed={processed}, cancelled={is_cancelled}")

            if is_cancelled:
                print(f"\n⚠️  CANCELLATION DETECTED - RAISING EXCEPTION\n", file=sys.stderr)
                self.log.warning(f"⚠️  CANCELLATION DETECTED - raising OperationCancelled")
                raise OperationCancelled("User cancelled the operation")

            try:
                if progress_screen in self.screen_stack:
                    progress_screen.update_progress(processed, filename)
            except OperationCancelled:
                raise  # Re-raise cancellation
            except Exception:
                pass  # Ignore other errors updating progress

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

            # Use Textual's run_worker with thread=True to keep UI responsive
            # This allows button clicks and key presses to be processed during execution
            import sys
            print("🔄 Starting worker thread...", file=sys.stderr)

            # Create a wrapper that stores the result
            result_container = {}

            def worker_func():
                """Worker function that runs in background thread."""
                try:
                    result = self.api.rename_files(request)
                    result_container['status'] = result
                    result_container['error'] = None
                except Exception as e:
                    result_container['status'] = None
                    result_container['error'] = e

            # Run in background thread (UI stays responsive!)
            worker = self.run_worker(
                worker_func,
                thread=True,
                name="file_processor",
                exclusive=True
            )

            # Poll worker status while checking for cancellation
            # DO NOT use await worker.wait() - it blocks the event loop!
            print("🔄 Polling worker status (checking cancellation)...", file=sys.stderr)

            poll_count = 0
            while not worker.is_finished:
                poll_count += 1
                if poll_count % 10 == 0:
                    print(f"  Poll #{poll_count}: worker running, cancelled={progress_screen.cancelled.is_set()}", file=sys.stderr)

                # Check if user cancelled
                if progress_screen.cancelled.is_set():
                    print("⚠️  CANCELLATION DETECTED IN POLL LOOP", file=sys.stderr)
                    # Worker will stop naturally when it checks the flag
                    break

                # Yield control to event loop (allows button events to be processed!)
                await self.app.animator.wait_for_idle()

            print(f"✅ Worker finished after {poll_count} polls", file=sys.stderr)

            # Check result
            if result_container.get('error'):
                raise result_container['error']

            status = result_container['status']
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

        except OperationCancelled:
            # User cancelled - dismiss overlay and notify
            try:
                self.pop_screen()
            except Exception:
                pass

            self.notify("Operation cancelled by user", severity="warning", timeout=3)
            self.log.info("User cancelled operation")

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
