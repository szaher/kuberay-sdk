# New SDK Features

kuberay-sdk v0.2.0 introduces eight new features that simplify configuration, improve observability during long operations, and add new workflows for common tasks. This page covers each feature with examples progressing from basic to advanced usage.

---

## Convenience Imports

*Added in v0.2.0*

All commonly used types are now re-exported from the top-level `kuberay_sdk` package. You no longer need to import from internal submodules.

### Before (v0.1.0)

```python
from kuberay_sdk import KubeRayClient, SDKConfig
from kuberay_sdk.async_client import AsyncKubeRayClient
from kuberay_sdk.models.cluster import WorkerGroup, HeadNodeConfig, ClusterConfig
from kuberay_sdk.models.runtime_env import RuntimeEnv, ExperimentTracking
from kuberay_sdk.models.storage import StorageVolume
from kuberay_sdk.models.job import JobConfig
from kuberay_sdk.models.service import ServiceConfig
```

### After (v0.2.0)

```python
from kuberay_sdk import (
    KubeRayClient,
    AsyncKubeRayClient,
    SDKConfig,
    WorkerGroup,
    HeadNodeConfig,
    ClusterConfig,
    JobConfig,
    ServiceConfig,
    RuntimeEnv,
    ExperimentTracking,
    StorageVolume,
)
```

### Full list of re-exported types

| Type | Previous import path |
|---|---|
| `KubeRayClient` | `kuberay_sdk.client` |
| `AsyncKubeRayClient` | `kuberay_sdk.async_client` |
| `SDKConfig` | `kuberay_sdk.config` |
| `WorkerGroup` | `kuberay_sdk.models.cluster` |
| `HeadNodeConfig` | `kuberay_sdk.models.cluster` |
| `ClusterConfig` | `kuberay_sdk.models.cluster` |
| `JobConfig` | `kuberay_sdk.models.job` |
| `ServiceConfig` | `kuberay_sdk.models.service` |
| `RuntimeEnv` | `kuberay_sdk.models.runtime_env` |
| `ExperimentTracking` | `kuberay_sdk.models.runtime_env` |
| `StorageVolume` | `kuberay_sdk.models.storage` |

!!! tip
    The old import paths still work. Existing code does not need to change.

---

## Configuration File & Environment Variables

*Added in v0.2.0*

In addition to programmatic `SDKConfig`, you can now configure the SDK with a YAML file and environment variables. This is useful when you always target the same namespace or want to share settings across scripts.

### Configuration file

The SDK looks for a config file at `~/.kuberay/config.yaml` by default:

```yaml
# ~/.kuberay/config.yaml
namespace: ml-team
timeout: 300
retry:
  max_attempts: 5
  backoff_factor: 1.0
```

The file is optional. If it does not exist, the SDK uses built-in defaults.

### Environment variables

Override individual settings with environment variables:

| Environment Variable | Config File Field | Default | Description |
|---|---|---|---|
| `KUBERAY_CONFIG` | -- | `~/.kuberay/config.yaml` | Path to the config file |
| `KUBERAY_NAMESPACE` | `namespace` | `None` (kubeconfig context) | Default namespace |
| `KUBERAY_TIMEOUT` | `timeout` | `300` | Default operation timeout (seconds) |
| `KUBERAY_RETRY_MAX_ATTEMPTS` | `retry.max_attempts` | `3` | Maximum retry attempts |
| `KUBERAY_RETRY_BACKOFF_FACTOR` | `retry.backoff_factor` | `0.5` | Exponential backoff multiplier |

```bash
# Set namespace for all SDK operations in this shell session
export KUBERAY_NAMESPACE=ml-team
export KUBERAY_TIMEOUT=600
```

### Precedence

When the same setting is specified in multiple places, the SDK resolves it in this order (highest priority first):

```
explicit SDKConfig args  >  env vars  >  config file  >  built-in defaults
```

For example:

