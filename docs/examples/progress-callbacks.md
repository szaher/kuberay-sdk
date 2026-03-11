# Progress Callbacks

*Added in v0.2.0*

Monitor long-running wait operations with a progress callback function.

**What this example covers:**

1. Define a progress callback that formats elapsed time and status
2. Pass the callback to `wait_until_ready()` for real-time feedback
3. Optional tqdm integration for progress bar display

!!! note
    This example requires a running KubeRay cluster for the wait operation. The callback definition and type signature can be reviewed without a cluster.

[:material-download: Download progress_callbacks.py](https://github.com/szaher/kuberay-sdk/blob/main/examples/progress_callbacks.py){ .md-button }

## Source Code

```python title="examples/progress_callbacks.py"
--8<-- "examples/progress_callbacks.py"
```

---

## Auto Progress Bars (v0.3.0+)

With `kuberay-sdk[rich]` or `kuberay-sdk[notebook]` installed, wait operations display progress bars automatically — no callback needed:

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()
cluster = client.create_cluster("my-cluster", workers=4)

# Progress bar appears automatically
cluster.wait_until_ready()

# Disable per-call
cluster.wait_until_ready(progress=False)

# Explicit callback still takes precedence
cluster.wait_until_ready(progress_callback=my_callback)
```

In notebooks, the progress bar renders as an ipywidgets widget inline in the cell.

See [Rich Display & Notebook Integration](../user-guide/rich-display.md) for setup and configuration.
