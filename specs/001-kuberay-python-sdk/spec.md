# Feature Specification: KubeRay Python SDK

**Feature Branch**: `001-kuberay-python-sdk`
**Created**: 2026-02-23
**Status**: Draft
**Input**: User description: "Build a robust, friendly, UX optimized SDK for KubeRay to enable users to launch Ray clusters, Ray jobs CRDs, and submit AI/ML workloads to existing Ray clusters via Ray Dashboard. Seamless integration with vanilla Kubernetes and OpenShift clusters."

## Clarifications

### Session 2026-02-23

- Q: Should the SDK API be sync-only, async-only, or both? → A: Sync-first with optional async. The primary API is synchronous (blocking), suitable for Jupyter notebooks and scripts. A separate async client is provided for advanced users who need concurrent operations.
- Q: Can a single SDK client operate across multiple namespaces? → A: Default namespace with per-call override. The client is initialized with a default namespace but every operation accepts an optional `namespace` parameter to target a different namespace.
- Q: How do users specify the Ray container image/version? → A: SDK defaults to a sensible Ray image (latest stable). Users can override via optional `ray_version` or `image` parameter on cluster/job/service creation.
- Q: What is explicitly out of scope? → A: KubeRay operator install/upgrade, Ray Tune API wrapping, multi-cluster federation, standalone CLI tool, and Ray client API wrapping are all out of scope.
- Q: Should the SDK auto-retry transient failures? → A: Yes. Auto-retry transient errors (5xx, timeouts, API throttling) with exponential backoff. Create operations are idempotent — return existing resource if an identical one exists. Users can configure retry behavior.
- Q: How should head node and heterogeneous worker groups be configured? → A: Simple defaults with optional advanced config. Flat parameters (workers, gpus_per_worker) for the common single-group case. Optional `worker_groups` list for heterogeneous clusters. Head node auto-configured (CPU-only default) with optional override.
- Q: What storage backends does artifact download support? → A: Ray Dashboard API artifacts and PVC-mounted data. Cloud object storage (S3, GCS, Azure Blob) is out of scope — users access those directly via their own SDKs.
- Q: How does the SDK provide access to the Ray Dashboard? → A: Auto port-forward with Route/Ingress detection. The SDK first checks for an OpenShift Route or Kubernetes Ingress; if found, uses that URL directly. Otherwise, auto-establishes a port-forward for internal Dashboard operations and exposes the local URL to users.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and Manage Ray Clusters (Priority: P1)

A data scientist wants to create a Ray cluster to run distributed
training jobs. They authenticate once, specify the cluster size and
resource requirements in plain terms (e.g., number of workers, GPU
count, memory), and the SDK provisions the cluster. They can list
their clusters, check status, scale up/down, and delete clusters
when done. They never interact with Kubernetes manifests, CRDs, or
kubectl.

**Why this priority**: Ray cluster lifecycle is the foundational
capability. Without clusters, no other feature (jobs, serving,
logs) is possible. This is the MVP.

**Independent Test**: Can be fully tested by creating a cluster,
verifying it reaches a ready state, scaling it, and deleting it.
Delivers the core value of launching Ray infrastructure without
Kubernetes knowledge.

**Acceptance Scenarios**:

1. **Given** a user has valid credentials configured via kube-authkit,
   **When** they create a cluster with `name="my-cluster"`,
   `workers=4`, `gpus_per_worker=1`,
   **Then** a RayCluster CR is created in their configured namespace
   and the SDK returns a cluster handle with a status indicating
   provisioning.

2. **Given** a running cluster,
   **When** the user calls `cluster.status()`,
   **Then** the SDK returns a human-readable status object showing
   head node readiness, worker count, and overall health — not raw
   Kubernetes conditions.

3. **Given** a running cluster,
   **When** the user calls `cluster.scale(workers=8)`,
   **Then** the worker count is updated and the SDK reports progress
   until the new workers are ready.

4. **Given** a running cluster,
   **When** the user calls `cluster.delete()`,
   **Then** the RayCluster CR and associated resources are removed,
   and the SDK confirms deletion.

5. **Given** a user lists clusters,
   **When** they call `list_clusters()`,
   **Then** they see all Ray clusters in their namespace with name,
   status, age, and worker count.

6. **Given** a Kubernetes-aware user,
   **When** they create a cluster with additional `labels`,
   `annotations`, `tolerations`, or `node_selector` parameters,
   **Then** those are applied to the underlying RayCluster CR.

