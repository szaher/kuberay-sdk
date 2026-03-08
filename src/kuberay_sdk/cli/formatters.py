"""Output formatters for the KubeRay CLI (T040).

Provides table and JSON formatting for CLI output.
"""

from __future__ import annotations

import json
from typing import Any


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Format data as a simple aligned table with column padding.

    Args:
        headers: Column header names.
        rows: List of rows, each a list of string values.

    Returns:
        A formatted table string with aligned columns.

    Example:
        >>> print(format_table(["NAME", "STATE"], [["my-cluster", "RUNNING"]]))
        NAME         STATE
        my-cluster   RUNNING
    """
    if not headers:
        return ""

    # Calculate column widths (minimum is header length)
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(cell))

    # Build header line
    header_line = "   ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))

    # Build row lines
    row_lines = []
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            if i < len(col_widths):
                cells.append(cell.ljust(col_widths[i]))
            else:
                cells.append(cell)
        row_lines.append("   ".join(cells))

    lines = [header_line, *row_lines]
    return "\n".join(lines)


def format_rich_table(
    headers: list[str],
    rows: list[list[str]],
    *,
    title: str | None = None,
    state_column: int | None = None,
) -> None:
    """Render a table using the rich display backend if available.

    Falls back to plain text format_table() when rich is not installed.

    Args:
        headers: Column header names.
        rows: Row data as list of string lists.
        title: Optional table title.
        state_column: Column index with state values for color coding.
    """
    try:
        from kuberay_sdk.display import get_backend

        backend = get_backend()
        backend.render_table(headers, rows, title=title, state_column=state_column)
    except Exception:
        if title:
            print(title)
        print(format_table(headers, rows))


def format_json(data: Any) -> str:
    """Format data as indented JSON.

    Args:
        data: Any JSON-serializable data.

    Returns:
        JSON string with indent=2.

    Example:
        >>> print(format_json({"name": "test"}))
        {
          "name": "test"
        }
    """
    return json.dumps(data, indent=2, default=str)
