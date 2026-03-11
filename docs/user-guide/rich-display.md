# Rich Display & Notebook Integration

*Added in v0.3.0*

kuberay-sdk can render styled tables, progress bars, and colored logs in terminals and Jupyter notebooks. Display capabilities are provided through optional extras that you install alongside the base SDK.

---

## Installation

=== "Terminal (Rich)"

    ```bash
    pip install kuberay-sdk[rich]
    ```

    Adds styled tables with box-drawing characters, animated progress bars during wait operations, and color-coded log output.

=== "Notebook (ipywidgets)"

    ```bash
    pip install kuberay-sdk[notebook]
    ```

    Adds HTML-styled tables, ipywidgets progress bars, action buttons on resource cards, and colored log output in Jupyter and Colab notebooks.

=== "Both"

    ```bash
    pip install kuberay-sdk[display]
    ```

    Installs both `rich` and `ipywidgets` for use in any environment.

!!! tip
    If no extras are installed, the SDK falls back to plain text output. Existing code does not break.

---

## Auto-Detection

The SDK automatically detects your environment and selects the best backend:

| Environment | Backend | Detected by |
|---|---|---|
| Jupyter / Colab / VS Code notebook | `NotebookBackend` | `ZMQInteractiveShell` or `VSCODE_PID` |
| Terminal with `rich` installed | `RichBackend` | TTY check + `rich` importable |
| Everything else | `PlainBackend` | Fallback |

You can override detection with the `KUBERAY_DISPLAY` environment variable:

```bash
# Force plain text output (no styling)
export KUBERAY_DISPLAY=plain

# Force rich terminal output
export KUBERAY_DISPLAY=rich

# Force notebook mode
export KUBERAY_DISPLAY=notebook

# Auto-detect (default)
export KUBERAY_DISPLAY=auto
```

Or programmatically:

```python
from kuberay_sdk.display import get_backend

backend = get_backend(override="plain")
```

---

## Terminal Usage

### Styled Tables

With `kuberay-sdk[rich]` installed, listing resources shows styled tables with color-coded states:

```python
from kuberay_sdk.display import display
from kuberay_sdk import KubeRayClient

client = KubeRayClient()
clusters = client.list_clusters()
display(clusters)
```

Output:

```
┌─────────────┬───────────┬─────────┬─────────┐
│ NAME        │ NAMESPACE │ STATE   │ WORKERS │
├─────────────┼───────────┼─────────┼─────────┤
│ my-cluster  │ default   │ RUNNING │ 4       │
│ old-cluster │ default   │ FAILED  │ 0       │
└─────────────┴───────────┴─────────┴─────────┘
```

States are color-coded: green for `RUNNING`, red for `FAILED`, yellow for `CREATING`.

### Progress Bars

Wait operations show animated progress bars automatically:

```python
cluster = client.create_cluster("my-cluster", workers=4)
cluster.wait_until_ready()  # Shows: ⠋ CREATING ━━━━━━━━━━ 12s
```

Disable the progress bar for a specific operation:

```python
cluster.wait_until_ready(progress=False)
```

### Colored Log Streaming

Log lines are color-coded by log level (ERROR in red, WARNING in yellow, INFO in default):

```python
for line in job.logs(stream=True, follow=True):
    pass  # Automatically styled
```

### CLI Integration

The `kuberay` CLI uses rich tables when the `[rich]` extra is installed:

```bash
kuberay cluster list
# Renders a styled table with color-coded states

kuberay cluster list --output json
# JSON output (always plain, never styled)
```

---

## Notebook Usage

### HTML Tables

In Jupyter or Colab, `display()` renders HTML tables with styled headers and alternating row colors:

```python
from kuberay_sdk.display import display
from kuberay_sdk import KubeRayClient

client = KubeRayClient()
clusters = client.list_clusters()
display(clusters)  # Renders interactive HTML table
```

### Resource Cards

Evaluating a handle in a notebook cell renders a styled HTML card:

```python
cluster = client.create_cluster("my-cluster", workers=4)
cluster  # Shows styled card with resource details
```

Handles expose `_repr_html_()` so Jupyter automatically renders them as HTML.

### Widget Progress Bars

Wait operations show ipywidgets progress bars inline in the notebook:

```python
cluster.wait_until_ready()  # ipywidgets progress bar renders inline
```

### Action Buttons

Notebook cards include action buttons for common operations like Delete, Scale, and open Dashboard.

---

## The `display()` Function

The `display()` function is the main entry point for rendering resource data:

```python
from kuberay_sdk.display import display

# Display a list of resources as a table
display(clusters)

# Display with a title
display(clusters, title="My Clusters")

# Force JSON output
display(clusters, format="json")
```

It accepts any list of SDK resource objects (cluster statuses, job statuses, service statuses) or dictionaries.

---

## Custom Progress Callbacks

You can still use explicit `progress_callback` functions alongside the display system:

```python
def on_progress(status):
    print(f"[{status.elapsed_seconds:.0f}s] {status.state}: {status.message}")

cluster.wait_until_ready(progress_callback=on_progress)
```

An explicit `progress_callback` takes precedence over the auto-generated progress bar from `progress=True`.

See [Progress Callbacks](../examples/progress-callbacks.md) for more examples.

---

## Configuration Reference

| Setting | Values | Default | Description |
|---|---|---|---|
| `KUBERAY_DISPLAY` env var | `auto`, `plain`, `rich`, `notebook` | `auto` | Force a specific display backend |
| `progress=True/False` | `bool` | `True` | Enable/disable progress bar per wait call |
| `progress_callback` | `Callable` or `None` | `None` | Custom callback overrides auto progress |

---

## Next Steps

- [Installation](getting-started/installation.md) -- install extras
- [Progress Callbacks](../examples/progress-callbacks.md) -- custom callback examples
- [API Reference](../reference/kuberay_sdk/display/index.md) -- full display module API
