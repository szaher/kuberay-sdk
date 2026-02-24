# Compound Operations

*Added in v0.2.0*

Create a cluster, wait for it, and submit a job in a single call.

**What this example covers:**

1. Use `create_cluster_and_submit_job()` for the most common workflow
2. Handle partial failures where the cluster is created but job submission fails
3. Access the cluster handle from the exception for cleanup

!!! note
    This example requires a running KubeRay cluster. The method signature and error handling pattern can be reviewed without a cluster.

[:material-download: Download compound_operations.py](https://github.com/szaher/kuberay-sdk/blob/main/examples/compound_operations.py){ .md-button }

## Source Code

```python title="examples/compound_operations.py"
--8<-- "examples/compound_operations.py"
```