---

### User Story 2 - Submit and Manage Ray Jobs (Priority: P2)

An ML engineer wants to submit a training script as a Ray job,
either by creating a RayJob CR (which provisions its own cluster)
or by submitting work to an existing Ray cluster via the Ray
Dashboard API. They can monitor job progress, view logs in
real-time, and retrieve job results.

**Why this priority**: Job submission is the primary way users run
workloads. Once clusters exist (P1), jobs are the next essential
capability.

**Independent Test**: Can be tested by submitting a simple Ray
script, watching it complete, and retrieving its logs and exit
status.

**Acceptance Scenarios**:

1. **Given** no existing cluster,
   **When** a user creates a RayJob with an entrypoint script and
   resource requirements,
   **Then** the SDK creates a RayJob CR that provisions a
   disposable cluster, runs the job, and tears down the cluster
   on completion.

2. **Given** an existing running cluster,
   **When** a user submits a job via `cluster.submit_job(entrypoint="python train.py", runtime_env={...})`,
   **Then** the job is submitted through the Ray Dashboard API and
   the SDK returns a job handle for monitoring.

3. **Given** a running job,
   **When** the user calls `job.logs(stream=True)`,
   **Then** logs are streamed to the caller in real-time.

4. **Given** a running job,
   **When** the user calls `job.status()`,
   **Then** a human-readable status is returned including progress
   information, duration, and any error messages.

5. **Given** a completed or failed job,
   **When** the user calls `job.logs()`,
   **Then** the full log output is returned as a string.

6. **Given** a user lists jobs,
   **When** they call `list_jobs()` or `cluster.list_jobs()`,
   **Then** they see all RayJob CRs in their namespace or all
   dashboard-submitted jobs on that cluster, with name, status,
   and submission time.

---

### User Story 3 - Stream Logs and Download Artifacts (Priority: P3)

A data scientist wants to monitor training progress by streaming
logs from a running job and download model checkpoints or other
output artifacts when training completes.

**Why this priority**: Observability is critical for long-running
ML workloads. Users need to verify training is progressing and
retrieve results without SSH-ing into pods or using kubectl.

**Independent Test**: Can be tested by running a job that produces
logs and artifacts, streaming logs during execution, and
downloading artifacts after completion.

**Acceptance Scenarios**:

1. **Given** a running Ray job,
   **When** the user calls `job.logs(stream=True)`,
   **Then** log lines are yielded in real-time as an iterator.

2. **Given** a running Ray job,
   **When** the user calls `job.logs(stream=True, follow=True)`,
   **Then** the stream blocks and continues yielding new log lines
   until the job completes.

3. **Given** a completed job that wrote artifacts to a mounted PVC
   or the Ray Dashboard artifact store,
   **When** the user calls `job.download_artifacts(destination="./output")`,
   **Then** artifacts are downloaded to the specified local path
   via the Dashboard API or by copying from the PVC.

4. **Given** a running or completed job,
   **When** the user calls `job.logs(tail=100)`,
   **Then** only the last 100 lines of logs are returned.

---

### User Story 4 - Ray Serve: Deploy and Manage Serving Applications (Priority: P4)

An AI engineer wants to deploy a trained model or LLM as a
scalable serving endpoint using Ray Serve. They configure the
model, autoscaling parameters, and resource requirements, and
the SDK creates a RayService CR. They can update deployments,
check endpoint health, and tear them down.

**Why this priority**: Model serving is a common post-training
workflow. RayService CRDs are a key part of the KubeRay ecosystem.

**Independent Test**: Can be tested by deploying a simple Ray
Serve application, verifying the endpoint is reachable, and
deleting the service.

**Acceptance Scenarios**:

1. **Given** a user has a Ray Serve application config,
   **When** they call `create_service(name="my-llm", import_path="serve_app:deployment", num_replicas=2)`,
   **Then** a RayService CR is created and the SDK returns a
   service handle.

2. **Given** a running service,
   **When** the user calls `service.status()`,
   **Then** a human-readable status is returned showing endpoint
   URL, replica count, health, and serving status.

3. **Given** a running service,
   **When** the user calls `service.update(num_replicas=4)`,
   **Then** the service scales and the SDK reports progress.

4. **Given** a running service,
   **When** the user calls `service.delete()`,
   **Then** the RayService CR is removed.

---

### User Story 5 - Storage and Runtime Environment Configuration (Priority: P5)

