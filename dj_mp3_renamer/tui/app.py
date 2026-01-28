"""
DJ MP3 Renamer - Terminal User Interface
Modern TUI using Textual framework - API-first architecture maintained
"""

from pathlib import Path
from typing import Optional

from rich.syntax import Syntax
from rich.table import Table
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
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
        """Display rename results."""
        mode = "PREVIEW" if is_preview else "COMPLETED"
        table = Table(
            title=f"Rename Results - {mode}",
            show_header=True,
            header_style="bold magenta",
        )

        table.add_column("Status", style="dim", width=8)
        table.add_column("Original", style="cyan")
        table.add_column("→", justify="center", width=3)
        table.add_column("New Name", style="green")

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

            table.add_row(
                f"[{status_style}]{status_icon}[/{status_style}]",
                result.src.name,
                "→" if result.dst else "",
                result.dst.name if result.dst else f"[dim]{result.message}[/dim]",
            )

        if len(status.results) > display_limit:
            table.add_row(
                "", f"[dim]... and {len(status.results) - display_limit} more files (scroll to see all)[/dim]", "", ""
            )

        self.update(table)


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
        await self._process_files(dry_run=True)

    @on(Button.Pressed, "#rename-btn")
    async def action_rename(self) -> None:
        """Execute rename operation."""
        if not self.last_status:
            self.notify("Run Preview first to see what will change", severity="warning")
            return

        # Confirm
        self.notify("Renaming files...", severity="information")
        await self._process_files(dry_run=False)

    @on(Button.Pressed, "#reset-btn")
    def action_reset(self) -> None:
        """Reset the form."""
        self.query_one("#path-input", Input).value = ""
        self.query_one("#template-input", Input).value = DEFAULT_TEMPLATE
        self.query_one("#recursive-check", Checkbox).value = True

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

        # Show progress
        mode = "Previewing" if dry_run else "Renaming"
        self.notify(f"{mode} files in {path.name}...", timeout=2)

        # Call the API (maintains API-first architecture)
        try:
            request = RenameRequest(
                path=path,
                recursive=recursive,
                dry_run=dry_run,
                template=template or DEFAULT_TEMPLATE,
            )

            status = self.api.rename_files(request)
            self.last_status = status

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
                    f"Preview: {status.renamed} files will be renamed",
                    severity="information",
                )
            else:
                self.notify(
                    f"✓ Successfully renamed {status.renamed} files!",
                    severity="success",
                )

        except Exception as e:
            self.notify(f"Error: {e}", severity="error")
            self.log.error(f"Processing error: {e}", exc_info=True)


def run_tui():
    """Launch the Terminal UI."""
    app = DJRenameTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
