# Data Model: KubeRay Python SDK

**Feature**: 001-kuberay-python-sdk
**Date**: 2026-02-23
**Source**: [spec.md](spec.md), [research.md](research.md)

## Entity Overview

```text
SDKConfig ─────────── KubeRayClient
                          │
                ┌─────────┼──────────┐
                │         │          │
          RayCluster   RayJob   RayService
                │         │          │
                └────┬────┘          │
                     │               │
              ┌──────┴──────┐        │
              │             │        │
         StorageVolume  RuntimeEnv   │
                                     │
                              ServiceEndpoint
```

## Entities

### 1. SDKConfig

SDK-level configuration. Created once, passed to client constructor.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `namespace` | `str` | No | From kubeconfig context | Default namespace for all operations |
| `auth` | `AuthConfig` | No | `AuthConfig(method="auto")` | kube-authkit auth configuration |
| `retry_max_attempts` | `int` | No | `3` | Max retry attempts for transient errors |
| `retry_backoff_factor` | `float` | No | `0.5` | Exponential backoff multiplier (seconds) |
| `retry_timeout` | `float` | No | `60.0` | Total retry timeout (seconds) |
| `hardware_profile_namespace` | `str` | No | `"redhat-ods-applications"` | Namespace where HardwareProfile CRs live |

**Validation Rules:**
- `retry_max_attempts` >= 0
- `retry_backoff_factor` > 0
- `retry_timeout` > 0

**Relationships:**
- Composed into `KubeRayClient` (1:1)
- `auth` delegates to `kube_authkit.AuthConfig`

---

### 2. RayCluster

Represents a Ray cluster. Maps to KubeRay `RayCluster` CR (`ray.io/v1`).

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | `str` | Yes | — | Cluster name (K8s resource name) |
| `namespace` | `str` | No | Client default | Target namespace |
| `workers` | `int` | No* | `1` | Worker count (simple mode) |
| `cpus_per_worker` | `float` | No | `1.0` | CPUs per worker (simple mode) |
| `gpus_per_worker` | `int` | No | `0` | GPUs per worker (simple mode) |
| `memory_per_worker` | `str` | No | `"2Gi"` | Memory per worker (simple mode) |
| `worker_groups` | `list[WorkerGroup]` | No* | — | Heterogeneous worker groups (advanced mode) |
| `head` | `HeadNodeConfig` | No | Auto-configured | Head node resource override |
| `ray_version` | `str` | No | Latest stable | Ray version string (e.g., `"2.41.0"`) |
| `image` | `str` | No | Derived from `ray_version` | Full container image (overrides `ray_version`) |
| `storage` | `list[StorageVolume]` | No | `[]` | Volumes to mount |
| `runtime_env` | `RuntimeEnv` | No | — | Default runtime env for all jobs |
| `labels` | `dict[str, str]` | No | `{}` | K8s labels on the CR |
| `annotations` | `dict[str, str]` | No | `{}` | K8s annotations on the CR |
| `tolerations` | `list[dict]` | No | `[]` | Pod tolerations |
| `node_selector` | `dict[str, str]` | No | `{}` | Pod node selector |
| `hardware_profile` | `str` | No | — | OpenShift HardwareProfile name |
| `queue` | `str` | No | — | Kueue LocalQueue name |
| `enable_autoscaling` | `bool` | No | `False` | Enable Ray autoscaler |
| `raw_overrides` | `dict` | No | — | Raw patches to CRD spec |

*Mutually exclusive: use `workers`/`gpus_per_worker` (simple) OR `worker_groups` (advanced), never both.

**Validation Rules:**
- `name` must be a valid K8s resource name (lowercase, alphanumeric, hyphens; max 63 chars)
- `workers` >= 1 (when used)
- `cpus_per_worker` > 0
- `gpus_per_worker` >= 0
- `worker_groups` and flat params (`workers`, `gpus_per_worker`, etc.) are mutually exclusive — error if both provided
- If `hardware_profile` is set, resource params (`cpus_per_worker`, `gpus_per_worker`, `memory_per_worker`) should not be set (profile provides them)