A user wants to attach persistent storage volumes for data
and model checkpoints and configure the Python runtime
environment (packages, environment variables, working
directory) for their Ray workloads.

**Why this priority**: Production ML workloads require data
persistence and reproducible environments. This is needed
before users run serious training jobs.

**Independent Test**: Can be tested by creating a cluster or
job with storage and runtime env configurations, verifying
the job can read/write to the volume and has the correct
packages installed.

**Acceptance Scenarios**:

1. **Given** a user creating a cluster or job,
   **When** they specify `storage={"data": {"size": "100Gi", "mount_path": "/data"}}`,
   **Then** a PVC is created and mounted at the specified path
   on all Ray nodes.

2. **Given** a user submitting a job,
   **When** they specify `runtime_env={"pip": ["torch", "transformers"], "env_vars": {"WANDB_API_KEY": "..."}, "working_dir": "./src"}`,
   **Then** the runtime environment is configured on the Ray
   cluster and the job has access to the specified packages,
   variables, and files.

3. **Given** a user creating a cluster with existing PVC names,
   **When** they specify `storage={"models": {"existing_claim": "my-pvc", "mount_path": "/models"}}`,
   **Then** the existing PVC is mounted without creating a new one.

---

### User Story 6 - Dashboard Metrics and Job Monitoring (Priority: P6)

A user wants to monitor cluster resource utilization, job
progress, and retrieve metrics from the Ray Dashboard without
leaving their Python environment.

**Why this priority**: Monitoring is essential for debugging
and optimizing workloads but is not required for basic
functionality.

**Independent Test**: Can be tested by running a job on a
cluster and fetching dashboard metrics from the SDK.

**Acceptance Scenarios**:

1. **Given** a running cluster,
   **When** the user calls `cluster.dashboard_url()`,
   **Then** the SDK checks for an OpenShift Route or Ingress
   first; if found, returns that URL. Otherwise, auto-establishes
   a port-forward and returns the local URL. The user can open
   the Dashboard in a browser without manual port-forwarding.

2. **Given** a running cluster,
   **When** the user calls `cluster.metrics()`,
   **Then** the SDK returns cluster-level metrics (CPU, GPU, memory
   utilization, active tasks, available resources).

3. **Given** a running job,
   **When** the user calls `job.progress()`,
   **Then** the SDK returns job progress information from the
   Ray Dashboard API.

---

### User Story 7 - OpenShift Integration (Priority: P7)

A user on an OpenShift cluster wants to use OpenShift-specific
features like hardware profiles (GPU types, accelerator
configurations), Kueue-based queuing, and OpenShift Routes for
service exposure.

**Why this priority**: OpenShift is a key deployment target.
Integration with OpenShift-specific features differentiates this
SDK from plain kubectl usage. However, the SDK must work on
vanilla Kubernetes first.

**Independent Test**: Can be tested on an OpenShift cluster by
creating a cluster with a hardware profile and verifying correct
resource configuration, or by submitting a job to a Kueue queue.

**Acceptance Scenarios**:

1. **Given** a user on an OpenShift cluster,
   **When** they create a cluster with `hardware_profile="gpu-large"`,
   **Then** the SDK resolves the profile to concrete resource
   requests/limits and node selectors from the OpenShift
   configuration.

2. **Given** a user on a cluster with Kueue installed,
   **When** they create a job with `queue="training-queue"`,
   **Then** the appropriate Kueue labels and annotations are
   applied to the RayJob CR.

3. **Given** a user on an OpenShift cluster deploying a RayService,
   **When** the service is created,
   **Then** an OpenShift Route is automatically created for the
   serving endpoint (unless explicitly disabled).

---

### User Story 8 - Experiment Tracking Integration (Priority: P8)

A data scientist wants their Ray training jobs to automatically
log metrics, parameters, and artifacts to an experiment tracking
system like MLflow.

**Why this priority**: Experiment tracking is important for
production ML workflows but is an integration rather than core
SDK functionality.

**Independent Test**: Can be tested by running a training job
with MLflow configuration and verifying that metrics appear in
the MLflow tracking server.

**Acceptance Scenarios**:

1. **Given** a user has an MLflow tracking server configured,
   **When** they submit a job with
   `experiment_tracking={"provider": "mlflow", "tracking_uri": "http://mlflow:5000", "experiment_name": "my-exp"}`,
   **Then** the runtime environment is configured with MLflow
   connection details and the job can log metrics and artifacts.

