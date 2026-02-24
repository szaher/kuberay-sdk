# Dry-Run Preview

*Added in v0.2.0*

Preview the CRD manifest that would be created, without making any Kubernetes API call.

**What this example covers:**

1. Create a cluster in dry-run mode and inspect the `DryRunResult`
2. Use `to_dict()` and `to_yaml()` to examine the generated manifest
3. Preview a GPU cluster with autoscaling
4. Preview a standalone RayJob in dry-run mode

[:material-download: Download dry_run_preview.py](https://github.com/szaher/kuberay-sdk/blob/main/examples/dry_run_preview.py){ .md-button }

## Source Code

```python title="examples/dry_run_preview.py"
--8<-- "examples/dry_run_preview.py"
```
