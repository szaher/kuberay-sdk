# Architecture

This page describes the internal structure of kuberay-sdk for contributors who want to understand how the codebase is organized.

## Module structure

```
src/kuberay_sdk/
├── __init__.py          # Public API exports (KubeRayClient, AsyncKubeRayClient, SDKConfig)
├── client.py            # KubeRayClient + ClusterHandle, JobHandle, ServiceHandle
├── async_client.py      # AsyncKubeRayClient + async handle variants
├── config.py            # SDKConfig, namespace resolution, K8s client setup, CRD detection
├── errors.py            # Error hierarchy + translate_k8s_error()
├── retry.py             # Retry decorator with exponential backoff
├── models/              # Pydantic models for configuration and status
│   ├── cluster.py       # WorkerGroup, HeadNodeConfig, ClusterConfig, ClusterStatus
│   ├── job.py           # JobConfig, JobStatus
│   ├── service.py       # ServiceConfig, ServiceStatus
│   ├── storage.py       # StorageVolume (PVC management)
│   ├── runtime_env.py   # RuntimeEnv, ExperimentTracking
│   └── common.py        # ClusterState enum, ResourceRequirements, deep_merge()
├── services/            # Business logic layer (K8s API interactions)
│   ├── cluster_service.py  # CRUD + status + scaling for RayClusters
│   ├── job_service.py      # CRUD + status + waiting for RayJobs
│   ├── service_service.py  # CRUD + status + updates for RayServices
│   ├── dashboard.py        # Ray Dashboard REST API client (httpx)
│   └── port_forward.py     # Dashboard URL discovery and port-forwarding
└── platform/            # Platform-specific integrations
    ├── detection.py     # OpenShift vs. vanilla K8s detection
    ├── openshift.py     # HardwareProfile resolution, Route creation
    └── kueue.py         # Kueue queue label injection and validation
```

## The Handle pattern

Every `create_*()` or `get_*()` call on `KubeRayClient` returns a **Handle** object — a lightweight wrapper bound to a specific resource. Handles carry the resource name, namespace, and a back-reference to the client.

```
KubeRayClient.create_cluster("my-cluster")
    → ClusterHandle(name="my-cluster", namespace="default", client=self)
        → .status()   → ClusterService.get_status()
        → .scale(n)   → ClusterService.scale()
        → .delete()   → ClusterService.delete()
        → .submit_job() → DashboardClient → JobHandle
```

Handles provide a fluent, resource-oriented API. Users never interact with service classes directly.

## Request flow: create_cluster()

1. `KubeRayClient.create_cluster()` is called with user parameters
2. `resolve_namespace()` determines the effective namespace
3. `ClusterService.create()` is called with all parameters
4. `ClusterConfig` Pydantic model validates inputs
5. `ClusterConfig.to_crd_dict()` generates the CRD manifest
6. If `hardware_profile` is set, `openshift.resolve_hardware_profile()` injects GPU config
7. If `queue` is set, the `kueue.x-k8s.io/queue-name` label is injected
8. `CustomObjectsApi.create_namespaced_custom_object()` sends the manifest to K8s
9. A `ClusterHandle` is returned to the user

## CRD generation

Models in `models/` are responsible for generating KubeRay CRD manifests. The flow is:

- `ClusterConfig.to_crd_dict()` → `ray.io/v1 RayCluster` manifest
- `JobConfig.to_crd_dict()` → `ray.io/v1 RayJob` manifest
- `ServiceConfig.to_crd_dict()` → `ray.io/v1 RayService` manifest

Each model handles:

- K8s name validation (lowercase alphanumeric, 1-63 chars)
- Resource requirements (CPU, GPU, memory)
- Volume mounts from `StorageVolume`
- Runtime environment serialization
- Label and annotation injection
- `raw_overrides` deep merge for escape-hatch customization

## Dashboard API client

The `DashboardClient` in `services/dashboard.py` uses `httpx` to communicate with the Ray Dashboard REST API. It handles:

- Job submission to running clusters
- Log retrieval and streaming
- Job status and progress queries
- Cluster metrics
- Artifact download

Dashboard URL discovery (`services/port_forward.py`) checks in order:

1. OpenShift Route
2. Kubernetes Ingress
3. Port-forward fallback

## Async implementation

`AsyncKubeRayClient` wraps the synchronous client using `ThreadPoolExecutor` and `asyncio.run_in_executor()`. Each async method delegates to the corresponding sync service method in a thread pool. This approach avoids duplicating all business logic while providing a native async interface.

## Error translation

All raw Kubernetes `ApiException` errors are caught at the service layer and translated via `translate_k8s_error()` into domain-specific errors (e.g., 404 → `ClusterNotFoundError`, 401/403 → `AuthenticationError`).
