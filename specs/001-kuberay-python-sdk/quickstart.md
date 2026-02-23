# Quickstart: KubeRay Python SDK

**Feature**: 001-kuberay-python-sdk
**Date**: 2026-02-23

## Installation

```bash
pip install kuberay-sdk
```

## Prerequisites

- Python 3.9+
- Access to a Kubernetes or OpenShift cluster (via kubeconfig)
- KubeRay operator v1.1+ installed on the cluster

## 1. Create a Ray Cluster

```python
from kuberay_sdk import KubeRayClient

# Authenticate (uses your kubeconfig automatically)
client = KubeRayClient()

# Create a cluster with 4 GPU workers
cluster = client.create_cluster(
    name="training-cluster",
    workers=4,
    gpus_per_worker=1,
    memory_per_worker="8Gi",
)

# Wait for the cluster to be ready
cluster.wait_until_ready(timeout=300)
print(cluster.status())
```

## 2. Submit a Job to the Cluster

```python
# Submit a training script to the running cluster
job = cluster.submit_job(
    entrypoint="python train.py --epochs=10",
    runtime_env={
        "pip": ["torch", "transformers"],
        "working_dir": "./src",
    },
)

# Stream logs in real-time
for line in job.logs(stream=True):
    print(line)

# Check final status
print(job.status())
```

## 3. Create a Standalone RayJob (Disposable Cluster)

```python
# Create a job that provisions its own cluster and tears it down after
job = client.create_job(
    name="one-off-training",
    entrypoint="python train.py",
    workers=2,
    gpus_per_worker=1,
    runtime_env={"pip": ["torch"]},
)

# Wait for completion
job.wait(timeout=3600)
print(f"Job finished: {job.status().state}")
```

## 4. Deploy a Model with Ray Serve

```python
# Deploy an LLM serving endpoint
service = client.create_service(
    name="my-llm",
    import_path="serve_app:deployment",
    num_replicas=2,
    gpus_per_worker=1,
    memory_per_worker="16Gi",
)

# Get the endpoint URL
status = service.status()
print(f"Serving at: {status.endpoint_url}")
```

## 5. Access the Ray Dashboard

```python
# Get the dashboard URL (auto port-forwards if needed)
url = cluster.dashboard_url()
print(f"Dashboard: {url}")

# Get cluster metrics
metrics = cluster.metrics()
print(f"CPU usage: {metrics['cpu_utilization']}%")
```

## 6. Scale and Clean Up

```python
# Scale workers
cluster.scale(workers=8)

# Delete when done
cluster.delete()
```

## Advanced Usage

### Heterogeneous Worker Groups

```python
from kuberay_sdk.models import WorkerGroup

cluster = client.create_cluster(
    name="mixed-cluster",
    worker_groups=[
        WorkerGroup(name="cpu-workers", replicas=4, cpus=4, memory="8Gi"),
        WorkerGroup(name="gpu-workers", replicas=2, cpus=2, gpus=1, memory="16Gi"),
    ],
)
```

### OpenShift Hardware Profiles

```python
# Use a predefined GPU profile (OpenShift only)
cluster = client.create_cluster(
    name="gpu-cluster",
    workers=2,
    hardware_profile="gpu-large",
)
```

### Kueue Queue Assignment

```python
# Submit a job through a Kueue queue
job = client.create_job(
    name="queued-training",
    entrypoint="python train.py",
    workers=4,
    queue="training-queue",
)
```

### Storage Volumes

```python
from kuberay_sdk.models import StorageVolume

cluster = client.create_cluster(
    name="storage-cluster",
    workers=2,
    storage=[
        StorageVolume(name="data", size="100Gi", mount_path="/data"),
        StorageVolume(name="models", existing_claim="shared-models", mount_path="/models"),
    ],
)
```

### MLflow Experiment Tracking

```python
job = client.create_job(
    name="tracked-training",
    entrypoint="python train.py",
    workers=2,
    experiment_tracking={
        "provider": "mlflow",
        "tracking_uri": "http://mlflow:5000",
        "experiment_name": "my-experiment",
    },
)
```

### Async Client

```python
import asyncio
from kuberay_sdk import AsyncKubeRayClient

async def main():
    client = AsyncKubeRayClient()

    # Create multiple clusters concurrently
    clusters = await asyncio.gather(
        client.create_cluster(name="cluster-a", workers=2),
        client.create_cluster(name="cluster-b", workers=4),
    )

    for c in clusters:
        await c.wait_until_ready()

asyncio.run(main())
```

### Cross-Namespace Operations

```python
# Default namespace from kubeconfig
client = KubeRayClient()

# Override per-call
clusters = client.list_clusters(namespace="other-team")
cluster = client.get_cluster("their-cluster", namespace="other-team")
```

### Advanced Kubernetes Options

```python
cluster = client.create_cluster(
    name="advanced-cluster",
    workers=4,
    labels={"team": "ml-platform", "env": "staging"},
    annotations={"custom.io/owner": "alice"},
    tolerations=[{"key": "gpu", "operator": "Exists", "effect": "NoSchedule"}],
    node_selector={"node-type": "gpu"},
)
```

### Raw CRD Overrides

```python
# For use cases not covered by the high-level API
cluster = client.create_cluster(
    name="custom-cluster",
    workers=2,
    raw_overrides={
        "spec": {
            "enableInTreeAutoscaling": True,
            "headGroupSpec": {
                "rayStartParams": {"dashboard-host": "0.0.0.0"},
            },
        },
    },
)
```
