"""RichBackend — terminal display backend using the ``rich`` library.

Provides styled tables, progress bars, and colored log output for
interactive terminal environments. Requires ``pip install kuberay-sdk[rich]``.
"""

from __future__ import annotations

import sys
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from kuberay_sdk.display._backend import ActionDef
from kuberay_sdk.display._colors import get_state_color
from kuberay_sdk.models.progress import ProgressStatus


class RichProgressContext:
    """Progress context wrapping ``rich.progress.Progress`` for terminal display."""

    def __init__(
        self,
        progress: Progress,
        task_id: Any,
        timeout: float,
    ) -> None:
        self._progress = progress
        self._task_id = task_id
        self._timeout = timeout

    def update(self, status: ProgressStatus) -> None:
        """Update the progress display with current state and elapsed time."""
        color = get_state_color(status.state)
        desc = f"[{color}]{status.state}[/{color}]"
        if status.message:
            desc += f" — {status.message}"
        self._progress.update(self._task_id, description=desc)

    def complete(self, message: str = "Done") -> None:
        """Mark progress as successfully completed."""
        self._progress.update(
            self._task_id,
            description=f"[green]✓ {message}[/green]",
            completed=self._timeout,
        )

    def fail(self, message: str) -> None:
        """Mark progress as failed with error message."""
        self._progress.update(
            self._task_id,
            description=f"[red]✗ {message}[/red]",
        )

    def __enter__(self) -> RichProgressContext:
        self._progress.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        self._progress.stop()
        # Never swallow exceptions; KeyboardInterrupt re-raises naturally
        return False


class RichBackend:
    """Display backend using the ``rich`` library for terminal environments."""

    def __init__(self) -> None:
        self._console = Console(force_terminal=sys.stdout.isatty())

    def render_table(
        self,
        headers: list[str],
        rows: list[list[str]],
        *,
        title: str | None = None,
        state_column: int | None = None,
    ) -> None:
        """Render a styled table with optional color-coded state column."""
        table = Table(title=title, show_header=True, header_style="bold")

        for header in headers:
            table.add_column(header)

        for row in rows:
            styled_row: list[str] = []
            for i, cell in enumerate(row):
                if i == state_column:
                    color = get_state_color(cell)
                    styled_row.append(f"[{color}]{cell}[/{color}]")
                else:
                    styled_row.append(cell)
            table.add_row(*styled_row)

        self._console.print(table)

    def render_progress(self, timeout: float) -> RichProgressContext:
        """Create a rich progress bar for a wait operation."""
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=self._console,
            transient=False,
        )
        task_id = progress.add_task("Waiting...", total=timeout)
        return RichProgressContext(progress, task_id, timeout)

    def render_log_line(
        self,
        line: str,
        *,
        source: str | None = None,
    ) -> None:
        """Render a color-coded log line based on detected log level."""
        from kuberay_sdk.display._log_renderer import parse_log_level

        level = parse_log_level(line)
        color = _LOG_LEVEL_COLORS.get(level, "")

        prefix = f"[cyan]\\[{source}][/cyan] " if source else ""

        if color:
            self._console.print(f"{prefix}[{color}]{line}[/{color}]")
        else:
            self._console.print(f"{prefix}{line}")

    def render_html_card(
        self,
        data: dict[str, str],
        *,
        actions: list[ActionDef] | None = None,
    ) -> str | None:
        """Return None — rich backend does not render HTML cards."""
        return None


# Mapping of log levels to rich color styles
_LOG_LEVEL_COLORS: dict[str, str] = {
    "ERROR": "red",
    "CRITICAL": "red bold",
    "WARNING": "yellow",
    "INFO": "",
    "DEBUG": "dim",
}
