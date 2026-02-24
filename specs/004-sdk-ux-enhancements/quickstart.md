# Quickstart: SDK UX Enhancements

**Feature**: 004-sdk-ux-enhancements

## Scenario 1: Actionable Error Recovery

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()

try:
    cluster = client.get_cluster("nonexistent")
except Exception as e:
    print(f"Error: {e}")
    print(f"How to fix:\n{e.remediation}")
    # Output:
    # Error: Ray cluster 'nonexistent' not found in namespace 'default'.
    # How to fix:
    # Check cluster name with: kubectl get rayclusters -n default
    # Verify namespace: kubectl config view --minify -o jsonpath='{..namespace}'
```

## Scenario 2: Progress Monitoring

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()
cluster = client.create_cluster("my-cluster", workers=4)

# With progress feedback
def on_progress(status):
    print(f"[{status.elapsed_seconds:.0f}s] State: {status.state} — {status.message}")

cluster.wait_until_ready(timeout=300, progress_callback=on_progress)
# Output:
# [5s] State: creating — Waiting for head pod...
# [10s] State: creating — Head pod running, waiting for workers...
# [20s] State: ready — All 4/4 workers ready
```

## Scenario 3: Config File + Env Vars

```yaml
# ~/.kuberay/config.yaml
namespace: ml-team
timeout: 120
retry:
  max_attempts: 5
```

```python
from kuberay_sdk import KubeRayClient

# No SDKConfig needed — loads from config file automatically
client = KubeRayClient()
# client._config.namespace == "ml-team"
# client._config.retry_timeout == 120.0
```

```bash
# Or via environment variables (override config file)
export KUBERAY_NAMESPACE=experiments
export KUBERAY_TIMEOUT=300
```

## Scenario 4: Handle Inspection in Notebook

```python
>>> from kuberay_sdk import KubeRayClient
>>> client = KubeRayClient()
>>> cluster = client.get_cluster("training-cluster")
>>> cluster
ClusterHandle(name='training-cluster', namespace='default')
>>> job = cluster.submit_job("python train.py")
>>> job
JobHandle(name='training-job-abc', namespace='default', mode='DASHBOARD')
```

## Scenario 5: Convenience Imports

```python
# Before: deep imports
from kuberay_sdk.models.cluster import WorkerGroup
from kuberay_sdk.models.runtime_env import RuntimeEnv
from kuberay_sdk.models.storage import StorageVolume

# After: top-level imports
from kuberay_sdk import KubeRayClient, WorkerGroup, RuntimeEnv, StorageVolume
```

## Scenario 6: Dry-Run / Preview

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()

# Preview the manifest without creating anything
result = client.create_cluster("test", workers=4, dry_run=True)

# Inspect as dict
print(result.to_dict()["spec"]["workerGroupSpecs"][0]["replicas"])  # 4

# Export as YAML for review or kubectl apply
print(result.to_yaml())
# apiVersion: ray.io/v1
# kind: RayCluster
# metadata:
#   name: test
# ...
```

## Scenario 7: Preset Usage

```python
from kuberay_sdk import KubeRayClient
from kuberay_sdk.presets import list_presets

# See available presets
for p in list_presets():
    print(f"{p.name}: {p.description}")
# dev: Lightweight development cluster
# gpu-single: Single-GPU training node
# data-processing: Multi-node data processing

# Create with preset
client = KubeRayClient()
cluster = client.create_cluster("training", preset="gpu-single")

# Override preset defaults
cluster = client.create_cluster("big-training", preset="gpu-single", workers=4)
```

## Scenario 8: Compound Operation

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()

# Single call: create cluster → wait → submit job
job = client.create_cluster_and_submit_job(
    cluster_name="ephemeral",
    workers=4,
    entrypoint="python train.py",
)
print(job.status())
```

## Scenario 9: CLI Usage

```bash
# List clusters
$ kuberay cluster list
NAME            STATE    WORKERS   AGE
training        ready    4/4       2h
dev             creating 0/2       5m

# Create with preset
$ kuberay cluster create my-cluster --preset gpu-single --workers 2

# Submit job
$ kuberay job create training-run --entrypoint "python train.py" --cluster my-cluster

# JSON output for scripting
$ kuberay cluster list --output json | jq '.[].name'

# Check capabilities
$ kuberay capabilities
CAPABILITY      STATUS
KubeRay         v1.2.0
GPU             nvidia.com/gpu (2 nodes)
Kueue           not installed
OpenShift       not detected
```

## Scenario 10: Capability Discovery

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()
caps = client.get_capabilities()

if caps.gpu_available:
    cluster = client.create_cluster("gpu-job", preset="gpu-single")
else:
    cluster = client.create_cluster("cpu-job", preset="data-processing")

if caps.kueue_available:
    # Use Kueue queue
    cluster = client.create_cluster("queued", queue="default")
```

## Scenario 11: Retry Jitter

No user-facing code change. The retry mechanism now adds random jitter automatically:

```python
# Before: all clients retry at exactly 0.5s, 1.0s, 2.0s
# After:  client A retries at 0.3s, 0.8s, 1.5s
#         client B retries at 0.4s, 0.9s, 1.7s
# Thundering herd eliminated
```
