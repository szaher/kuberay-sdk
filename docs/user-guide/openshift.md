# OpenShift Integration

kuberay-sdk includes built-in support for Red Hat OpenShift features: hardware profiles, Kueue queue integration, automatic Route creation, and platform detection.

## Platform detection

The SDK can auto-detect whether it's running on OpenShift:

```python
from kuberay_sdk.platform.detection import detect_platform

platform = detect_platform()
print(f"Platform: {platform}")  # "openshift" or "kubernetes"
```

## Hardware profiles

On OpenShift AI (RHOAI), hardware profiles define GPU types, tolerations, and node selectors. Pass a profile name and the SDK resolves the underlying Kubernetes configuration:

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()

cluster = client.create_cluster(
    "gpu-cluster",
    hardware_profile="nvidia-gpu-large",
    workers=2,
)
```

The hardware profile namespace defaults to `redhat-ods-applications`. Override it via `SDKConfig`:

```python
from kuberay_sdk import KubeRayClient, SDKConfig

client = KubeRayClient(config=SDKConfig(
    hardware_profile_namespace="my-custom-namespace",
))
```

## Kueue queue integration

Submit workloads to a [Kueue](https://kueue.sigs.k8s.io/) queue by name. The SDK injects the `kueue.x-k8s.io/queue-name` label into the resource metadata:

```python
# Cluster with queue
cluster = client.create_cluster(
    "queued-cluster",
    workers=4,
    queue="team-a-queue",
)

# Job with queue
job = client.create_job(
    "queued-job",
    entrypoint="python train.py",
    workers=4,
    queue="team-a-queue",
)
```

## OpenShift Routes

On OpenShift, enable automatic Route creation for Ray Serve services to expose endpoints externally:

```python
service = client.create_service(
    "public-service",
    import_path="serve_app:deployment",
    route_enabled=True,
)

status = service.status()
print(f"Endpoint: {status.endpoint_url}")  # Route URL on OpenShift
```

## Dashboard URL discovery

The SDK automatically discovers the Ray Dashboard URL via OpenShift Routes or Ingress resources. If neither exists, it falls back to port-forwarding:

```python
cluster = client.get_cluster("my-cluster")
url = cluster.dashboard_url()
print(f"Dashboard: {url}")
```
