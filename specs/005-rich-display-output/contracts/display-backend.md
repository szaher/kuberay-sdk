# Contract: DisplayBackend Protocol

**Module**: `kuberay_sdk.display._backend`
**Type**: Public Protocol (structural typing)

## Protocol Definition

```python
from typing import Protocol, runtime_checkable
from kuberay_sdk.models.progress import ProgressStatus


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

    def __enter__(self) -> "ProgressContext":
        ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        ...


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
        actions: list["ActionDef"] | None = None,
    ) -> str | None:
        """Render an HTML card for notebook display.

        Args:
            data: Key-value pairs to display.
            actions: Optional action buttons.

        Returns:
            HTML string, or None if not applicable.
        """
        ...
```

## Implementations

| Backend | Module | Requires | Environment |
|---------|--------|----------|-------------|
| `PlainBackend` | `kuberay_sdk.display._backend` | (none) | Fallback / non-TTY |
| `RichBackend` | `kuberay_sdk.display._rich_backend` | `rich>=13.0` | Interactive terminal |
| `NotebookBackend` | `kuberay_sdk.display._notebook_backend` | `ipywidgets>=8.0` | Jupyter / JupyterLab |

## Selection Logic

```python
def get_backend(override: str | None = None) -> DisplayBackend:
    """Get the appropriate display backend.

    Resolution order:
    1. KUBERAY_DISPLAY env var (if set)
    2. override parameter (if provided)
    3. Auto-detection:
       a. Notebook kernel detected → NotebookBackend
       b. stdout is TTY + rich available → RichBackend
       c. Fallback → PlainBackend
    """
```

## Behavior Contract

- `PlainBackend.render_table()` delegates to existing `cli.formatters.format_table()`.
- `PlainBackend.render_progress()` returns a no-op context manager (silent).
- `PlainBackend.render_html_card()` returns `None`.
- `RichBackend.render_table()` outputs ANSI-styled table via `rich.table.Table`.
- `RichBackend.render_progress()` returns a `rich.progress.Progress` wrapper.
- `NotebookBackend.render_table()` calls `IPython.display.display(HTML(...))`.
- `NotebookBackend.render_progress()` returns an ipywidgets progress wrapper.
- All backends: `ProgressContext.__exit__` with `KeyboardInterrupt` cleans up display, cancels operation, returns `False` (re-raises).
