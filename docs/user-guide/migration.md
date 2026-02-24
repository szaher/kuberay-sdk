# Migration Guide: If You Know kubectl

This guide provides a side-by-side comparison of common `kubectl` commands for managing KubeRay resources and their equivalent operations using the kuberay-sdk Python client. If you are already familiar with managing RayClusters, RayJobs, and RayServices via `kubectl`, this guide will help you transition to the SDK quickly.

---

## Quick Setup

Before using the SDK, initialize the client:

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()
```

The `KubeRayClient` automatically uses your current kubeconfig context, just like `kubectl` does.

---

## Cluster Operations

### List All Clusters

=== "kubectl"

    ```bash
    kubectl get rayclusters -n my-namespace
    ```

=== "kuberay-sdk"

    ```python
    clusters = client.list_clusters(namespace="my-namespace")
    for c in clusters:
        print(c.name, c.state)
    ```

### Get a Specific Cluster

=== "kubectl"

    ```bash
    kubectl get raycluster my-cluster -n my-namespace -o yaml
    ```

=== "kuberay-sdk"

    ```python
    cluster = client.get_cluster("my-cluster", namespace="my-namespace")
    status = cluster.status()
    print(status.state, status.workers_ready)
    ```

### Create a Cluster

=== "kubectl"

    ```bash
    kubectl apply -f cluster.yaml
    ```

    Where `cluster.yaml` is a full RayCluster manifest (typically 50+ lines of YAML).

=== "kuberay-sdk"

    ```python
    cluster = client.create_cluster(
        "my-cluster",
        workers=4,
        cpus_per_worker=2.0,
        gpus_per_worker=1,
        memory_per_worker="8Gi",
        image="rayproject/ray:2.9.0",
    )
    cluster.wait_until_ready()
    ```

### Delete a Cluster

=== "kubectl"

    ```bash
    kubectl delete raycluster my-cluster -n my-namespace
    ```

=== "kuberay-sdk"

    ```python
    cluster = client.get_cluster("my-cluster")
    cluster.delete()
    ```

### Scale a Cluster

=== "kubectl"

    ```bash
    kubectl patch raycluster my-cluster -n my-namespace \
      --type=merge \
      -p '{"spec":{"workerGroupSpecs":[{"replicas":8,"groupName":"default-worker"}]}}'
    ```

=== "kuberay-sdk"

    ```python
    cluster = client.get_cluster("my-cluster")
    cluster.scale(workers=8)
    ```

### Access the Ray Dashboard

=== "kubectl"

    ```bash
    kubectl port-forward svc/my-cluster-head-svc 8265:8265 -n my-namespace
    # Then open http://localhost:8265
    ```

=== "kuberay-sdk"

    ```python
    cluster = client.get_cluster("my-cluster")
    url = cluster.dashboard_url()
    print(f"Dashboard: {url}")
    ```

---

## Job Operations

### List All Jobs

=== "kubectl"

    ```bash
    kubectl get rayjobs -n my-namespace
    ```

=== "kuberay-sdk"

    ```python
    jobs = client.list_jobs(namespace="my-namespace")
    for j in jobs:
        print(j)
    ```

### Get a Specific Job

=== "kubectl"

    ```bash
    kubectl get rayjob my-job -n my-namespace -o yaml
    ```

=== "kuberay-sdk"

    ```python
    job = client.get_job("my-job", namespace="my-namespace")
    status = job.status()
    print(status.state)
    ```

### Create a Job

=== "kubectl"

    ```bash
    kubectl apply -f job.yaml
    ```

    Where `job.yaml` is a full RayJob manifest with embedded cluster spec.

=== "kuberay-sdk"

    ```python
    job = client.create_job(
        "training-job",
        entrypoint="python train.py --epochs=10",
        workers=4,
        gpus_per_worker=1,
        runtime_env={"pip": ["torch", "transformers"]},
    )
    job.wait()
    print(job.logs())
    ```

### Delete a Job

=== "kubectl"

    ```bash
    kubectl delete rayjob my-job -n my-namespace
    ```

=== "kuberay-sdk"

    ```python
    job = client.get_job("my-job")
    job.stop()
    ```

### View Job Logs

=== "kubectl"

    ```bash
    kubectl logs -l ray.io/cluster=my-job,ray.io/node-type=head -n my-namespace
    ```

=== "kuberay-sdk"

    ```python
    job = client.get_job("my-job")
    # Full logs
    print(job.logs())
    # Or stream in real-time
    for line in job.logs(stream=True, follow=True):
        print(line)
    ```

---

## Service Operations

### List All Services

=== "kubectl"

    ```bash
    kubectl get rayservices -n my-namespace
    ```

=== "kuberay-sdk"

    ```python
    services = client.list_services(namespace="my-namespace")
    for s in services:
        print(s.name, s.state)
    ```

### Get a Specific Service

=== "kubectl"

    ```bash
    kubectl get rayservice my-llm -n my-namespace -o yaml
    ```

=== "kuberay-sdk"

    ```python
    service = client.get_service("my-llm", namespace="my-namespace")
    status = service.status()
    print(status.state, status.endpoint_url)
    ```

### Create a Service

=== "kubectl"

    ```bash
    kubectl apply -f service.yaml
    ```

    Where `service.yaml` is a full RayService manifest with serve configuration.

=== "kuberay-sdk"

    ```python
    service = client.create_service(
        "my-llm",
        import_path="serve_app:deployment",
        num_replicas=2,
        gpus_per_worker=1,
    )
    ```

### Delete a Service

=== "kubectl"

    ```bash
    kubectl delete rayservice my-llm -n my-namespace
    ```

=== "kuberay-sdk"

    ```python
    service = client.get_service("my-llm")
    service.delete()
    ```

### Update a Service

=== "kubectl"

    ```bash
    kubectl patch rayservice my-llm -n my-namespace \
      --type=merge \
      -p '{"spec":{"serveConfigV2":{"applications":[{"numReplicas":4}]}}}'
    ```

=== "kuberay-sdk"

    ```python
    service = client.get_service("my-llm")
    service.update(num_replicas=4)
    ```

---

## Complete Reference Table

The table below summarizes all kubectl-to-SDK mappings:

| kubectl Command | SDK Equivalent |
|---|---|
| `kubectl get rayclusters` | `client.list_clusters()` |
| `kubectl get raycluster NAME` | `client.get_cluster(NAME)` |
| `kubectl apply -f cluster.yaml` | `client.create_cluster(...)` |
| `kubectl delete raycluster NAME` | `cluster.delete()` |
| `kubectl scale` (via patch) | `cluster.scale(workers=N)` |
| `kubectl port-forward` | `cluster.dashboard_url()` |
| `kubectl get rayjobs` | `client.list_jobs()` |
| `kubectl get rayjob NAME` | `client.get_job(NAME)` |
| `kubectl apply -f job.yaml` | `client.create_job(...)` |
| `kubectl delete rayjob NAME` | `job.stop()` |
| `kubectl logs` (job pods) | `job.logs()` |
| `kubectl get rayservices` | `client.list_services()` |
| `kubectl get rayservice NAME` | `client.get_service(NAME)` |
| `kubectl apply -f service.yaml` | `client.create_service(...)` |
| `kubectl delete rayservice NAME` | `service.delete()` |
| `kubectl patch rayservice` | `service.update(...)` |

---

## Key Advantages of the SDK

Compared to raw `kubectl` commands, the kuberay-sdk provides several benefits:

1. **No YAML authoring** -- create clusters, jobs, and services with simple Python function calls instead of writing verbose YAML manifests.

2. **Built-in waiting and polling** -- `cluster.wait_until_ready()` and `job.wait()` handle polling for you, with configurable timeouts.

3. **Integrated log streaming** -- `job.logs(stream=True)` streams logs in real-time without needing to find the correct pod name.

4. **Automatic dashboard access** -- `cluster.dashboard_url()` automatically sets up port-forwarding or discovers Ingress/Routes.

5. **Type-safe models** -- Pydantic models validate your configuration at creation time, catching errors before they reach the API server.

6. **Pythonic error handling** -- structured exceptions with clear messages instead of raw HTTP errors.

```python
from kuberay_sdk import KubeRayClient
from kuberay_sdk.errors import NotFoundError, QuotaExceededError

client = KubeRayClient()
try:
    cluster = client.get_cluster("nonexistent")
except NotFoundError as e:
    print(f"Cluster not found: {e}")
except QuotaExceededError as e:
    print(f"Quota exceeded: {e}")
```

---

## Next Steps

- [Quick Start](getting-started/quick-start.md) -- get up and running in 5 minutes.
- [Cluster Management](cluster-management.md) -- detailed cluster lifecycle guide.
- [Job Submission](job-submission.md) -- learn about job submission patterns.
- [Error Handling](error-handling.md) -- understand SDK error types and recovery.
- [Troubleshooting](troubleshooting.md) -- resolve common issues.
