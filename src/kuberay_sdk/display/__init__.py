"""Rich display and notebook integration for KubeRay SDK.

Provides automatic rich output for terminal and notebook environments:
- Terminal (with ``rich`` extra): styled tables, progress bars, colored logs
- Notebook (with ``ipywidgets`` extra): HTML tables, widget progress bars, action buttons
- Plain fallback: basic text output when no extras are installed

Installation:
    Terminal rich output::

        pip install kuberay-sdk[rich]

    Notebook widgets::

        pip install kuberay-sdk[notebook]

    Both::

        pip install kuberay-sdk[display]

Example:
    >>> from kuberay_sdk import display
    >>> from kuberay_sdk import KubeRayClient
    >>> client = KubeRayClient()
    >>> clusters = client.list_clusters()
    >>> display(clusters)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kuberay_sdk.display._backend import DisplayBackend

__all__ = ["display", "get_backend"]

_cached_backend: DisplayBackend | None = None


def get_backend(*, override: str | None = None) -> DisplayBackend:
    """Get the appropriate display backend for the current environment.

    Selects a backend based on environment auto-detection, with optional
    override via the ``KUBERAY_DISPLAY`` environment variable or the
    ``override`` parameter.

    Resolution order:
        1. ``override`` parameter (if provided)
        2. ``KUBERAY_DISPLAY`` env var (if set and not ``"auto"``)
        3. Auto-detection: notebook → terminal (rich) → plain

    Args:
        override: Force a specific backend. One of ``"rich"``,
            ``"notebook"``, ``"plain"``, or ``None`` for auto-detection.

    Returns:
        A :class:`DisplayBackend` implementation appropriate for the
        current environment.

    Example:
        >>> backend = get_backend()
        >>> backend.render_table(["NAME"], [["my-cluster"]])

        >>> # Force plain output
        >>> backend = get_backend(override="plain")
    """
    global _cached_backend

    if override is None and _cached_backend is not None:
        return _cached_backend

    from kuberay_sdk.display._backend import PlainBackend
    from kuberay_sdk.display._detect import detect_environment

    env = override if override else detect_environment()

    backend: DisplayBackend

    if env == "notebook":
        try:
            from kuberay_sdk.display._notebook_backend import NotebookBackend

            backend = NotebookBackend()
        except ImportError:
            backend = PlainBackend()
    elif env in ("terminal", "rich"):
        try:
            from kuberay_sdk.display._rich_backend import RichBackend

            backend = RichBackend()
        except ImportError:
            backend = PlainBackend()
    else:
        backend = PlainBackend()

    if override is None:
        _cached_backend = backend

    return backend


def display(
    data: list[Any] | Any,
    *,
    title: str | None = None,
    format: str = "auto",
) -> None:
    """Render resource data using the appropriate display backend.

    Detects the current environment (terminal, notebook, plain) and
    renders the data accordingly:

    - Terminal with ``rich``: styled table with color-coded states
    - Notebook: HTML table with styled headers and alternating rows
    - Plain: basic aligned text table

    Args:
        data: A single resource object (e.g., ``ClusterHandle``) or a
            list of resource objects (e.g., ``list[ClusterStatus]``).
        title: Optional title displayed above the table.
        format: Output format. ``"auto"`` selects based on environment,
            ``"table"`` forces tabular output, ``"json"`` forces JSON.

    Example:
        >>> from kuberay_sdk import KubeRayClient, display
        >>> client = KubeRayClient()
        >>> clusters = client.list_clusters()
        >>> display(clusters)
        >>> display(clusters, title="My Clusters")
        >>> display(clusters, format="json")
    """
    if format == "json":
        from kuberay_sdk.cli.formatters import format_json

        print(format_json(data if isinstance(data, list) else [data]))
        return

    if isinstance(data, list) and len(data) == 0:
        print("No resources found.")
        return

    backend = get_backend()

    if not isinstance(data, list):
        # Single resource — try to render as HTML card or repr
        card = backend.render_html_card(
            _extract_card_data(data),
        )
        if card is not None:
            try:
                from IPython.display import HTML
                from IPython.display import display as ipy_display

                ipy_display(HTML(card))
            except ImportError:
                print(repr(data))
        else:
            print(repr(data))
        return

    # List of resources — render as table
    headers, rows, state_col = _extract_table_data(data)
    backend.render_table(headers, rows, title=title, state_column=state_col)


def _extract_card_data(obj: Any) -> dict[str, str]:
    """Extract key-value pairs from a resource object for card display."""
    data: dict[str, str] = {}
    type_name = type(obj).__name__

    if hasattr(obj, "name"):
        data["Name"] = str(obj.name)
    if hasattr(obj, "_name"):
        data["Name"] = str(obj._name)
    if hasattr(obj, "namespace"):
        data["Namespace"] = str(obj.namespace)
    if hasattr(obj, "_namespace"):
        data["Namespace"] = str(obj._namespace)
    if hasattr(obj, "state"):
        data["State"] = str(obj.state)

    data["Type"] = type_name
    return data


def _extract_table_data(
    items: list[Any],
) -> tuple[list[str], list[list[str]], int | None]:
    """Extract table headers, rows, and state column index from a list of resource objects."""
    if not items:
        return [], [], None

    first = items[0]

    # Handle dicts
    if isinstance(first, dict):
        headers = list(first.keys())
        rows = [[str(item.get(h, "")) for h in headers] for item in items]
        state_col = None
        for i, h in enumerate(headers):
            if h.lower() in ("state", "status"):
                state_col = i
                break
        return [h.upper() for h in headers], rows, state_col

    # Handle pydantic models or objects with known fields
    headers: list[str] = []
    state_col = None

    type_name = type(first).__name__

    if "Cluster" in type_name:
        headers = ["NAME", "NAMESPACE", "STATE", "WORKERS"]
        state_col = 2
    elif "Job" in type_name:
        headers = ["NAME", "NAMESPACE", "MODE", "STATE"]
        state_col = 3
    elif "Service" in type_name:
        headers = ["NAME", "NAMESPACE", "STATE"]
        state_col = 2
    else:
        # Generic fallback — try to extract from model fields or __dict__
        if hasattr(first, "model_fields"):
            headers = [f.upper() for f in first.model_fields]
        elif hasattr(first, "__dict__"):
            headers = [k.upper() for k in first.__dict__ if not k.startswith("_")]
        state_col = None
        for i, h in enumerate(headers):
            if h in ("STATE", "STATUS"):
                state_col = i
                break

    rows = []
    for item in items:
        row: list[str] = []
        for h in headers:
            attr = h.lower()
            val = getattr(item, attr, getattr(item, f"_{attr}", ""))
            row.append(str(val) if val is not None else "")
        rows.append(row)

    return headers, rows, state_col
