# Contract: Capability Discovery (US11)

## Public API

### ClusterCapabilities model

```python
from pydantic import BaseModel

class ClusterCapabilities(BaseModel):
    """Cluster capability discovery result."""
    kuberay_installed: bool = False
    kuberay_version: str | None = None
    gpu_available: bool | None = None    # None = unknown (no permission)
    gpu_types: list[str] = []
    kueue_available: bool | None = None  # None = unknown (no permission)
    openshift: bool | None = None        # None = unknown (no permission)
```

### Client method

```python
class KubeRayClient:
    def get_capabilities(self) -> ClusterCapabilities:
        """Discover cluster capabilities.

        Returns a ClusterCapabilities object.
        Permission errors result in None for the affected field (not raised).
        """
```

### Async variant

```python
class AsyncKubeRayClient:
    async def get_capabilities(self) -> ClusterCapabilities:
        """Async version of capability discovery."""
```

## Detection Logic

1. **KubeRay**: Check for `rayclusters.ray.io` CRD. Extract version from CRD annotations/labels if available.
2. **GPU**: List nodes, check for `nvidia.com/gpu` in allocatable resources. On RBAC error → `gpu_available = None`.
3. **Kueue**: Check for `workloads.kueue.x-k8s.io` CRD. On RBAC error → `kueue_available = None`.
4. **OpenShift**: Reuse existing `platform.detection.is_openshift()`. On error → `openshift = None`.

## Error Handling

- No exceptions are raised from `get_capabilities()`.
- RBAC permission errors result in `None` for the affected capability.
- Network errors that prevent all discovery raise `KubeRayError`.

## Test Contract

```python
def test_capabilities_all_available(mock_k8s):
    """Full capability cluster."""
    caps = client.get_capabilities()
    assert caps.kuberay_installed is True
    assert caps.gpu_available is True
    assert "nvidia.com/gpu" in caps.gpu_types

def test_capabilities_minimal(mock_k8s):
    """Vanilla K8s with only KubeRay."""
    caps = client.get_capabilities()
    assert caps.kuberay_installed is True
    assert caps.kueue_available is False
    assert caps.openshift is False

def test_capabilities_permission_error(mock_k8s):
    """RBAC prevents GPU detection."""
    caps = client.get_capabilities()
    assert caps.gpu_available is None  # unknown
```
