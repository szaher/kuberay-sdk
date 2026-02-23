# Research: KubeRay Python SDK

**Feature**: 001-kuberay-python-sdk
**Date**: 2026-02-23
**Status**: Complete

## 1. KubeRay CRD Schemas

### Decision
Target KubeRay CRD API version `ray.io/v1`. Support operator versions v1.1+ (minimum for Kueue integration), with latest tested against v1.5.1.

### Rationale
`ray.io/v1` is the stable API group used by all current KubeRay CRDs (RayCluster, RayJob, RayService). The `v1alpha1` version is deprecated. The constitution requires supporting the two most recent minor versions.

### Key Findings

**CRD Resources:**

| CRD | API Group | Plural | Scope |
|-----|-----------|--------|-------|
| RayCluster | `ray.io/v1` | `rayclusters` | Namespaced |
| RayJob | `ray.io/v1` | `rayjobs` | Namespaced |
| RayService | `ray.io/v1` | `rayservices` | Namespaced |

**RayCluster Spec Structure:**
- `headGroupSpec`: Head pod template — `rayStartParams`, `template` (PodTemplateSpec)
- `workerGroupSpecs[]`: List of worker groups — each has `groupName`, `replicas`, `minReplicas`, `maxReplicas`, `rayStartParams`, `template`
- `rayVersion`: String (e.g., `"2.41.0"`) — informational, does not select image
- `enableInTreeAutoscaling`: Boolean — enables Ray autoscaler
- `suspendSpec`: Used by Kueue for workload suspension

**RayJob Spec Structure:**
- `entrypoint`: Command string (e.g., `"python train.py"`)
- `runtimeEnvYAML`: YAML string for Ray runtime environment
- `rayClusterSpec`: Inline cluster spec (for disposable clusters)
- `clusterSelector`: Map to select existing cluster (mutually exclusive with `rayClusterSpec`)
- `shutdownAfterJobFinishes`: Boolean — must be `true` for Kueue
- `jobId`: Optional — auto-generated if omitted
- `submitterPodTemplate`: Optional pod template for the job submitter

**RayService Spec Structure:**
- `serveConfigV2`: YAML string with Ray Serve deployment config
- `rayClusterConfig`: Cluster spec for the service's backing cluster
- `serviceUnhealthySecondThreshold`: Timeout for unhealthy service detection
- `deploymentUnhealthySecondThreshold`: Per-deployment unhealthy timeout

**Status Conditions (Beta, v1.3+):**
- `RayClusterProvisioned`, `RayClusterReplicaFailure`, `HeadPodReady`
- Condition status: `True`, `False`, `Unknown`
- Access via `status.conditions[]`

**CRD Detection:**
```python
from kubernetes import client
api_ext = client.ApiextensionsV1Api()
try:
    api_ext.read_custom_resource_definition("rayclusters.ray.io")
    kuberay_installed = True
except client.ApiException as e:
    if e.status == 404:
        kuberay_installed = False
```

### Alternatives Considered
- `v1alpha1` API: Deprecated, no longer maintained
- Direct Pod management: Bypasses operator benefits (reconciliation, autoscaling)

---

## 2. Ray Dashboard REST API

### Decision
Use the Ray Dashboard Jobs API (stable since Ray 2.2) for job submission to existing clusters. Use API token authentication when available (Ray 2.52+).

### Rationale
The Jobs API is the recommended way to submit jobs to running Ray clusters without using `ray.init()`. It provides a clean REST interface for job CRUD, log streaming, and package upload.

### Key Findings

**Base URL**: `http://<dashboard-host>:<port>` (default port 8265)

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/jobs/` | Submit a new job |
| GET | `/api/jobs/` | List all jobs |
| GET | `/api/jobs/{job_id}` | Get job details |
| DELETE | `/api/jobs/{job_id}` | Stop a job |
| GET | `/api/jobs/{job_id}/logs` | Get job logs |
| GET | `/api/jobs/{job_id}/logs/tail` | Stream logs (SSE) |
| PUT | `/api/packages/{uri}` | Upload runtime_env package |
| GET | `/api/version` | Get Ray version info |

**Job Submission Payload:**
```json
{
  "entrypoint": "python train.py",
  "runtime_env": {
    "pip": ["torch", "transformers"],
    "working_dir": "./src",
    "env_vars": {"KEY": "value"}
  },
  "entrypoint_num_cpus": 1,
  "entrypoint_num_gpus": 0,
  "entrypoint_memory": 0,
  "entrypoint_resources": {},
  "metadata": {"job_submission_id": "custom-id"}
}
```

**JobStatus Enum:**
`PENDING` | `RUNNING` | `STOPPED` | `SUCCEEDED` | `FAILED`

**Log Streaming:**
- `GET /api/jobs/{job_id}/logs/tail` returns Server-Sent Events (SSE)
- Content-Type: `text/event-stream`

**Authentication (Ray 2.52+):**
- Token-based: `Authorization: Bearer <token>`
- Configure via `RAY_DASHBOARD_API_TOKEN` env var on the cluster

### Alternatives Considered
- Ray Client protocol (`ray://`): Requires port 10001, less stable for production use
- kubectl exec + ray job submit CLI: Requires kubectl, not programmatic

