# Contract: display() Helper Function

**Module**: `kuberay_sdk.display`
**Import**: `from kuberay_sdk import display` or `from kuberay_sdk.display import display`

## Function Signature

```python
def display(
    data: list | object,
    *,
    title: str | None = None,
    format: str = "auto",  # "auto" | "table" | "json"
) -> None:
    """Render resource data using the appropriate display backend.

    Detects the current environment (terminal, notebook, plain) and
    renders the data accordingly:
    - Terminal with rich: styled table with color-coded states
    - Notebook: HTML table with styled headers and alternating rows
    - Plain: basic aligned text table

    Args:
        data: A single resource object (ClusterStatus, JobHandle, etc.)
              or a list of resource objects.
        title: Optional title displayed above the table.
        format: Output format. "auto" selects based on data type,
                "table" forces tabular output, "json" forces JSON.

    Examples:
        >>> from kuberay_sdk import KubeRayClient, display
        >>> client = KubeRayClient()
        >>> clusters = client.list_clusters()
        >>> display(clusters)
        >>> display(clusters, title="My Clusters")
        >>> display(clusters, format="json")
    """
```

## Supported Data Types

| Input Type | Table Columns | State Column |
|------------|---------------|--------------|
| `list[ClusterStatus]` | NAME, NAMESPACE, STATE, WORKERS, AGE | STATE (index 2) |
| `list[JobHandle]` | NAME, NAMESPACE, MODE, STATE | STATE (index 3) |
| `list[ServiceHandle]` | NAME, NAMESPACE, STATE | STATE (index 2) |
| `ClusterHandle` | Rendered as key-value card (not table) | STATE field |
| `JobHandle` | Rendered as key-value card | STATE field |
| `ServiceHandle` | Rendered as key-value card | STATE field |
| `list[dict]` | Keys as headers, values as rows | Auto-detect "state"/"status" key |

## Top-Level Re-export

Added to `kuberay_sdk/__init__.py`:

```python
# In _LAZY_IMPORTS
"display": ("kuberay_sdk.display", "display"),
```

## Behavior Notes

- `display()` writes directly to stdout (terminal) or uses `IPython.display.display()` (notebook).
- It does NOT return a value — it is a side-effect function.
- When `format="json"`, it delegates to the existing `cli.formatters.format_json()`.
- When data is empty, it prints a "No resources found" message.
- When data type is unrecognized, it falls back to `repr(data)`.