2. **Given** a user has experiment tracking configured at the
   cluster level,
   **When** they submit any job to that cluster,
   **Then** the experiment tracking configuration is inherited
   by the job without re-specifying it.

---

### User Story 9 - Ray Agentic Workloads (Priority: P9)

An AI engineer wants to deploy agentic AI workloads (autonomous
agents using LLMs, tool calling, multi-step reasoning) on Ray.
These workloads typically use Ray Serve for the agent endpoint
and Ray tasks/actors for parallel tool execution.

**Why this priority**: Agentic AI is an emerging use case. Support
is important for adoption but can build on top of existing
Ray Serve and Ray Job primitives.

**Independent Test**: Can be tested by deploying an agentic
application via Ray Serve and verifying it handles requests.

**Acceptance Scenarios**:

1. **Given** a user has an agentic Ray Serve application,
   **When** they deploy it using the SDK's service creation
   workflow with appropriate resource configuration (e.g., GPU
   for LLM inference, CPU workers for tool execution),
   **Then** the RayService CR is created with heterogeneous
   resource groups matching the agent architecture.

2. **Given** a deployed agentic service,
   **When** the user monitors it,
   **Then** they can see cluster-level resource utilization
   and job progress via the standard dashboard metrics
   (FR-028, FR-029). Per-component metrics (LLM latency,
   tool execution times) are visible through the Ray
   Dashboard UI directly.

---

### Edge Cases

- What happens when a user tries to create a cluster with a name
  that already exists in the namespace?
  If the existing cluster has an identical specification, the SDK
  MUST return a handle to the existing cluster (idempotent create).
  If the specification differs, the SDK MUST return a clear error:
  "Cluster 'X' already exists in namespace 'Y' with a different
  configuration."

- What happens when authentication credentials expire mid-operation?
  The SDK MUST surface a clear re-authentication message rather
  than a raw Kubernetes 401 error.

- What happens when a user requests more GPUs than available?
  The SDK MUST report the resource constraint clearly, e.g.,
  "Requested 8 GPUs but only 4 are available in namespace 'Y'."
  (best-effort; depends on cluster quota visibility).

- What happens when a cluster is deleted while a job is running?
  The SDK MUST warn the user and require explicit confirmation
  (e.g., `force=True`) before proceeding.

- What happens when the Ray Dashboard is unreachable?
  Operations that depend on the Dashboard (job submission to
  existing clusters, log streaming, metrics) MUST fail with a
  clear message. Cluster CRUD operations (which use CRDs) MUST
  continue to work.

- What happens on a cluster without KubeRay operator installed?
  The SDK MUST detect the absence of KubeRay CRDs and return a
  clear error message explaining the prerequisite.

- What happens when a user passes invalid runtime_env?
  The SDK MUST validate runtime_env structure locally before
  submitting and provide actionable error messages.

### Out of Scope

The following are explicitly **not** part of this SDK:

- **KubeRay operator installation or upgrade**: The SDK assumes
  the KubeRay operator is already installed. Operator lifecycle
  management belongs to cluster administrators and tools like
  Helm or OLM.
- **Ray Tune API wrapping**: The SDK manages infrastructure
  (clusters, jobs, services), not Ray-internal APIs like Tune
  for hyperparameter sweeps. Users call Ray Tune directly within
  their job code.
- **Multi-cluster federation**: The SDK operates against a single
  Kubernetes cluster at a time (as determined by the kubeconfig
  context). Cross-cluster orchestration is a separate concern.
- **Standalone CLI tool**: The SDK is a Python library. A CLI
  wrapper may be built on top of it as a separate project but
  is not part of this specification.
- **Ray client API wrapping**: The SDK does not wrap the Ray
  Client protocol (`ray.init("ray://...")`) for interactive
  development. It manages KubeRay CRDs and the Ray Dashboard
  REST API.

## Requirements *(mandatory)*

### Functional Requirements

**API Model**

- **FR-039**: SDK MUST provide a synchronous (blocking) API as the
  primary interface, suitable for Jupyter notebooks and scripts.
- **FR-040**: SDK MUST provide a separate async client for users
  who need concurrent operations (async/await).
- **FR-041**: Both sync and async clients MUST expose identical
  functionality and method signatures (except for async/await
  syntax).

**Authentication & Configuration**

- **FR-001**: SDK MUST authenticate to Kubernetes and OpenShift
  clusters using kube-authkit.
- **FR-002**: SDK MUST support namespace configuration at the
  client level, defaulting to the user's current kubeconfig
  namespace. Every operation MUST accept an optional `namespace`
  parameter to override the default for that call.