---

## 3. kube-authkit

### Decision
Use `kube-authkit` (PyPI: `kube-authkit`, v0.4.0 Alpha) for all Kubernetes authentication. The SDK delegates auth entirely to kube-authkit.

### Rationale
kube-authkit provides a unified API for multiple auth strategies (kubeconfig, in-cluster, OIDC, OpenShift OAuth) and returns a standard `kubernetes.client.ApiClient`. This aligns with the constitution's principle of configuring auth once, not per-call.

### Key Findings

**Installation:** `pip install kube-authkit`

**Core API:**
```python
from kube_authkit import get_k8s_client, AuthConfig

# Auto-detect auth strategy
config = AuthConfig(method="auto")
api_client = get_k8s_client(config)

# Explicit kubeconfig
config = AuthConfig(method="kubeconfig", kubeconfig_path="~/.kube/config", context="my-context")
api_client = get_k8s_client(config)

# In-cluster (service account)
config = AuthConfig(method="incluster")
api_client = get_k8s_client(config)

# OpenShift OAuth
config = AuthConfig(method="openshift", server="https://api.cluster.example.com:6443", token="sha256~...")
api_client = get_k8s_client(config)
```

**Return Type:** `kubernetes.client.ApiClient` — standard client, usable with all `kubernetes` client APIs (`CoreV1Api`, `CustomObjectsApi`, etc.)

**Auth Strategies:**

| Strategy | AuthConfig method | Use Case |
|----------|-------------------|----------|
| Auto | `"auto"` | Tries kubeconfig, then in-cluster |
| Kubeconfig | `"kubeconfig"` | Local development |
| In-cluster | `"incluster"` | Running inside K8s pod |
| OIDC | `"oidc"` | Enterprise SSO |
| OpenShift | `"openshift"` | OpenShift OAuth token |

**Namespace Resolution:**
kube-authkit does not provide namespace resolution. The SDK must read the default namespace from the kubeconfig context via the `kubernetes` client library.

### Alternatives Considered
- Direct `kubernetes.config.load_kube_config()`: No unified strategy pattern, no OpenShift OAuth
- `openshift-client`: Too OpenShift-specific, adds heavy dependency
- Custom auth layer: Violates YAGNI, duplicates kube-authkit

---

## 4. OpenShift Routes

### Decision
Use the standard `kubernetes` Python client's `CustomObjectsApi` to interact with OpenShift Routes (`route.openshift.io/v1`). No additional OpenShift-specific Python dependency required.

### Rationale
Using `CustomObjectsApi` avoids adding `openshift` as a dependency. Routes are just custom resources with a well-known schema. The SDK only needs to read existing Routes (for dashboard URL detection) and optionally create Routes for RayService endpoints.

### Key Findings

**OpenShift Detection:**
```python
from kubernetes import client
api = client.ApisApi(api_client)
api_groups = api.get_api_versions()
openshift_groups = {"route.openshift.io", "config.openshift.io"}
is_openshift = openshift_groups.issubset({g.name for g in api_groups.groups})
```

Check for multiple API groups (not just one) to avoid false positives.

**Route CRUD via CustomObjectsApi:**
```python
custom_api = client.CustomObjectsApi(api_client)

# Read Route for dashboard URL
route = custom_api.get_namespaced_custom_object(
    group="route.openshift.io", version="v1",
    namespace=ns, plural="routes", name=route_name
)
dashboard_url = f"https://{route['spec']['host']}"
```

**Route Spec (key fields):**
- `spec.host`: External hostname (auto-generated on OpenShift as `<name>-<ns>.apps.<domain>`)
- `spec.to.kind`: `"Service"`, `spec.to.name`: target service name
- `spec.port.targetPort`: Backend port
- `spec.tls.termination`: `edge` | `passthrough` | `reencrypt`

**Key difference from Ingress:**
On OpenShift, Ingress objects are auto-converted to Routes. The SDK should check for Routes first (more specific), then Ingress as fallback.

### Alternatives Considered
- `openshift` Python package (DynamicClient): Adds heavy dependency
- `openshift-python-wrapper`: Another dependency to manage
- Kubernetes Ingress only: Would miss Routes on OpenShift

---

## 5. Kueue Integration

### Decision
Support Kueue integration via labels on KubeRay CRDs. Use API discovery to detect Kueue availability. API group: `kueue.x-k8s.io`, current version `v1beta2`.

### Rationale
Kueue has native built-in support for KubeRay resources (RayJob, RayCluster, RayService). Integration requires only adding labels to CRD metadata — no Kueue-specific API calls needed from the SDK.

### Key Findings

**Queue Assignment (single label):**
```yaml
metadata:
  labels:
    kueue.x-k8s.io/queue-name: <local-queue-name>
```

