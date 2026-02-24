# kuberay-sdk

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green)
![Status Alpha](https://img.shields.io/badge/status-alpha-orange)

A user-friendly Python SDK for managing Ray clusters, jobs, and services on Kubernetes and OpenShift via [KubeRay](https://ray-project.github.io/kuberay/).

## Overview

kuberay-sdk wraps the KubeRay CRD API and the Ray Dashboard REST API into a high-level Python interface. Instead of writing YAML manifests and calling `kubectl`, you get a typed, validated, handle-based workflow.

Key features:

- **Handle-based API** — `create_cluster()` returns a `ClusterHandle` you can `.scale()`, `.delete()`, or `.submit_job()` on
- **Two cluster modes** — simple (workers/cpus/gpus/memory) or advanced (explicit `WorkerGroup` list)
- **Job submission** — via KubeRay CRD (standalone RayJob) or Dashboard REST API (submit to running cluster)
- **Ray Serve** — deploy, update, and inspect RayService resources
- **OpenShift integration** — hardware profiles, Route creation, platform detection
- **Kueue integration** — queue label injection, constraint validation
- **Pydantic models** — validated configs for clusters, jobs, services, storage, and runtime environments
- **Async support** — `AsyncKubeRayClient` mirrors every sync method
- **Retry with backoff** — configurable retry for transient K8s API errors
- **Auth delegation** — uses [kube-authkit](https://pypi.org/project/kube-authkit/) for Kubernetes authentication

## Installation

```bash
pip install kuberay-sdk
```

### Prerequisites

- Python 3.10+
- A Kubernetes cluster with the [KubeRay operator](https://ray-project.github.io/kuberay/deploy/installation/) installed
- `kubectl` configured with access to the target cluster (kubeconfig)

## Quick Start

### Create a Ray Cluster

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()
cluster = client.create_cluster("my-cluster", workers=2, cpus_per_worker=2, memory_per_worker="4Gi")
cluster.wait_until_ready()

status = cluster.status()
print(f"Cluster {status.name}: {status.state}, {status.workers_ready}/{status.workers_desired} workers")
```

### Submit a Job

```python
job = client.create_job(
    "my-job",
    entrypoint="python train.py --epochs 10",
    workers=4,
    gpus_per_worker=1,
)
result = job.wait()
print(job.logs())
```

### Deploy a Ray Serve Application

```python
service = client.create_service(
    "my-service",
    import_path="serve_app:app",
    num_replicas=2,
)
status = service.status()
print(f"Endpoint: {status.endpoint_url}")
```

## Core Concepts

### KubeRayClient

The main entry point. Instantiate with an optional `SDKConfig` to set defaults (namespace, retry policy). All `create_*` / `get_*` / `list_*` methods live here.

```python
from kuberay_sdk import KubeRayClient, SDKConfig

client = KubeRayClient(config=SDKConfig(
    namespace="ml-team",
    retry_max_attempts=5,
))
```

### Handles

Every `create_*` or `get_*` call returns a **handle** — a lightweight object bound to a specific resource. Handles carry the resource name and namespace and provide all operations for that resource type.

| Handle | Returned by | Key methods |
|---|---|---|
| `ClusterHandle` | `create_cluster()`, `get_cluster()` | `status()`, `scale()`, `delete()`, `wait_until_ready()`, `dashboard_url()`, `metrics()`, `submit_job()`, `list_jobs()` |
| `JobHandle` | `create_job()`, `get_job()`, `cluster.submit_job()` | `status()`, `logs()`, `stop()`, `wait()`, `progress()`, `download_artifacts()` |
| `ServiceHandle` | `create_service()`, `get_service()` | `status()`, `update()`, `delete()` |

### Namespace Resolution

Namespace is resolved in this order:

1. Explicit `namespace=` parameter on the method call
2. `SDKConfig.namespace` default
3. Active namespace from kubeconfig context

## API Reference

### KubeRayClient Methods

| Method | Description |
|---|---|
| `create_cluster(name, ...)` | Create a RayCluster and return a `ClusterHandle` |
| `get_cluster(name, *, namespace=)` | Get a handle to an existing RayCluster |
| `list_clusters(*, namespace=)` | List all RayClusters, returns `list[ClusterStatus]` |
| `create_job(name, entrypoint, ...)` | Create a standalone RayJob and return a `JobHandle` |
| `get_job(name, *, namespace=)` | Get a handle to an existing RayJob |
| `list_jobs(*, namespace=)` | List all RayJobs |
| `create_service(name, import_path, ...)` | Create a RayService and return a `ServiceHandle` |
| `get_service(name, *, namespace=)` | Get a handle to an existing RayService |
| `list_services(*, namespace=)` | List all RayServices, returns `list[ServiceStatus]` |

### ClusterHandle

| Method | Description |
|---|---|
| `status()` | Returns `ClusterStatus` with state, worker counts, age, conditions |
| `scale(workers)` | Scale the default worker group to `workers` replicas |
| `delete(force=False)` | Delete the cluster. `force=True` skips graceful shutdown |
| `wait_until_ready(timeout=300)` | Block until the cluster reaches RUNNING state |
| `dashboard_url()` | Discover the Ray Dashboard URL (Route / Ingress / port-forward) |
| `metrics()` | Fetch cluster metrics (CPU, GPU, memory utilization) via Dashboard |
| `submit_job(entrypoint, ...)` | Submit a job to this cluster via the Dashboard API |
| `list_jobs()` | List jobs submitted to this cluster via Dashboard |

### JobHandle

| Method | Description |
|---|---|
| `status()` | Returns current job status |
| `logs(*, stream=False, follow=False, tail=None)` | Get job logs. `stream=True` returns an iterator |
| `stop()` | Stop the running job |
| `wait(timeout=3600)` | Block until the job completes |
| `progress()` | Get job progress information |
| `download_artifacts(destination)` | Download job artifacts to a local directory |

### ServiceHandle

| Method | Description |
|---|---|
| `status()` | Returns `ServiceStatus` with state, endpoint URL, replica counts |
| `update(*, num_replicas=, import_path=, runtime_env=)` | Update service configuration |
| `delete()` | Delete the service |

## Advanced Usage

### Heterogeneous Worker Groups

Use `WorkerGroup` objects for clusters with mixed hardware:

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

### Custom Head Node

```python
from kuberay_sdk.models.cluster import HeadNodeConfig

cluster = client.create_cluster(
    "custom-head",
    workers=4,
    head=HeadNodeConfig(cpus=2, memory="4Gi"),
)
```

### Storage Volumes

Attach persistent storage to cluster pods:

```python
from kuberay_sdk.models.storage import StorageVolume

cluster = client.create_cluster(
    "cluster-with-storage",
    workers=2,
    storage=[
        StorageVolume(name="data", mount_path="/mnt/data", size="100Gi"),
        StorageVolume(name="models", mount_path="/mnt/models", existing_claim="shared-models-pvc"),
    ],
)
```

### Runtime Environment

Install packages and set environment variables:

```python
from kuberay_sdk.models.runtime_env import RuntimeEnv

job = client.create_job(
    "training-job",
    entrypoint="python train.py",
    runtime_env=RuntimeEnv(
        pip=["torch>=2.0", "transformers", "datasets"],
        env_vars={"WANDB_PROJECT": "my-project"},
        working_dir="/app",
    ),
)
```

### Experiment Tracking (MLflow)

```python
from kuberay_sdk.models.runtime_env import ExperimentTracking

job = client.create_job(
    "tracked-job",
    entrypoint="python train.py",
    experiment_tracking=ExperimentTracking(
        provider="mlflow",
        tracking_uri="http://mlflow.ml-infra:5000",
        experiment_name="bert-finetune",
    ),
)
```

### Submit Job to Running Cluster (Dashboard API)

```python
cluster = client.get_cluster("my-cluster")
cluster.wait_until_ready()

job = cluster.submit_job(
    entrypoint="python eval.py",
    runtime_env={"pip": ["scikit-learn"]},
)
print(job.logs(stream=True))
```

### OpenShift Features

```python
# Hardware profiles resolve GPU types, tolerations, and node selectors automatically
cluster = client.create_cluster(
    "gpu-cluster",
    hardware_profile="nvidia-gpu-large",
    workers=2,
)

# Kueue queue integration
job = client.create_job(
    "queued-job",
    entrypoint="python train.py",
    queue="team-a-queue",
)
```

### Autoscaling

```python
cluster = client.create_cluster(
    "autoscale-cluster",
    worker_groups=[
        WorkerGroup(name="scalable", replicas=1, min_replicas=1, max_replicas=10, cpus=2),
    ],
    enable_autoscaling=True,
)
```

### Raw Overrides

Inject arbitrary fields into the generated CRD manifest:

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

### Async Client

```python
import asyncio
from kuberay_sdk import AsyncKubeRayClient

async def main():
    client = AsyncKubeRayClient()
    cluster = await client.create_cluster("async-cluster", workers=2)
    await cluster.wait_until_ready()
    status = await cluster.status()
    print(f"{status.name}: {status.state}")
    await cluster.delete()

asyncio.run(main())
```

### Convenience Imports

*Added in v0.2.0*

Common types are re-exported from the top-level package, so you don't need deep module imports:

```python
# Instead of this:
from kuberay_sdk.models.cluster import WorkerGroup
from kuberay_sdk.models.runtime_env import RuntimeEnv
from kuberay_sdk.models.storage import StorageVolume

# You can write this:
from kuberay_sdk import KubeRayClient, WorkerGroup, RuntimeEnv, StorageVolume
```

All re-exported types: `KubeRayClient`, `AsyncKubeRayClient`, `SDKConfig`, `WorkerGroup`, `HeadNodeConfig`, `ClusterConfig`, `JobConfig`, `ServiceConfig`, `RuntimeEnv`, `ExperimentTracking`, `StorageVolume`.

### Configuration File & Environment Variables

*Added in v0.2.0*

The SDK can load settings from a YAML config file and environment variables, eliminating repeated `SDKConfig` boilerplate:

```yaml
# ~/.kuberay/config.yaml
namespace: ml-team
timeout: 120
retry:
  max_attempts: 5
  backoff_factor: 1.0
```

```python
from kuberay_sdk import KubeRayClient

# No SDKConfig needed — loads from config file automatically
client = KubeRayClient()
```

Environment variables override the config file:

```bash
export KUBERAY_NAMESPACE=experiments
export KUBERAY_TIMEOUT=300
```

**Configuration precedence** (highest to lowest):

1. Explicit `SDKConfig(...)` arguments
2. `KUBERAY_*` environment variables
3. `~/.kuberay/config.yaml` file
4. Built-in defaults

Available environment variables: `KUBERAY_CONFIG` (config file path), `KUBERAY_NAMESPACE`, `KUBERAY_TIMEOUT`, `KUBERAY_RETRY_MAX_ATTEMPTS`, `KUBERAY_RETRY_BACKOFF_FACTOR`.

> **Security note**: The config file stores operational settings only (namespace, timeout, retry).
> Do NOT store credentials or auth tokens in this file.
> Authentication is handled by kubeconfig and [kube-authkit](https://pypi.org/project/kube-authkit/).

### Dry-Run Mode

*Added in v0.2.0*

Preview the CRD manifest that would be created, without making any Kubernetes API call:

```python
result = client.create_cluster("test-cluster", workers=4, dry_run=True)

# Inspect as a dictionary
print(result.to_dict()["spec"]["workerGroupSpecs"][0]["replicas"])  # 4

# Export as YAML for review or kubectl apply
print(result.to_yaml())
```

Dry-run works for `create_cluster()`, `create_job()`, and `create_service()`. It validates the pydantic models locally and returns a `DryRunResult` without contacting the API server.

### Presets

*Added in v0.2.0*

Built-in presets provide opinionated defaults for common cluster configurations:

```python
from kuberay_sdk.presets import list_presets

# See available presets
for p in list_presets():
    print(f"{p.name}: {p.description}")
# dev: Lightweight development cluster
# gpu-single: Single-GPU training node
# data-processing: Multi-node data processing

# Create a cluster with a preset
cluster = client.create_cluster("training", preset="gpu-single")

# Override preset defaults with explicit parameters
cluster = client.create_cluster("big-training", preset="gpu-single", workers=4)
```

### Progress Callbacks

*Added in v0.2.0*

Monitor long-running wait operations with a callback:

```python
def on_progress(status):
    print(f"[{status.elapsed_seconds:.0f}s] {status.state} — {status.message}")

cluster.wait_until_ready(timeout=300, progress_callback=on_progress)
# [5s] creating — Waiting for head pod...
# [15s] creating — Head pod running, waiting for workers...
# [25s] ready — All 4/4 workers ready
```

The callback receives a `ProgressStatus` object with `state`, `elapsed_seconds`, `message`, and `metadata` fields. Also works with `job.wait(progress_callback=...)`.

### Compound Operations

*Added in v0.2.0*

The most common workflow — create a cluster, wait for it, and submit a job — in a single call:

```python
job = client.create_cluster_and_submit_job(
    cluster_name="ephemeral",
    workers=4,
    entrypoint="python train.py",
)
print(job.status())
```

On failure, the partially-created cluster is **not** deleted. The error includes the cluster handle so you can inspect or clean up.

### Capability Discovery

*Added in v0.2.0*

Discover what features are available on the cluster before attempting operations:

```python
caps = client.get_capabilities()

if caps.gpu_available:
    cluster = client.create_cluster("gpu-job", preset="gpu-single")
else:
    cluster = client.create_cluster("cpu-job", preset="data-processing")

if caps.kueue_available:
    cluster = client.create_cluster("queued", queue="default")
```

Returns a `ClusterCapabilities` object with `kuberay_installed`, `kuberay_version`, `gpu_available`, `gpu_types`, `kueue_available`, and `openshift` fields. Fields set to `None` mean the SDK lacked permissions to detect that capability.

### CLI Tool

*Added in v0.2.0*

Manage Ray resources from the terminal without writing Python scripts:

```bash
# List clusters
$ kuberay cluster list
NAME            STATE    WORKERS   AGE
training        ready    4/4       2h
dev             creating 0/2       5m

# Create with a preset
$ kuberay cluster create my-cluster --preset gpu-single --workers 2

# JSON output for scripting
$ kuberay cluster list --output json | jq '.[].name'

# Check cluster capabilities
$ kuberay capabilities
```

For the full command reference with all subcommands and options, see the [CLI Reference](https://szaher.github.io/kuberay-sdk/user-guide/cli-reference/).

## Configuration

`SDKConfig` controls client-wide defaults:

| Field | Type | Default | Description |
|---|---|---|---|
| `namespace` | `str \| None` | `None` | Default namespace. Falls back to kubeconfig context |
| `retry_max_attempts` | `int` | `3` | Max retry attempts for transient errors |
| `retry_backoff_factor` | `float` | `0.5` | Exponential backoff multiplier |
| `retry_timeout` | `float` | `60.0` | Total timeout for retry operations (seconds) |
| `hardware_profile_namespace` | `str` | `"redhat-ods-applications"` | Namespace for OpenShift HardwareProfile CRs |

```python
from kuberay_sdk import KubeRayClient, SDKConfig

client = KubeRayClient(config=SDKConfig(
    namespace="ml-team",
    retry_max_attempts=5,
    retry_backoff_factor=1.0,
    retry_timeout=120.0,
))
```

## Error Handling

The SDK defines a hierarchy of domain-specific errors:

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

Raw Kubernetes API errors are automatically translated via `translate_k8s_error()`:

```python
from kuberay_sdk.errors import ClusterNotFoundError, TimeoutError

try:
    cluster = client.get_cluster("missing-cluster")
except ClusterNotFoundError as e:
    print(f"Cluster not found: {e}")

try:
    cluster.wait_until_ready(timeout=60)
except TimeoutError as e:
    print(f"Timed out: {e}")
```

## Development

### Setup

```bash
git clone https://github.com/your-org/kuberay-sdk.git
cd kuberay-sdk
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Testing

```bash
pytest                              # run all tests
pytest -m "not integration"         # skip integration tests
pytest --tb=short -q                # concise output
```

### Linting

```bash
ruff check src/ tests/              # lint
ruff format --check src/ tests/     # format check
mypy src/                           # type check
```
