# Error Handling

kuberay-sdk translates raw Kubernetes API errors into domain-specific exceptions with user-friendly messages in Ray/ML terms. All errors inherit from [`KubeRayError`][kuberay_sdk.errors.KubeRayError].

## Error hierarchy

```
KubeRayError (base)
├── ClusterError
│   ├── ClusterNotFoundError
│   └── ClusterAlreadyExistsError
├── JobError
│   └── JobNotFoundError
├── ServiceError
│   └── ServiceNotFoundError
├── DashboardUnreachableError
├── KubeRayOperatorNotFoundError
├── AuthenticationError
├── ValidationError
├── ResourceConflictError
└── TimeoutError
```

## Catching specific errors

```python
from kuberay_sdk import KubeRayClient
from kuberay_sdk.errors import (
    ClusterNotFoundError,
    TimeoutError,
    AuthenticationError,
    KubeRayOperatorNotFoundError,
)

client = KubeRayClient()

# Handle missing cluster
try:
    cluster = client.get_cluster("nonexistent")
except ClusterNotFoundError as e:
    print(f"Cluster not found: {e}")

# Handle timeout
try:
    cluster.wait_until_ready(timeout=60)
except TimeoutError as e:
    print(f"Timed out: {e}")
```

## Common error scenarios

### Cluster not found

```python
from kuberay_sdk.errors import ClusterNotFoundError

try:
    cluster = client.get_cluster("missing-cluster")
except ClusterNotFoundError as e:
    print(e)  # "Ray cluster 'missing-cluster' not found in namespace 'default'."
```

### Authentication failure

```python
from kuberay_sdk.errors import AuthenticationError

try:
    client = KubeRayClient()
except AuthenticationError as e:
    print(e)  # "Authentication failed. Please check your kubeconfig or re-authenticate."
```

### KubeRay operator not installed

```python
from kuberay_sdk.errors import KubeRayOperatorNotFoundError

try:
    client = KubeRayClient()
except KubeRayOperatorNotFoundError as e:
    print(e)  # "KubeRay operator is not installed on this cluster..."
```

### Validation errors

```python
from kuberay_sdk.errors import ValidationError

try:
    cluster = client.create_cluster("INVALID_NAME!", workers=2)
except ValidationError as e:
    print(e)  # "Invalid cluster name 'INVALID_NAME!': must be lowercase alphanumeric..."
```

### Dashboard unreachable

```python
from kuberay_sdk.errors import DashboardUnreachableError

try:
    url = cluster.dashboard_url()
except DashboardUnreachableError as e:
    print(e)  # "Ray Dashboard for cluster 'my-cluster' is not reachable."
```

## K8s error translation

The SDK automatically translates Kubernetes API exceptions into domain-specific errors via `translate_k8s_error()`:

| K8s Status Code | SDK Error |
|---|---|
| 401, 403 | `AuthenticationError` |
| 404 | `ClusterNotFoundError` / `JobNotFoundError` / `ServiceNotFoundError` |
| 409 | `ResourceConflictError` |
| 422 | `ValidationError` |
| 5xx | `KubeRayError` (with "transient" message and auto-retry) |

## Error details

All errors include a `details` dict with structured context:

```python
try:
    cluster = client.get_cluster("missing")
except ClusterNotFoundError as e:
    print(e.details)  # {"name": "missing", "namespace": "default"}
```

## Recovery patterns

### Retry on transient failures

The SDK automatically retries on 5xx server errors using the retry policy from `SDKConfig`:

```python
from kuberay_sdk import KubeRayClient, SDKConfig

client = KubeRayClient(config=SDKConfig(
    retry_max_attempts=5,
    retry_backoff_factor=1.0,
    retry_timeout=120.0,
))
```

### Catching the base error

To catch all SDK errors, use `KubeRayError`:

```python
from kuberay_sdk.errors import KubeRayError

try:
    cluster = client.create_cluster("my-cluster", workers=4)
    cluster.wait_until_ready()
except KubeRayError as e:
    print(f"SDK error: {e}")
```
