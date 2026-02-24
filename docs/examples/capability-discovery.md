# Capability Discovery

*Added in v0.2.0*

Discover what features are available on the connected cluster before attempting operations.

**What this example covers:**

1. Use `client.get_capabilities()` to detect cluster features
2. Conditional GPU vs CPU cluster configuration
3. Check for Kueue queue support
4. Detect OpenShift platform

!!! note
    This example requires a running KubeRay cluster for capability detection. The conditional logic patterns can be reviewed without a cluster.

[:material-download: Download capability_discovery.py](https://github.com/szaher/kuberay-sdk/blob/main/examples/capability_discovery.py){ .md-button }

## Source Code

```python title="examples/capability_discovery.py"
--8<-- "examples/capability_discovery.py"
```