**State Transitions:**

```text
Creating ──► Running ──► Deleting ──► Deleted
    │            │
    │            └──► Suspended (Kueue)
    │                     │
    │                     └──► Running (resumed)
    └──► Failed
```

---

### 3. WorkerGroup

A group of homogeneous workers within a RayCluster. Used in advanced (heterogeneous) mode.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | `str` | Yes | — | Group name (e.g., `"gpu-workers"`) |
| `replicas` | `int` | Yes | — | Number of workers in this group |
| `min_replicas` | `int` | No | `replicas` | Min workers (autoscaling) |
| `max_replicas` | `int` | No | `replicas` | Max workers (autoscaling) |
| `cpus` | `float` | No | `1.0` | CPUs per worker |
| `gpus` | `int` | No | `0` | GPUs per worker |
| `memory` | `str` | No | `"2Gi"` | Memory per worker |
| `gpu_type` | `str` | No | — | GPU resource name (e.g., `"nvidia.com/gpu"`) |
| `ray_start_params` | `dict[str, str]` | No | `{}` | Extra Ray start parameters |

**Validation Rules:**
- `replicas` >= 1
- `min_replicas` <= `replicas` <= `max_replicas`
- `name` must be unique within the cluster

---

### 4. HeadNodeConfig

Override head node resource defaults.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `cpus` | `float` | No | `1.0` | CPUs for head node |
| `memory` | `str` | No | `"2Gi"` | Memory for head node |
| `gpus` | `int` | No | `0` | GPUs for head node (unusual) |
| `ray_start_params` | `dict[str, str]` | No | `{}` | Extra Ray start parameters |

---

### 5. ClusterStatus

Read-only status returned by `cluster.status()` and `list_clusters()`.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Cluster name |
| `namespace` | `str` | Namespace |
| `state` | `ClusterState` | `CREATING`, `RUNNING`, `SUSPENDED`, `FAILED`, `DELETING`, `UNKNOWN` |
| `head_ready` | `bool` | Whether head pod is ready |
| `workers_ready` | `int` | Number of ready workers |
| `workers_desired` | `int` | Desired worker count |
| `ray_version` | `str` | Ray version on the cluster |
| `dashboard_url` | `str \| None` | Dashboard URL if available |
| `age` | `timedelta` | Time since creation |
| `conditions` | `list[Condition]` | Human-readable status conditions |

---

### 6. RayJob

Represents a Ray job. Two modes: CRD-based (disposable cluster) or Dashboard-submitted (existing cluster).

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | `str` | Yes | — | Job name |
| `namespace` | `str` | No | Client default | Target namespace |
| `entrypoint` | `str` | Yes | — | Command to run (e.g., `"python train.py"`) |
| `runtime_env` | `RuntimeEnv` | No | — | Runtime environment config |
| `cluster_name` | `str` | No* | — | Existing cluster to submit to (Dashboard mode) |
| `workers` | `int` | No* | `1` | Workers for disposable cluster (CRD mode) |
| `cpus_per_worker` | `float` | No | `1.0` | CPUs per worker (CRD mode) |
| `gpus_per_worker` | `int` | No | `0` | GPUs per worker (CRD mode) |
| `memory_per_worker` | `str` | No | `"2Gi"` | Memory per worker (CRD mode) |
| `worker_groups` | `list[WorkerGroup]` | No | — | Heterogeneous workers (CRD mode) |
| `head` | `HeadNodeConfig` | No | Auto-configured | Head node override (CRD mode) |
| `ray_version` | `str` | No | Latest stable | Ray version (CRD mode) |
| `image` | `str` | No | Derived | Container image (CRD mode) |
| `storage` | `list[StorageVolume]` | No | `[]` | Volumes to mount (CRD mode) |
| `shutdown_after_finish` | `bool` | No | `True` | Delete cluster after job (CRD mode) |
| `labels` | `dict[str, str]` | No | `{}` | K8s labels |
| `annotations` | `dict[str, str]` | No | `{}` | K8s annotations |
| `queue` | `str` | No | — | Kueue LocalQueue name |
| `hardware_profile` | `str` | No | — | OpenShift HardwareProfile name |
| `experiment_tracking` | `ExperimentTracking` | No | — | MLflow config |
| `raw_overrides` | `dict` | No | — | Raw patches to CRD spec |