- **FR-003**: SDK MUST auto-detect whether it is running on
  vanilla Kubernetes or OpenShift and adjust behavior accordingly
  (e.g., Routes vs Ingress for service exposure).

**Ray Cluster Lifecycle**

- **FR-004**: SDK MUST support creating RayCluster CRs with
  user-friendly parameters (name, workers, CPUs, GPUs, memory)
  without requiring knowledge of CRD schema. The SDK MUST default
  to a sensible Ray container image (latest stable version).
  Users MAY override the image via an optional `ray_version` or
  `image` parameter.
- **FR-045**: SDK MUST auto-configure head node resources with
  sensible defaults (CPU-only, no GPU). Users MAY override head
  node resources via an optional `head` parameter.
- **FR-046**: SDK MUST support heterogeneous clusters via an
  optional `worker_groups` parameter that accepts a list of
  worker group configurations, each with independent resource
  profiles (CPUs, GPUs, memory, replicas). When `worker_groups`
  is provided, the flat `workers`/`gpus_per_worker` parameters
  MUST NOT be used (mutually exclusive).
- **FR-005**: SDK MUST support listing all RayClusters in the
  configured namespace.
- **FR-006**: SDK MUST support retrieving detailed status of a
  specific RayCluster in human-readable format.
- **FR-007**: SDK MUST support scaling a RayCluster's worker
  count up or down.
- **FR-008**: SDK MUST support deleting a RayCluster with
  safety checks (warn if jobs are running).
- **FR-009**: SDK MUST support waiting for a cluster to reach
  a ready state with a configurable timeout.

**Ray Job Lifecycle**

- **FR-010**: SDK MUST support creating RayJob CRs (disposable
  cluster jobs) with entrypoint, runtime_env, and resource
  configuration.
- **FR-011**: SDK MUST support submitting jobs to existing
  RayClusters via the Ray Dashboard API.
- **FR-012**: SDK MUST support listing jobs (both CRD-based and
  dashboard-submitted).
- **FR-013**: SDK MUST support retrieving job status in
  human-readable format.
- **FR-014**: SDK MUST support stopping/cancelling running jobs.
- **FR-015**: SDK MUST support waiting for a job to complete
  with a configurable timeout.

**Logs & Artifacts**

- **FR-016**: SDK MUST support retrieving full logs from a
  completed or running job.
- **FR-017**: SDK MUST support streaming logs from a running
  job in real-time.
- **FR-018**: SDK MUST support downloading artifacts via two
  mechanisms: (a) the Ray Dashboard job artifact API, and
  (b) copying files from PVCs mounted to the cluster. Cloud
  object storage (S3, GCS, Azure Blob) is out of scope for
  artifact download — users access those directly.
- **FR-019**: SDK MUST support tailing logs (last N lines).

**Ray Serve / Services**

- **FR-020**: SDK MUST support creating RayService CRs for
  deploying Ray Serve applications including LLM serving.
- **FR-021**: SDK MUST support retrieving service status and
  endpoint URLs.
- **FR-022**: SDK MUST support updating running services
  (scaling, config changes).
- **FR-023**: SDK MUST support deleting services.

**Storage & Runtime Environment**

- **FR-024**: SDK MUST support attaching new or existing PVCs
  to Ray clusters and jobs.
- **FR-025**: SDK MUST support configuring Ray runtime_env
  (pip packages, conda, env vars, working_dir, py_modules).
- **FR-026**: SDK MUST validate runtime_env and storage
  configuration locally before submitting to the cluster.

**Monitoring & Metrics**

- **FR-027**: SDK MUST support retrieving the Ray Dashboard URL
  for a given cluster. The SDK MUST first check for an existing
  OpenShift Route or Kubernetes Ingress and use that URL if
  available. If neither exists, the SDK MUST automatically
  establish a port-forward and return the local URL. All
  Dashboard-dependent operations (job submission, log streaming,
  metrics) MUST use this mechanism transparently.
- **FR-028**: SDK MUST support fetching cluster-level resource
  metrics from the Ray Dashboard.
- **FR-029**: SDK MUST support fetching job progress and
  task-level metrics.

**OpenShift Integration**

- **FR-030**: SDK MUST support hardware profiles for GPU and
  accelerator configuration on OpenShift.
- **FR-031**: SDK MUST support Kueue integration via queue
  assignment on jobs and clusters.
- **FR-032**: SDK MUST support OpenShift Routes for service
  exposure.

