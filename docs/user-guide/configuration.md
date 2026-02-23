# Configuration

kuberay-sdk is configured through the [`SDKConfig`][kuberay_sdk.config.SDKConfig] model, which controls client-wide defaults for namespace, retry behavior, and authentication.

## SDKConfig fields

| Field | Type | Default | Description |
|---|---|---|---|
| `namespace` | `str \| None` | `None` | Default namespace for all operations. Falls back to kubeconfig context. |
| `auth` | `AuthConfig \| None` | `None` | kube-authkit `AuthConfig` for Kubernetes authentication. Falls back to kubeconfig / in-cluster auto-detection. |
| `retry_max_attempts` | `int` | `3` | Maximum retry attempts for transient K8s API errors. |
| `retry_backoff_factor` | `float` | `0.5` | Exponential backoff multiplier between retries. |
| `retry_timeout` | `float` | `60.0` | Total timeout for retry operations (seconds). |
| `hardware_profile_namespace` | `str` | `"redhat-ods-applications"` | Namespace where OpenShift HardwareProfile CRs live. |

## Basic configuration

```python
from kuberay_sdk import KubeRayClient, SDKConfig

client = KubeRayClient(config=SDKConfig(
    namespace="ml-team",
    retry_max_attempts=5,
    retry_backoff_factor=1.0,
    retry_timeout=120.0,
))
```

## Namespace resolution

Namespace is resolved in priority order:

1. **Per-call override** — `namespace=` parameter on the method call
2. **SDKConfig default** — `SDKConfig.namespace`
3. **Kubeconfig context** — the active namespace from your kubeconfig

```python
# Uses SDKConfig.namespace ("ml-team")
cluster = client.create_cluster("my-cluster", workers=2)

# Per-call override takes precedence
cluster = client.create_cluster("my-cluster", workers=2, namespace="other-team")
```

## Authentication

### Auto-detection (default)

With no `auth` parameter, the SDK tries kube-authkit auto-detection, then falls back to standard kubeconfig loading:

```python
client = KubeRayClient()  # Auto-detects credentials
```

### Explicit kube-authkit

```python
from kube_authkit import AuthConfig

client = KubeRayClient(config=SDKConfig(
    auth=AuthConfig(method="oidc", oidc_issuer="https://sso.example.com", client_id="my-app"),
))
```

### In-cluster service account

When running inside a Kubernetes pod (e.g., in a CI pipeline or notebook on the cluster), the SDK automatically uses the pod's service account:

```python
client = KubeRayClient()  # Detects in-cluster environment automatically
```

## Retry behavior

The SDK retries on transient Kubernetes API errors (5xx status codes) with exponential backoff:

```python
config = SDKConfig(
    retry_max_attempts=5,     # Try up to 5 times
    retry_backoff_factor=1.0, # Wait 1s, 2s, 4s, 8s between retries
    retry_timeout=120.0,      # Give up after 120 seconds total
)
```

### Disable retries

```python
config = SDKConfig(retry_max_attempts=0)
```

## OpenShift configuration

When working on OpenShift with custom HardwareProfile locations:

```python
config = SDKConfig(
    hardware_profile_namespace="my-rhoai-namespace",
)
```

## Default configuration

If no `SDKConfig` is provided, the SDK uses these defaults:

```python
# These two are equivalent:
client = KubeRayClient()
client = KubeRayClient(config=SDKConfig())
```