*Mode selection: if `cluster_name` is provided, uses Dashboard submission. Otherwise, creates a RayJob CR with disposable cluster.

**Validation Rules:**
- `entrypoint` must not be empty
- `cluster_name` and cluster resource params (`workers`, `worker_groups`, etc.) are mutually exclusive
- If `queue` is set and mode is CRD, `shutdown_after_finish` must be `True` (Kueue constraint)
- If `queue` is set, max 7 worker groups (Kueue 8-PodSet limit)

**State Transitions (CRD mode):**

```text
Pending ──► Running ──► Succeeded
    │           │
    │           └──► Failed
    │           │
    │           └──► Stopped (user cancelled)
    └──► Suspended (Kueue) ──► Pending (resumed)
```

**State Transitions (Dashboard mode):**

```text
PENDING ──► RUNNING ──► SUCCEEDED
                │
                └──► FAILED
                │
                └──► STOPPED
```

---

### 7. JobStatus

Read-only status returned by `job.status()` and `list_jobs()`.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Job name / job ID |
| `namespace` | `str` | Namespace |
| `state` | `JobState` | `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `STOPPED`, `SUSPENDED`, `UNKNOWN` |
| `mode` | `JobMode` | `CRD` or `DASHBOARD` |
| `entrypoint` | `str` | Job entrypoint command |
| `submitted_at` | `datetime` | Submission timestamp |
| `duration` | `timedelta \| None` | Duration (if completed) |
| `error_message` | `str \| None` | Error details (if failed) |
| `cluster_name` | `str \| None` | Associated cluster |

---

### 8. RayService

Represents a Ray Serve deployment. Maps to KubeRay `RayService` CR.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | `str` | Yes | — | Service name |
| `namespace` | `str` | No | Client default | Target namespace |
| `import_path` | `str` | Yes | — | Python import path (e.g., `"serve_app:deployment"`) |
| `runtime_env` | `RuntimeEnv` | No | — | Runtime environment |
| `num_replicas` | `int` | No | `1` | Number of serve replicas |
| `ray_version` | `str` | No | Latest stable | Ray version |
| `image` | `str` | No | Derived | Container image |
| `workers` | `int` | No | `1` | Backing cluster workers |
| `cpus_per_worker` | `float` | No | `1.0` | CPUs per worker |
| `gpus_per_worker` | `int` | No | `0` | GPUs per worker |
| `memory_per_worker` | `str` | No | `"2Gi"` | Memory per worker |
| `worker_groups` | `list[WorkerGroup]` | No | — | Heterogeneous workers |
| `head` | `HeadNodeConfig` | No | Auto-configured | Head node override |
| `storage` | `list[StorageVolume]` | No | `[]` | Volumes to mount |
| `labels` | `dict[str, str]` | No | `{}` | K8s labels |
| `annotations` | `dict[str, str]` | No | `{}` | K8s annotations |
| `route_enabled` | `bool` | No | `True` on OpenShift | Auto-create Route |
| `serve_config_v2` | `str` | No | — | Raw serveConfigV2 YAML (advanced) |
| `raw_overrides` | `dict` | No | — | Raw patches to CRD spec |

**Validation Rules:**
- `import_path` must not be empty (unless `serve_config_v2` is provided)
- `num_replicas` >= 1
- `import_path` and `serve_config_v2` are mutually exclusive

---

### 9. ServiceStatus

Read-only status returned by `service.status()`.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Service name |
| `namespace` | `str` | Namespace |
| `state` | `ServiceState` | `DEPLOYING`, `RUNNING`, `UNHEALTHY`, `FAILED`, `DELETING`, `UNKNOWN` |
| `endpoint_url` | `str \| None` | Serve endpoint URL |
| `route_url` | `str \| None` | OpenShift Route URL (if applicable) |
| `replicas_ready` | `int` | Ready replica count |
| `replicas_desired` | `int` | Desired replica count |
| `age` | `timedelta` | Time since creation |

---

### 10. StorageVolume

Volume attachment for clusters and jobs.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | `str` | Yes | — | Volume name (used as PVC name prefix) |
| `mount_path` | `str` | Yes | — | Mount path inside containers |
| `size` | `str` | No* | — | PVC size (e.g., `"100Gi"`) — for new PVCs |
| `existing_claim` | `str` | No* | — | Name of existing PVC — for existing PVCs |
| `access_mode` | `str` | No | `"ReadWriteOnce"` | PVC access mode |
| `storage_class` | `str` | No | Cluster default | Storage class name |

*Mutually exclusive: `size` (create new PVC) or `existing_claim` (use existing). Exactly one must be set.

**Validation Rules:**
- Exactly one of `size` or `existing_claim` must be provided
- `mount_path` must be an absolute path
- `access_mode` must be one of: `ReadWriteOnce`, `ReadOnlyMany`, `ReadWriteMany`

---

### 11. RuntimeEnv

Ray runtime environment configuration.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `pip` | `list[str]` | No | `[]` | pip packages to install |
| `conda` | `str \| dict` | No | — | Conda env name or spec |
| `env_vars` | `dict[str, str]` | No | `{}` | Environment variables |
| `working_dir` | `str` | No | — | Working directory (local path or URI) |
| `py_modules` | `list[str]` | No | `[]` | Python modules to upload |

**Validation Rules:**
- `pip` and `conda` are mutually exclusive (Ray constraint)
- `pip` entries must be valid pip requirement strings

---

### 12. ExperimentTracking

MLflow experiment tracking configuration.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `provider` | `str` | Yes | — | Tracking provider (currently: `"mlflow"`) |
| `tracking_uri` | `str` | Yes | — | MLflow tracking server URI |
| `experiment_name` | `str` | No | — | Experiment name |
| `env_vars` | `dict[str, str]` | No | `{}` | Additional env vars for tracking |

**Validation Rules:**
- `provider` must be `"mlflow"` (only supported provider)
- `tracking_uri` must be a valid URI

**SDK Behavior:**
Experiment tracking is implemented by injecting env vars into the RuntimeEnv:
- `MLFLOW_TRACKING_URI` ← `tracking_uri`
- `MLFLOW_EXPERIMENT_NAME` ← `experiment_name`
- Additional vars from `env_vars`

---

## Enumerations

### ClusterState
`CREATING` | `RUNNING` | `SUSPENDED` | `FAILED` | `DELETING` | `UNKNOWN`

### JobState
`PENDING` | `RUNNING` | `SUCCEEDED` | `FAILED` | `STOPPED` | `SUSPENDED` | `UNKNOWN`

### JobMode
`CRD` | `DASHBOARD`

### ServiceState
`DEPLOYING` | `RUNNING` | `UNHEALTHY` | `FAILED` | `DELETING` | `UNKNOWN`

## Relationships

| From | To | Cardinality | Description |
|------|----|-------------|-------------|
| KubeRayClient | SDKConfig | 1:1 | Client holds config |
| RayCluster | WorkerGroup | 1:N | Cluster has 1+ worker groups |
| RayCluster | HeadNodeConfig | 1:1 | Cluster has one head node |
| RayCluster | StorageVolume | 1:N | Cluster mounts 0+ volumes |
| RayCluster | RuntimeEnv | 1:0..1 | Cluster may have default runtime env |
| RayJob | StorageVolume | 1:N | CRD-mode job mounts 0+ volumes |
| RayJob | RuntimeEnv | 1:0..1 | Job may have runtime env |
| RayJob | ExperimentTracking | 1:0..1 | Job may have tracking config |
| RayJob | RayCluster | N:1 | Dashboard-mode jobs target a cluster |
| RayService | WorkerGroup | 1:N | Service has 1+ worker groups |
| RayService | StorageVolume | 1:N | Service mounts 0+ volumes |
| RayService | RuntimeEnv | 1:0..1 | Service may have runtime env |
