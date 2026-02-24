# Data Model: SDK UX & Developer Experience Enhancements

**Feature**: 004-sdk-ux-enhancements
**Date**: 2026-02-23

## Modified Entities

### KubeRayError (modified)

**File**: `src/kuberay_sdk/errors.py`
**Change**: Add `remediation` attribute.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `message` | `str` | (required) | Error description |
| `remediation` | `str` | `""` | Step-by-step recovery instructions |
| `details` | `dict[str, Any]` | `{}` | Structured metadata |

**Validation**: None (plain string).
**Relationships**: All error subclasses inherit `remediation`. Each subclass provides a default value.

### SDKConfig (modified)

**File**: `src/kuberay_sdk/config.py`
**Change**: Add config file and env var loading.

| Field | Type | Default | Source Priority |
|-------|------|---------|-----------------|
| `auth` | `Any` | `None` | explicit only |
| `namespace` | `str \| None` | `None` | explicit > env (`KUBERAY_NAMESPACE`) > file > `None` |
| `retry_max_attempts` | `int` | `3` | explicit > env (`KUBERAY_RETRY_MAX_ATTEMPTS`) > file > `3` |
| `retry_backoff_factor` | `float` | `0.5` | explicit > env (`KUBERAY_RETRY_BACKOFF_FACTOR`) > file > `0.5` |
| `retry_timeout` | `float` | `60.0` | explicit > env (`KUBERAY_TIMEOUT`) > file > `60.0` |
| `hardware_profile_namespace` | `str` | `"redhat-ods-applications"` | explicit only |

**New class method**: `SDKConfig.from_defaults()` — loads from env vars and config file, then applies explicit overrides.

### ClusterHandle / JobHandle / ServiceHandle (modified)

**File**: `src/kuberay_sdk/client.py`
**Change**: Add `__repr__` methods.

**ClusterHandle.__repr__**: `ClusterHandle(name='...', namespace='...')`
**JobHandle.__repr__**: `JobHandle(name='...', namespace='...', mode='...')`
**ServiceHandle.__repr__**: `ServiceHandle(name='...', namespace='...')`

Note: `__repr__` uses only cached/constructor values — no API calls (FR-013).

### wait_until_ready / wait methods (modified)

**Files**: `src/kuberay_sdk/client.py`, `src/kuberay_sdk/async_client.py`, `src/kuberay_sdk/services/cluster_service.py`, `src/kuberay_sdk/services/job_service.py`
**Change**: Add `progress_callback` parameter.

**New parameter**: `progress_callback: Callable[[ProgressStatus], None] | None = None`
- When `None`: behavior unchanged (silent blocking).
- When provided: invoked every poll cycle with current status.

### create_cluster / create_job / create_service (modified)

**Files**: `src/kuberay_sdk/client.py`, `src/kuberay_sdk/async_client.py`
**Change**: Add `dry_run` and `preset` parameters.

**New parameters**:
- `dry_run: bool = False` — return manifest without creating resource.
- `preset: str | Preset | None = None` — apply preset defaults (create_cluster only).

---

## New Entities

### ProgressStatus

**File**: `src/kuberay_sdk/models/progress.py`
**Purpose**: Data object passed to progress callbacks during wait operations.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `state` | `str` | (required) | Current resource state (e.g., "creating", "ready") |
| `elapsed_seconds` | `float` | (required) | Seconds since wait started |
| `message` | `str` | `""` | Human-readable status message |
| `metadata` | `dict[str, Any]` | `{}` | Additional context (worker counts, conditions, etc.) |

**Validation**: `elapsed_seconds >= 0`.
**Relationships**: Used by `ClusterHandle.wait_until_ready()`, `JobHandle.wait()`.

### DryRunResult

**File**: `src/kuberay_sdk/models/common.py` (or inline in client)
**Purpose**: Wrapper for dry-run CRD manifest.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `manifest` | `dict[str, Any]` | (required) | Full CRD manifest dictionary |
| `kind` | `str` | (required) | Resource kind (RayCluster, RayJob, RayService) |

**Methods**:
- `to_dict() -> dict[str, Any]` — returns the raw manifest.
- `to_yaml() -> str` — returns YAML-serialized manifest.

**Validation**: `manifest` must contain `apiVersion`, `kind`, `metadata`, `spec`.

### Preset

**File**: `src/kuberay_sdk/presets.py`
**Purpose**: Named, reusable cluster configuration with defaults.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | (required) | Preset identifier (e.g., "dev", "gpu-single") |
| `description` | `str` | `""` | Human-readable description |
| `workers` | `int` | `1` | Default worker count |
| `head_cpu` | `str` | `"1"` | Head node CPU |
| `head_memory` | `str` | `"2Gi"` | Head node memory |
| `worker_cpu` | `str` | `"1"` | Worker CPU |
| `worker_memory` | `str` | `"2Gi"` | Worker memory |
| `worker_gpu` | `int` | `0` | GPU per worker |
| `ray_version` | `str` | `"2.41.0"` | Ray image version |

**Built-in presets**:
- `dev`: 1 worker, 1 CPU, 2Gi — lightweight development.
- `gpu-single`: 1 worker, 4 CPU, 8Gi, 1 GPU — single-GPU training.
- `data-processing`: 4 workers, 2 CPU, 4Gi — multi-node processing.

**Functions**:
- `get_preset(name: str) -> Preset` — look up by name.
- `list_presets() -> list[Preset]` — list all built-in presets.

### ClusterCapabilities

**File**: `src/kuberay_sdk/models/capabilities.py`
**Purpose**: Structured result from capability discovery.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `kuberay_installed` | `bool` | `False` | KubeRay operator CRDs detected |
| `kuberay_version` | `str \| None` | `None` | KubeRay operator version (if detectable) |
| `gpu_available` | `bool \| None` | `None` | GPU nodes detected (`None` = unknown / no permission) |
| `gpu_types` | `list[str]` | `[]` | GPU types found (e.g., "nvidia.com/gpu") |
| `kueue_available` | `bool \| None` | `None` | Kueue CRDs detected |
| `openshift` | `bool \| None` | `None` | OpenShift platform detected |

**Validation**: None (all fields optional/defaulted).
**Relationships**: Returned by `KubeRayClient.get_capabilities()`.

### ConfigFile

**Conceptual entity** — not a model class, but a YAML file schema.

**File path**: `~/.kuberay/config.yaml` (overridable via `KUBERAY_CONFIG` env var).

**Schema**:
```yaml
namespace: string        # Default namespace
timeout: float           # Default timeout in seconds
retry:
  max_attempts: int      # Retry count
  backoff_factor: float  # Backoff multiplier
```

**Validation**: Pydantic model validates after loading. Unknown fields produce a `ValidationError`.

---

## State Transitions

### Error with Remediation (new behavior)

```
Error raised → user reads .remediation → user follows steps → retries operation
```

No SDK state change — remediation is informational.

### Progress Callback Flow

```
wait() called with callback
  ↓
Poll resource status → invoke callback(ProgressStatus) → sleep → repeat
  ↓                                                           ↓
Resource reaches target state → return            Timeout → raise TimeoutError (includes last status)
```

### Dry-Run Flow

```
create_*(dry_run=True) → validate pydantic model → build CRD dict → return DryRunResult
                                ↓ (validation fails)
                         raise ValidationError
```

No Kubernetes API call is made.