```python
from kuberay_sdk import KubeRayClient, SDKConfig

# This namespace="override" wins over KUBERAY_NAMESPACE and config file
client = KubeRayClient(config=SDKConfig(namespace="override"))
```

!!! warning
    **Do NOT store credentials in the config file.** Authentication is handled by your kubeconfig or kube-authkit configuration, not by the SDK config file. The config file is stored in plain text and is not encrypted.

For the full configuration reference, see [Configuration](configuration.md).

---

## Dry-Run Mode

*Added in v0.2.0*

Dry-run mode lets you preview the Kubernetes manifest that the SDK would create, without making any API calls. This is useful for validating configuration, debugging, and integrating with GitOps workflows.

### Basic usage

Pass `dry_run=True` to any create method. Instead of creating the resource, the SDK returns a `DryRunResult`:

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()

result = client.create_cluster("my-cluster", workers=2, dry_run=True)
```

### Inspect the generated manifest

```python
# Print as YAML (suitable for kubectl apply)
print(result.to_yaml())

# Get as a Python dict for programmatic inspection
manifest = result.to_dict()
print(manifest["spec"]["workerGroupSpecs"][0]["replicas"])
```

### Works for all resource types

Dry-run mode is available for clusters, jobs, and services:

```python
# Dry-run a job
job_result = client.create_job(
    "training-run",
    entrypoint="python train.py",
    workers=4,
    gpus_per_worker=1,
    dry_run=True,
)
print(job_result.to_yaml())

# Dry-run a service
service_result = client.create_service(
    "my-llm",
    import_path="serve_app:deployment",
    num_replicas=2,
    dry_run=True,
)
print(service_result.to_yaml())
```

### Validation without API calls

Dry-run still validates all pydantic models. If your configuration is invalid, you get a `ValidationError` immediately:

```python
from kuberay_sdk.errors import ValidationError

try:
    result = client.create_cluster("INVALID!", workers=-1, dry_run=True)
except ValidationError as e:
    print(e)  # Validation errors are raised even in dry-run mode
```

For more on validation errors, see [Error Handling](error-handling.md).

!!! tip
    Combine dry-run with [Presets](#presets) to preview what a preset generates before creating real resources.

---

## Presets

*Added in v0.2.0*

Presets are named configuration templates for common cluster shapes. Instead of specifying workers, CPU, memory, and GPU counts every time, choose a preset and override only what differs.

### Built-in presets

| Preset | Workers | CPU per Worker | Memory per Worker | GPUs per Worker | Use Case |
|---|---|---|---|---|---|
| `dev` | 1 | 1 | `2Gi` | 0 | Local development and testing |
| `gpu-single` | 1 | 4 | `16Gi` | 1 | Single-GPU training or inference |
| `data-processing` | 4 | 4 | `8Gi` | 0 | CPU-heavy data pipelines |

### Using a preset

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()
cluster = client.create_cluster("my-cluster", preset="dev")
```

### Listing and inspecting presets

```python
from kuberay_sdk.presets import list_presets, get_preset

# List all available preset names
print(list_presets())  # ["dev", "gpu-single", "data-processing"]

# Get full details of a preset
preset = get_preset("gpu-single")
print(preset)
```

### Override preset defaults

Explicit parameters take precedence over the preset. This lets you use a preset as a starting point and adjust specific values:

```python
# Start with gpu-single but use 2 workers instead of 1
cluster = client.create_cluster(
    "multi-gpu",
    preset="gpu-single",
    workers=2,
    memory_per_worker="32Gi",
)
```

### Preview a preset with dry-run

Combine presets with dry-run mode to see the full manifest before creating:

```python
result = client.create_cluster("preview", preset="data-processing", dry_run=True)
print(result.to_yaml())
```

---

## Progress Callbacks

*Added in v0.2.0*

Long-running operations like `wait_until_ready()` and `job.wait()` can now report progress via a callback function. This is useful for logging, progress bars, and notebook UIs.