**Experiment Tracking**

- **FR-033**: SDK MUST support configuring experiment tracking
  (MLflow) at the cluster or job level by injecting tracking
  configuration into the runtime environment.

**Advanced / Kubernetes-Aware Users**

- **FR-034**: SDK MUST support passing arbitrary labels and
  annotations to all CRDs.
- **FR-035**: SDK MUST support specifying tolerations and
  node selectors for workload placement as first-class
  parameters. Node affinity MUST be supported via
  `raw_overrides` (FR-036) per Principle V (YAGNI).
- **FR-036**: SDK MUST support passing raw overrides to the
  underlying CRD spec for use cases not covered by the
  high-level API.

**Error Handling**

- **FR-037**: SDK MUST translate Kubernetes API errors into
  user-friendly messages in Ray/ML domain terms.
- **FR-038**: SDK MUST detect missing KubeRay CRDs and report
  a clear prerequisite error.

**Reliability & Retry Behavior**

- **FR-042**: SDK MUST automatically retry transient errors
  (5xx responses, network timeouts, API server throttling) with
  exponential backoff.
- **FR-043**: Create operations (clusters, jobs, services) MUST
  be idempotent — if a resource with an identical specification
  already exists, the SDK MUST return a handle to the existing
  resource instead of raising a duplicate error.
- **FR-044**: Retry behavior MUST be configurable (max retries,
  backoff factor, timeout) at the client level.

### Key Entities

- **RayCluster**: A logical Ray cluster. Attributes: name,
  namespace, head node resources (auto-defaulted, CPU-only),
  worker groups (one or more, each with CPUs, GPUs, memory,
  replica count), status, age, labels, annotations. Simple
  creation uses flat params (workers, gpus_per_worker);
  advanced creation uses explicit worker_groups list. Maps to
  a KubeRay RayCluster CR.

- **RayJob**: A batch job that runs on Ray. Two modes:
  (a) CRD-based — creates its own disposable cluster via
  RayJob CR; (b) dashboard-submitted — runs on an existing
  cluster via the Ray Dashboard API. Attributes: name, status,
  entrypoint, runtime_env, submission time, duration, logs.

- **RayService**: A long-running serving deployment. Attributes:
  name, import path, replicas, autoscaling config, endpoint URL,
  status. Maps to a KubeRay RayService CR.

- **Storage**: A volume attachment. Attributes: name, size
  (or existing claim name), mount path, access mode.

- **RuntimeEnv**: Ray's runtime environment configuration.
  Attributes: pip packages, conda env, env vars, working dir,
  py_modules.

- **SDKConfig**: SDK-level configuration. Attributes:
  namespace, auth context (via kube-authkit), retry behavior,
  hardware profile namespace.

### Assumptions

- kube-authkit provides a stable Python API for obtaining
  authenticated Kubernetes clients. The SDK delegates all
  authentication concerns to kube-authkit.
- The KubeRay operator (v1.1+) is installed on the target
  cluster. The SDK does not install or manage the operator.
- Ray Dashboard is accessible from the SDK's runtime
  environment (direct, port-forward, or via OpenShift Route).
- MLflow integration is handled by injecting configuration into
  the Ray runtime environment; the SDK does not implement an
  MLflow client.
- Hardware profiles on OpenShift are discoverable via a known
  API or configuration; the exact mechanism depends on the
  OpenShift version and configuration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with no Kubernetes experience can create a
  Ray cluster, submit a job, and retrieve logs in under 5
  minutes using only the SDK's getting-started guide.

- **SC-002**: Creating a cluster requires no more than 3
  mandatory parameters (name, workers, and resource size or
  profile).

- **SC-003**: 100% of error messages surfaced to users are in
  Ray/ML domain terms, not raw Kubernetes API errors.

- **SC-004**: All CRUD operations on clusters, jobs, and services
  are achievable with a single method call each.

- **SC-005**: SDK works on both vanilla Kubernetes and OpenShift
  without requiring users to change their code (platform
  detection is automatic).

- **SC-006**: Advanced Kubernetes configuration (labels,
  annotations, tolerations, node selectors) is accessible
  without breaking the simple default interface.

- **SC-007**: Log streaming begins within 2 seconds of calling
  the stream method on a running job.

- **SC-008**: SDK detects a missing KubeRay operator and reports
  a clear error within the first API call.

- **SC-009**: 90% of users who complete the getting-started guide
  rate the SDK as "easy to use" or better.
