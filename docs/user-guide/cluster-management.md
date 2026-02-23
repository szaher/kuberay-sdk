# Cluster Management

This guide covers creating, configuring, monitoring, scaling, and deleting Ray clusters.

## Create a cluster (simple mode)

The simplest way to create a cluster uses flat parameters:

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()
cluster = client.create_cluster(
    "my-cluster",
    workers=4,
    cpus_per_worker=2,
    gpus_per_worker=1,
    memory_per_worker="8Gi",
)
cluster.wait_until_ready()
```

## Create a cluster (advanced mode)

For heterogeneous clusters with multiple worker groups, use `WorkerGroup` objects:

```python
from kuberay_sdk.models.cluster import WorkerGroup

cluster = client.create_cluster(
    "hetero-cluster",
    worker_groups=[
        WorkerGroup(name="cpu-workers", replicas=4, cpus=4, memory="8Gi"),
        WorkerGroup(name="gpu-workers", replicas=2, cpus=2, gpus=1, memory="16Gi"),
    ],
)
```

## Custom head node

Override head node resource defaults with [`HeadNodeConfig`][kuberay_sdk.models.cluster.HeadNodeConfig]:

```python
from kuberay_sdk.models.cluster import HeadNodeConfig

cluster = client.create_cluster(
    "custom-head",
    workers=4,
    head=HeadNodeConfig(cpus=4, memory="8Gi"),
)
```

## Autoscaling

Enable Ray autoscaling with min/max replicas per worker group:

```python
cluster = client.create_cluster(
    "autoscale-cluster",
    worker_groups=[
        WorkerGroup(
            name="scalable",
            replicas=2,
            min_replicas=1,
            max_replicas=10,
            cpus=2,
            memory="4Gi",
        ),
    ],
    enable_autoscaling=True,
)
```

## Monitor cluster status

```python
status = cluster.status()
print(f"State: {status.state}")           # CREATING, RUNNING, SUSPENDED, FAILED, DELETING, UNKNOWN
print(f"Head ready: {status.head_ready}")
print(f"Workers: {status.workers_ready}/{status.workers_desired}")
print(f"Ray version: {status.ray_version}")
print(f"Age: {status.age}")
```

## Cluster metrics

Fetch real-time resource utilization from the Ray Dashboard:

```python
metrics = cluster.metrics()
print(f"CPU utilization: {metrics['cpu_utilization']}%")
print(f"GPU utilization: {metrics['gpu_utilization']}%")
print(f"Memory: {metrics['memory_used']} / {metrics['memory_total']}")
```

## Scale workers

Scale the default worker group to a new replica count:

```python
cluster.scale(workers=8)
```

## List clusters

```python
clusters = client.list_clusters()
for c in clusters:
    print(f"{c.name}: {c.state} ({c.workers_ready}/{c.workers_desired} workers)")
```

## Get an existing cluster

```python
cluster = client.get_cluster("my-cluster")
status = cluster.status()
```

## Delete a cluster

```python
# Graceful shutdown
cluster.delete()

# Force delete (skips graceful shutdown)
cluster.delete(force=True)
```

## Raw overrides

Inject arbitrary fields into the generated CRD manifest for advanced K8s configuration:

```python
cluster = client.create_cluster(
    "custom-cluster",
    workers=2,
    raw_overrides={
        "metadata": {"annotations": {"my.co/team": "ml-platform"}},
        "spec": {"rayVersion": "2.41.0"},
    },
)
```

## Labels and node placement

```python
cluster = client.create_cluster(
    "labeled-cluster",
    workers=2,
    labels={"team": "ml-platform", "env": "staging"},
    node_selector={"node-type": "gpu"},
    tolerations=[{"key": "nvidia.com/gpu", "operator": "Exists", "effect": "NoSchedule"}],
)
```