**Priority (optional label):**
```yaml
metadata:
  labels:
    kueue.x-k8s.io/priority-class: <priority-class-name>
```

**Kueue Detection:**
```python
api = client.ApisApi(api_client)
api_groups = api.get_api_versions()
kueue_installed = any(g.name == "kueue.x-k8s.io" for g in api_groups.groups)
```

**Constraints for Kueue-managed RayJobs:**
- `spec.shutdownAfterJobFinishes` must be `true`
- Cannot use `clusterSelector` (must create inline cluster)
- Maximum 7 worker groups (8 PodSet limit minus head group)

**Listing Available Queues:**
```python
custom_api = client.CustomObjectsApi(api_client)
queues = custom_api.list_namespaced_custom_object(
    group="kueue.x-k8s.io", version="v1beta2",
    namespace=ns, plural="localqueues"
)
```

### Alternatives Considered
- Volcano scheduler: Less K8s-native, not integrated with KubeRay
- Custom scheduling: Violates YAGNI
- No queueing support: Would miss a key OpenShift AI workflow

---

## 6. OpenShift AI Hardware Profiles

### Decision
Support hardware profiles via the `infrastructure.opendatahub.io/v1` CRD. Resolve HardwareProfile CRs to concrete resource requests, node selectors, and tolerations at cluster/job creation time.

### Rationale
Hardware profiles are the standard way to configure GPU and accelerator resources in OpenShift AI / Open Data Hub environments. They encapsulate resource limits, node scheduling, and optional Kueue queue assignment into a single named profile.

### Key Findings

**CRD Details:**
- API Group: `infrastructure.opendatahub.io`
- Version: `v1`
- Kind: `HardwareProfile`
- Scope: Namespaced

**HardwareProfile Structure:**
```yaml
spec:
  identifiers:
    - displayName: CPU
      identifier: cpu
      resourceType: CPU          # CPU | Memory | Accelerator
      defaultCount: 4
      minCount: 2
      maxCount: 8
    - displayName: NVIDIA GPU
      identifier: nvidia.com/gpu
      resourceType: Accelerator
      defaultCount: 1
      minCount: 1
      maxCount: 4
  scheduling:
    schedulingType: Node         # "Node" or "Queue"
    node:
      nodeSelector:
        nvidia.com/gpu.present: "true"
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
```

**Queue-based scheduling (mutually exclusive with Node):**
```yaml
scheduling:
  schedulingType: Queue
  kueue:
    localQueueName: gpu-queue
    priorityClass: high-priority
```

**SDK Resolution Flow:**
1. User passes `hardware_profile="gpu-small"` to `create_cluster()`
2. SDK reads HardwareProfile CR from the profile's namespace
3. Extracts `defaultCount` for each identifier → resource requests/limits
4. Extracts `scheduling.node.nodeSelector` and `tolerations` → pod spec
5. If `scheduling.schedulingType == "Queue"`, applies Kueue labels instead

**Profile Namespace:**
Profiles live in a specific namespace (commonly `redhat-ods-applications` or `opendatahub`). The SDK needs a configurable profile namespace.

**Detection:**
Check for the `infrastructure.opendatahub.io` API group or the HardwareProfile CRD directly.

### Alternatives Considered
- Accelerator Profiles: Deprecated in OpenShift AI 2.19
- Manual resource specification: Always available as fallback, but profiles provide curated configs
- ConfigMap-based profiles: Not the upstream approach

---

## Sources

### KubeRay
- [KubeRay GitHub](https://github.com/ray-project/kuberay)
- [KubeRay API Reference](https://docs.ray.io/en/latest/cluster/kubernetes/getting-started/raycluster-quick-start.html)
- [KubeRay v1.5.1 Release](https://github.com/ray-project/kuberay/releases/tag/v1.5.1)

### Ray Dashboard API
- [Ray Jobs REST API](https://docs.ray.io/en/latest/cluster/running-applications/job-submission/rest.html)
- [Ray Dashboard API Token Auth](https://docs.ray.io/en/latest/cluster/kubernetes/user-guides/rayservice.html)

### kube-authkit
- [PyPI: kube-authkit](https://pypi.org/project/kube-authkit/)

### OpenShift Routes
- [Route API Reference](https://docs.okd.io/4.11/rest_api/network_apis/route-route-openshift-io-v1.html)
- [Kubernetes Ingress vs OpenShift Route](https://www.redhat.com/en/blog/kubernetes-ingress-vs-openshift-route)

### Kueue
- [Kueue Overview](https://kueue.sigs.k8s.io/docs/overview/)
- [Run RayJobs with Kueue](https://kueue.sigs.k8s.io/docs/tasks/run/rayjobs/)
- [Run RayClusters with Kueue](https://kueue.sigs.k8s.io/docs/tasks/run/rayclusters/)

### Hardware Profiles
- [Working with Hardware Profiles](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_cloud_service/1/html/working_with_accelerators/working-with-hardware-profiles_accelerators)
- [OpenDataHub Operator](https://github.com/opendatahub-io/opendatahub-operator)
