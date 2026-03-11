"""DisplayBackend Protocol, ProgressContext Protocol, ActionDef, and PlainBackend.

Defines the core abstractions for display rendering and provides
the plain-text fallback implementation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from kuberay_sdk.models.progress import ProgressStatus


@dataclass(frozen=True)
class ActionDef:
    """Definition for a notebook action button.

    Attributes:
        label: Button display text (e.g., "Delete", "Scale Workers").
        callback: Function to execute when clicked.
        destructive: If True, requires confirmation before executing.
        icon: Optional icon identifier (e.g., "trash", "resize").
    """

    label: str
    callback: Callable[[], None]
    destructive: bool = False
    icon: str | None = None


@runtime_checkable
class ProgressContext(Protocol):
    """Context manager for progress display during wait operations."""

    def update(self, status: ProgressStatus) -> None:
        """Update progress display with new status."""
        ...

    def complete(self, message: str = "Done") -> None:
        """Mark operation as successfully completed."""
        ...

    def fail(self, message: str) -> None:
        """Mark operation as failed."""
        ...

    def __enter__(self) -> ProgressContext: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool: ...


@runtime_checkable
class DisplayBackend(Protocol):
    """Protocol for display rendering backends."""

    def render_table(
        self,
        headers: list[str],
        rows: list[list[str]],
        *,
        title: str | None = None,
        state_column: int | None = None,
    ) -> None:
        """Render tabular data to output.

        Args:
            headers: Column header names.
            rows: Row data as list of string lists.
            title: Optional table title.
            state_column: Column index containing resource state
                values for color coding. None disables color coding.
        """
        ...

    def render_progress(self, timeout: float) -> ProgressContext:
        """Create a progress context for a wait operation.

        Args:
            timeout: Maximum duration in seconds.

        Returns:
            A context manager that displays and updates progress.
        """
        ...

    def render_log_line(
        self,
        line: str,
        *,
        source: str | None = None,
    ) -> None:
        """Render a single log line with optional styling.

        Args:
            line: The log line text.
            source: Optional source label (e.g., "head", "worker-0").
        """
        ...

    def render_html_card(
        self,
        data: dict[str, str],
        *,
        actions: list[ActionDef] | None = None,
    ) -> str | None:
        """Render an HTML card for notebook display.

        Args:
            data: Key-value pairs to display.
            actions: Optional action buttons.

        Returns:
            HTML string, or None if not applicable.
        """
        ...


class PlainProgressContext:
    """No-op progress context for plain-text environments."""

    def update(self, status: ProgressStatus) -> None:
        """No-op — plain backend does not display progress."""

    def complete(self, message: str = "Done") -> None:
        """No-op — plain backend does not display progress."""

    def fail(self, message: str) -> None:
        """No-op — plain backend does not display progress."""

    def __enter__(self) -> PlainProgressContext:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        return False


class PlainBackend:
    """Fallback display backend using plain text output.

    Delegates table rendering to :func:`kuberay_sdk.cli.formatters.format_table`.
    Progress and HTML card rendering are no-ops.
    """

    def render_table(
        self,
        headers: list[str],
        rows: list[list[str]],
        *,
        title: str | None = None,
        state_column: int | None = None,
    ) -> None:
        """Render a plain-text table to stdout."""
        from kuberay_sdk.cli.formatters import format_table

        if title:
            print(title)
        print(format_table(headers, rows))

    def render_progress(self, timeout: float) -> PlainProgressContext:
        """Return a no-op progress context."""
        return PlainProgressContext()

    def render_log_line(
        self,
        line: str,
        *,
        source: str | None = None,
    ) -> None:
        """Print a plain log line with optional source prefix."""
        if source:
            print(f"[{source}] {line}")
        else:
            print(line)

    def render_html_card(
        self,
        data: dict[str, str],
        *,
        actions: list[ActionDef] | None = None,
    ) -> str | None:
        """Return None — plain backend does not render HTML cards."""
        return None
