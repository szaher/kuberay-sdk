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
