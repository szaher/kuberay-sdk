# Ray Serve

This guide covers deploying, monitoring, updating, and deleting Ray Serve applications.

## Create a service

Deploy a Ray Serve application by specifying the import path to your deployment:

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()

service = client.create_service(
    "my-llm",
    import_path="serve_app:deployment",
    num_replicas=2,
    gpus_per_worker=1,
    memory_per_worker="16Gi",
)
```

## Check service status

```python
status = service.status()
print(f"State: {status.state}")
print(f"Endpoint URL: {status.endpoint_url}")
```

## Update a service

Update replica count, import path, or runtime environment without redeploying:

```python
# Scale replicas
service.update(num_replicas=4)

# Update the application code
service.update(import_path="serve_app_v2:deployment")

# Update runtime environment
service.update(runtime_env={"pip": ["transformers>=4.40"]})
```

## Heterogeneous workers for agentic workloads

Use worker groups for services that need mixed hardware (e.g., CPU workers for routing, GPU workers for inference):

```python
from kuberay_sdk.models.cluster import WorkerGroup

service = client.create_service(
    "agentic-service",
    import_path="agent_app:deployment",
    worker_groups=[
        WorkerGroup(name="cpu-routers", replicas=2, cpus=2, memory="4Gi"),
        WorkerGroup(name="gpu-inference", replicas=4, cpus=2, gpus=1, memory="16Gi"),
    ],
)
```

## Custom head node and storage

```python
from kuberay_sdk.models.cluster import HeadNodeConfig
from kuberay_sdk.models.storage import StorageVolume

service = client.create_service(
    "model-service",
    import_path="serve_app:deployment",
    head=HeadNodeConfig(cpus=2, memory="4Gi"),
    storage=[
        StorageVolume(name="models", mount_path="/models", existing_claim="shared-models-pvc"),
    ],
)
```

## OpenShift Route

On OpenShift, enable automatic Route creation for external access:

```python
service = client.create_service(
    "public-service",
    import_path="serve_app:deployment",
    route_enabled=True,
)
```

## List services

```python
services = client.list_services()
for svc in services:
    print(f"{svc.name}: {svc.state} — {svc.endpoint_url}")
```

## Get an existing service

```python
service = client.get_service("my-llm")
status = service.status()
```

## Delete a service

```python
service.delete()
```
