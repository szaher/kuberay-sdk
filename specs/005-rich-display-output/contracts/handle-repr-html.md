# Contract: Handle `_repr_html_()` for Notebook Display

**Module**: `kuberay_sdk.client` (ClusterHandle, JobHandle, ServiceHandle)
**Depends on**: `kuberay_sdk.display`

## Method Signatures

Added to `ClusterHandle`, `JobHandle`, and `ServiceHandle`:

```python
class ClusterHandle:
    def _repr_html_(self) -> str | None:
        """Render HTML summary card for Jupyter notebook display.

        Returns styled HTML with resource details and action buttons
        when the [notebook] extra is installed. Returns None otherwise
        (Jupyter falls back to __repr__).

        The HTML card includes:
        - Resource name and namespace
        - Current state (color-coded)
        - Action buttons: "Delete", "Scale Workers", "Open Dashboard"
        """

class JobHandle:
    def _repr_html_(self) -> str | None:
        """Render HTML summary card for Jupyter notebook display.

        The HTML card includes:
        - Job name, namespace, and submission mode
        - Current state (color-coded)
        - Action buttons: "Stop", "View Logs", "Download Artifacts"
        """

class ServiceHandle:
    def _repr_html_(self) -> str | None:
        """Render HTML summary card for Jupyter notebook display.

        The HTML card includes:
        - Service name and namespace
        - Current state (color-coded)
        - Action buttons: "Delete", "Update Replicas"
        """
```

## HTML Card Structure

```html
<div style="border:1px solid #ddd; border-radius:8px; padding:16px; margin:8px 0; font-family:sans-serif; max-width:500px;">
  <div style="font-size:14px; font-weight:bold; margin-bottom:8px;">
    ClusterHandle: my-cluster
  </div>
  <table style="border-collapse:collapse; width:100%;">
    <tr><td style="padding:4px 8px; color:#666;">Namespace</td><td style="padding:4px 8px;">default</td></tr>
    <tr><td style="padding:4px 8px; color:#666;">State</td><td style="padding:4px 8px;"><span style="color:green; font-weight:bold;">RUNNING</span></td></tr>
  </table>
  <div style="margin-top:12px; display:flex; gap:8px;">
    <!-- Action buttons rendered via ipywidgets when available -->
  </div>
</div>
```

## Behavior Contract

- When `[notebook]` extra is NOT installed: `_repr_html_()` returns `None`. Jupyter falls back to `__repr__()`.
- When `[notebook]` extra IS installed but environment is NOT a notebook: `_repr_html_()` is not called by the runtime (only Jupyter calls it).
- Action buttons use `ipywidgets.Button` in Jupyter/JupyterLab environments.
- In Colab/VS Code notebooks (HTML-only): the card renders without interactive buttons.
- Destructive action buttons ("Delete") show a confirmation widget before executing.
- `_repr_html_()` does NOT make API calls to fetch current state — it uses the cached state from the last operation (consistent with existing `__repr__` behavior per FR-013 from feature 004).

## Wait Method Progress Integration

Updated signatures on handles:

```python
class ClusterHandle:
    def wait_until_ready(
        self,
        timeout: float = 300,
        progress_callback: Any = None,
        progress: bool = True,          # NEW parameter
    ) -> None:
        """Block until cluster reaches RUNNING state.

        When progress=True and no progress_callback is provided,
        auto-displays a progress bar using the detected display backend.
        """

class JobHandle:
    def wait(
        self,
        timeout: float = 3600,
        progress_callback: Any = None,
        progress: bool = True,          # NEW parameter
    ) -> Any:
        """Block until job completes.

        When progress=True and no progress_callback is provided,
        auto-displays a progress bar using the detected display backend.
        """
```

## Parameter Precedence

1. `progress_callback` provided → use it (ignore `progress` flag)
2. `progress=True` (default) + no callback → auto-create rich/notebook/plain progress callback via detected backend
3. `progress=False` → no progress display at all