### Callback signature

The callback receives a `ProgressStatus` object on each poll iteration:

```python
from kuberay_sdk.models.progress import ProgressStatus
```

| Field | Type | Description |
|---|---|---|
| `state` | `str` | Current resource state (e.g., `"CREATING"`, `"RUNNING"`) |
| `elapsed_seconds` | `float` | Seconds since the wait started |
| `message` | `str` | Human-readable status message |
| `metadata` | `dict` | Additional context (e.g., `workers_ready`, `workers_desired`) |

### Basic usage

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()
cluster = client.create_cluster("my-cluster", workers=4)

def on_progress(status):
    print(f"[{status.elapsed_seconds:.0f}s] {status.state}: {status.message}")

cluster.wait_until_ready(progress_callback=on_progress)
```

Output:

```
[2s] CREATING: Waiting for head node to start
[5s] CREATING: Head node running, waiting for workers (1/4 ready)
[12s] CREATING: Workers starting (3/4 ready)
[15s] RUNNING: Cluster is ready (4/4 workers)
```

### Progress callbacks for jobs

```python
job = client.create_job("training-run", entrypoint="python train.py", workers=4)

job.wait(progress_callback=lambda s: print(f"{s.state}: {s.message}"))
```

### Error handling in callbacks

Exceptions raised inside the callback are caught and logged. They do not interrupt the wait operation:

```python
def flaky_callback(status):
    if status.elapsed_seconds > 10:
        raise RuntimeError("Something went wrong in the callback")

# The wait continues even if the callback raises
cluster.wait_until_ready(progress_callback=flaky_callback)
```

### Timeout behavior

When a wait operation times out, the `TimeoutError` includes the last known status:

```python
from kuberay_sdk.errors import TimeoutError

try:
    cluster.wait_until_ready(timeout=30, progress_callback=on_progress)
except TimeoutError as e:
    print(f"Timed out. Last status: {e.last_status}")
```

---

## Compound Operations

*Added in v0.2.0*

Compound operations combine multiple steps into a single call for common workflows.

### Create cluster and submit job

The most common pattern -- create a cluster, wait for it to become ready, and submit a job -- is now a single method:

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()

job = client.create_cluster_and_submit_job(
    "training-cluster",
    entrypoint="python train.py --epochs=10",
    workers=4,
    gpus_per_worker=1,
    memory_per_worker="16Gi",
)

# job is a JobHandle — the cluster is already running
result = job.wait()
print(job.logs())
```

This is equivalent to:

```python
cluster = client.create_cluster("training-cluster", workers=4, gpus_per_worker=1, memory_per_worker="16Gi")
cluster.wait_until_ready()
job = cluster.submit_job(entrypoint="python train.py --epochs=10")
```

### Error handling

If cluster creation succeeds but the job submission fails, the cluster is **not** automatically deleted. The error includes a reference to the cluster handle so you can inspect or clean up:

```python
from kuberay_sdk.errors import JobError

try:
    job = client.create_cluster_and_submit_job(
        "my-cluster",
        entrypoint="python train.py",
        workers=4,
    )
except JobError as e:
    print(f"Job submission failed: {e}")
    # The cluster is still running — clean up if needed
    if e.cluster_handle is not None:
        print(f"Cluster '{e.cluster_handle.name}' is still running")
        e.cluster_handle.delete()
```

!!! warning
    The cluster is intentionally kept alive on failure so you can inspect logs, dashboard state, and debug the issue. Delete it explicitly when done.

---

## Capability Discovery

*Added in v0.2.0*

Discover what features are available on the connected Kubernetes cluster before writing logic that depends on them. This is useful for writing portable code that adapts to different environments.

