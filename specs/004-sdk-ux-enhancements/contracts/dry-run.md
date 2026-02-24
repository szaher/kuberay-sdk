# Contract: Dry-Run / Validation Mode (US6)

## Public API

### DryRunResult

```python
class DryRunResult:
    """Result of a dry-run create operation."""

    def __init__(self, manifest: dict[str, Any], kind: str) -> None: ...

    def to_dict(self) -> dict[str, Any]:
        """Return the raw CRD manifest dictionary."""

    def to_yaml(self) -> str:
        """Return the CRD manifest as a YAML string."""
```

### Modified create methods

```python
class KubeRayClient:
    def create_cluster(
        self,
        name: str,
        ...,
        dry_run: bool = False,
    ) -> ClusterHandle | DryRunResult:
        """When dry_run=True, returns DryRunResult instead of ClusterHandle."""

    def create_job(
        self,
        name: str,
        ...,
        dry_run: bool = False,
    ) -> JobHandle | DryRunResult: ...

    def create_service(
        self,
        name: str,
        ...,
        dry_run: bool = False,
    ) -> ServiceHandle | DryRunResult: ...
```

### Behavior

1. Validates input via pydantic model (raises `ValidationError` on invalid params).
2. Builds CRD manifest via `to_crd_dict()`.
3. Returns `DryRunResult` wrapping the manifest — NO Kubernetes API call.
4. If `dry_run=False` (default), behavior is unchanged.

## Backward Compatibility

- Return type is `ClusterHandle | DryRunResult` — callers not using `dry_run` see no change.
- `dry_run=False` is the default.

## Test Contract

```python
def test_dry_run_returns_manifest():
    result = client.create_cluster("test", workers=2, dry_run=True)
    assert isinstance(result, DryRunResult)
    d = result.to_dict()
    assert d["kind"] == "RayCluster"
    assert d["metadata"]["name"] == "test"

def test_dry_run_no_api_call(mock_k8s):
    client.create_cluster("test", dry_run=True)
    mock_k8s.create_namespaced_custom_object.assert_not_called()

def test_dry_run_validates_input():
    with pytest.raises(ValidationError):
        client.create_cluster("", workers=-1, dry_run=True)

def test_dry_run_to_yaml():
    result = client.create_cluster("test", dry_run=True)
    yaml_str = result.to_yaml()
    assert "apiVersion: ray.io/v1" in yaml_str
```
