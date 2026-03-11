"""NotebookBackend — display backend for Jupyter notebook environments.

Provides HTML tables, ipywidgets progress bars, and styled HTML cards
for notebook display. Requires ``pip install kuberay-sdk[notebook]``.
"""

from __future__ import annotations

from typing import Any

from kuberay_sdk.display._backend import ActionDef
from kuberay_sdk.display._colors import get_state_color
from kuberay_sdk.models.progress import ProgressStatus

try:
    import ipywidgets  # noqa: F401

    HAS_IPYWIDGETS = True
except ImportError:
    HAS_IPYWIDGETS = False

# Color map from abstract names to CSS color values
_CSS_COLORS: dict[str, str] = {
    "green": "#28a745",
    "yellow": "#ffc107",
    "red": "#dc3545",
}


def _ipython_display(obj: Any) -> None:
    """Display an object using IPython's display system."""
    from IPython.display import display

    display(obj)


class NotebookProgressContext:
    """Progress context using ipywidgets for notebook environments."""

    def __init__(
        self,
        bar: Any,
        label: Any,
        box: Any,
        timeout: float,
    ) -> None:
        self._bar = bar
        self._label = label
        self._box = box
        self._timeout = timeout

    def update(self, status: ProgressStatus) -> None:
        """Update the progress widget with current state."""
        self._label.value = f"{status.state} — {status.elapsed_seconds:.0f}s"
        # Update bar as fraction of timeout
        if self._timeout > 0:
            self._bar.value = min(status.elapsed_seconds / self._timeout * 100, 100)

    def complete(self, message: str = "Done") -> None:
        """Mark progress as complete with green style."""
        self._bar.value = 100
        self._bar.bar_style = "success"
        self._label.value = f"✓ {message}"

    def fail(self, message: str) -> None:
        """Mark progress as failed with red style."""
        self._bar.bar_style = "danger"
        self._label.value = f"✗ {message}"

    def __enter__(self) -> NotebookProgressContext:
        _ipython_display(self._box)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        return False


class _PlainNotebookProgressContext:
    """Fallback progress context when ipywidgets is not available."""

    def update(self, status: ProgressStatus) -> None:
        pass

    def complete(self, message: str = "Done") -> None:
        pass

    def fail(self, message: str) -> None:
        pass

    def __enter__(self) -> _PlainNotebookProgressContext:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> bool:
        return False


class NotebookBackend:
    """Display backend for Jupyter notebook environments."""

    def render_table(
        self,
        headers: list[str],
        rows: list[list[str]],
        *,
        title: str | None = None,
        state_column: int | None = None,
    ) -> None:
        """Render an HTML table with styled headers and alternating rows."""
        from IPython.display import HTML

        html_parts: list[str] = []
        html_parts.append('<table style="border-collapse:collapse; width:auto; font-family:sans-serif;">')

        if title:
            html_parts.append(
                f'<caption style="font-weight:bold; font-size:14px; '
                f'text-align:left; padding:8px 0;">{_escape(title)}</caption>'
            )

        # Header row
        html_parts.append("<tr>")
        for h in headers:
            html_parts.append(
                f'<th style="padding:8px 12px; text-align:left; '
                f'background:#2d3748; color:white; font-weight:bold;">{_escape(h)}</th>'
            )
        html_parts.append("</tr>")

        # Data rows with alternating colors
        for row_idx, row in enumerate(rows):
            bg = "#f7fafc" if row_idx % 2 == 0 else "#edf2f7"
            html_parts.append(f'<tr style="background:{bg};">')
            for col_idx, cell in enumerate(row):
                if col_idx == state_column:
                    color = _CSS_COLORS.get(get_state_color(cell), "inherit")
                    html_parts.append(
                        f'<td style="padding:8px 12px; color:{color}; font-weight:bold;">{_escape(cell)}</td>'
                    )
                else:
                    html_parts.append(f'<td style="padding:8px 12px;">{_escape(cell)}</td>')
            html_parts.append("</tr>")

        html_parts.append("</table>")
        _ipython_display(HTML("".join(html_parts)))

    def render_progress(self, timeout: float) -> NotebookProgressContext | _PlainNotebookProgressContext:
        """Create a notebook progress bar widget."""
        try:
            import ipywidgets as widgets
        except ImportError:
            return _PlainNotebookProgressContext()

        bar = widgets.FloatProgress(
            value=0,
            min=0,
            max=100,
            description="",
            bar_style="info",
            style={"bar_color": "#4299e1"},
        )
        label = widgets.Label(value="Waiting...")
        box = widgets.VBox([label, bar])
        return NotebookProgressContext(bar, label, box, timeout)

    def render_log_line(
        self,
        line: str,
        *,
        source: str | None = None,
    ) -> None:
        """Render a color-coded log line as HTML."""
        from IPython.display import HTML

        from kuberay_sdk.display._log_renderer import parse_log_level

        level = parse_log_level(line)
        color = _LOG_LEVEL_CSS.get(level, "inherit")

        prefix = f'<span style="color:#4299e1; font-weight:bold;">[{_escape(source)}]</span> ' if source else ""
        _ipython_display(HTML(f'<pre style="margin:2px 0; color:{color};">{prefix}{_escape(line)}</pre>'))

    def render_html_card(
        self,
        data: dict[str, str],
        *,
        actions: list[ActionDef] | None = None,
    ) -> str | None:
        """Render an HTML summary card for notebook display."""
        parts: list[str] = []
        parts.append(
            '<div style="border:1px solid #ddd; border-radius:8px; '
            'padding:16px; margin:8px 0; font-family:sans-serif; max-width:500px;">'
        )

        # Title
        type_name = data.get("Type", "Resource")
        name = data.get("Name", "unknown")
        parts.append(
            f'<div style="font-size:14px; font-weight:bold; margin-bottom:8px;">'
            f"{_escape(type_name)}: {_escape(name)}</div>"
        )

        # Key-value table
        parts.append('<table style="border-collapse:collapse; width:100%;">')
        for key, value in data.items():
            if key == "Type":
                continue
            if key == "State":
                color = _CSS_COLORS.get(get_state_color(value), "inherit")
                val_html = f'<span style="color:{color}; font-weight:bold;">{_escape(value)}</span>'
            else:
                val_html = _escape(value)
            parts.append(
                f'<tr><td style="padding:4px 8px; color:#666;">{_escape(key)}</td>'
                f'<td style="padding:4px 8px;">{val_html}</td></tr>'
            )
        parts.append("</table>")

        parts.append("</div>")
        return "".join(parts)


def _escape(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


_LOG_LEVEL_CSS: dict[str, str] = {
    "ERROR": "#dc3545",
    "CRITICAL": "#dc3545",
    "WARNING": "#ffc107",
    "INFO": "inherit",
    "DEBUG": "#6c757d",
}
