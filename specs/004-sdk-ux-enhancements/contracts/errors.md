# Contract: Actionable Error Messages (US1)

## Public API

### KubeRayError (modified base class)

```python
class KubeRayError(Exception):
    def __init__(
        self,
        message: str,
        remediation: str = "",
        details: dict[str, Any] | None = None,
    ) -> None: ...

    remediation: str  # Step-by-step recovery instructions
    details: dict[str, Any]
```

### Error Subclass Remediation Defaults

Each error subclass MUST pass a default `remediation` string to the base class:

```python
class ClusterNotFoundError(ClusterError):
    # remediation: "Check cluster name with: kubectl get rayclusters -n {namespace}\n..."

class DashboardUnreachableError(KubeRayError):
    # remediation: "Check cluster status: kubectl get raycluster {name} -n {namespace}\n
    #              Check pod status: kubectl get pods -n {namespace} -l ray.io/cluster={name}\n
    #              Check network: kubectl port-forward svc/{name}-head-svc 8265:8265 -n {namespace}"

class KubeRayOperatorNotFoundError(KubeRayError):
    # remediation: "Install KubeRay operator:\n
    #              helm repo add kuberay https://ray-project.github.io/kuberay-helm/\n
    #              helm install kuberay-operator kuberay/kuberay-operator"

class AuthenticationError(KubeRayError):
    # remediation: "Check kubeconfig: kubectl config current-context\n
    #              Re-authenticate: kubectl auth whoami\n
    #              Verify RBAC: kubectl auth can-i list rayclusters"

class TimeoutError(KubeRayError):
    # remediation: "Increase timeout or check resource events:\n
    #              kubectl describe raycluster {name} -n {namespace}\n
    #              kubectl get events -n {namespace} --field-selector involvedObject.name={name}"
```

## Backward Compatibility

- Existing `KubeRayError(message, details=...)` calls continue to work (remediation defaults to `""`).
- No breaking changes to exception handling patterns.

## Test Contract

```python
def test_all_errors_have_remediation():
    """Every error subclass must have a non-empty remediation string."""
    for error_cls in [ClusterNotFoundError, DashboardUnreachableError, ...]:
        err = error_cls(...)  # construct with typical args
        assert isinstance(err.remediation, str)
        assert len(err.remediation) > 0

def test_remediation_contains_kubectl():
    """Remediation hints should include kubectl commands."""
    err = DashboardUnreachableError("my-cluster")
    assert "kubectl" in err.remediation
```