### Basic usage

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()
caps = client.get_capabilities()
```

### ClusterCapabilities fields

| Field | Type | Description |
|---|---|---|
| `kuberay_installed` | `bool \| None` | Whether the KubeRay operator CRDs are present |
| `kuberay_version` | `str \| None` | Installed KubeRay operator version |
| `gpu_available` | `bool \| None` | Whether GPU nodes are available in the cluster |
| `gpu_types` | `list[str] \| None` | GPU types available (e.g., `["nvidia-a100", "nvidia-t4"]`) |
| `kueue_available` | `bool \| None` | Whether Kueue (job queueing) is installed |
| `openshift` | `bool \| None` | Whether the cluster is running OpenShift |

!!! tip
    A value of `None` means "unknown" -- the SDK could not determine the capability, typically because the service account lacks the necessary RBAC permissions to query it.

### Conditional logic

```python
caps = client.get_capabilities()

if not caps.kuberay_installed:
    print("KubeRay operator is not installed. Please install it first.")
    exit(1)

if caps.gpu_available:
    cluster = client.create_cluster("gpu-training", workers=2, gpus_per_worker=1)
else:
    print("No GPUs available, falling back to CPU-only cluster")
    cluster = client.create_cluster("cpu-training", workers=4)

if caps.kueue_available:
    print("Kueue detected — jobs will be queued automatically")

if caps.openshift:
    print(f"Running on OpenShift (KubeRay {caps.kuberay_version})")
```

---

## CLI Tool

*Added in v0.2.0*

kuberay-sdk now includes a `kuberay` command-line tool for managing Ray resources directly from the terminal. The CLI wraps the Python SDK and uses the same configuration (kubeconfig, config file, environment variables).

### Quick examples

```bash
# List all clusters in the current namespace
kuberay cluster list

# Create a cluster with a preset
kuberay cluster create my-cluster --preset dev

# Check cluster status
kuberay cluster status my-cluster

# Submit a job to an existing cluster
kuberay job create --cluster my-cluster --entrypoint "python train.py"

# List jobs
kuberay job list

# Stream job logs
kuberay job logs my-job --follow

# Delete a cluster
kuberay cluster delete my-cluster
```

### Dry-run from the CLI

```bash
kuberay cluster create my-cluster --workers 4 --gpus-per-worker 1 --dry-run
```

This prints the generated YAML manifest to stdout without creating the resource.

For the full list of commands and options, see [CLI Reference](cli-reference.md).

---

---

## Rich Display & Notebook Integration

*Added in v0.3.0*

The SDK now provides rich output for terminals and Jupyter notebooks via optional extras.

### Install

```bash
pip install kuberay-sdk[rich]      # Terminal: styled tables, progress bars, colored logs
pip install kuberay-sdk[notebook]  # Notebook: HTML tables, widget progress, action buttons
pip install kuberay-sdk[display]   # Both
```

### Auto progress bars

Wait operations now show progress bars automatically (no callback needed):

```python
cluster = client.create_cluster("my-cluster", workers=4)
cluster.wait_until_ready()  # Shows: ⠋ CREATING ━━━━━━━━━━ 12s
```

### Display function

A new `display()` function renders resource data with the best available backend:

```python
from kuberay_sdk.display import display

clusters = client.list_clusters()
display(clusters)  # Styled table in terminal, HTML table in notebook
```

### Notebook cards

Resource handles render as styled HTML cards when evaluated in a notebook cell:

```python
cluster  # Shows card with Name, Namespace, State, and action buttons
```

### Environment detection

The SDK auto-detects Jupyter, Colab, VS Code notebooks, and TTY terminals. Override with `KUBERAY_DISPLAY=plain|rich|notebook|auto`.

For the full guide, see [Rich Display & Notebook Integration](rich-display.md).

---

## Next Steps

- [Configuration](configuration.md) -- full configuration reference including auth and retry settings
- [Cluster Management](cluster-management.md) -- detailed cluster lifecycle guide
- [Job Submission](job-submission.md) -- job submission patterns and log streaming
- [Error Handling](error-handling.md) -- error hierarchy and recovery patterns
- [Troubleshooting](troubleshooting.md) -- common issues and solutions
