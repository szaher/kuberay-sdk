# Tasks: KubeRay Python SDK

**Input**: Design documents from `/specs/001-kuberay-python-sdk/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included per Constitution Principle IV (Test-First, NON-NEGOTIABLE). Contract tests verify CRD schema compliance, unit tests cover public API methods.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Package**: `src/kuberay_sdk/` (src-based layout per PyPA)
- **Tests**: `tests/unit/`, `tests/contract/`, `tests/integration/`
- **Config**: `pyproject.toml` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, tooling

- [x] T001 Create project directory structure per plan.md: `src/kuberay_sdk/`, `src/kuberay_sdk/models/`, `src/kuberay_sdk/services/`, `src/kuberay_sdk/platform/`, `tests/unit/`, `tests/contract/`, `tests/integration/`
- [x] T002 Create pyproject.toml with project metadata (name=kuberay-sdk, python>=3.9), runtime deps (kubernetes, kube-authkit, httpx, pydantic), dev deps (pytest, pytest-asyncio, pytest-httpx, ruff, mypy), and build config
- [x] T003 [P] Configure ruff (linting/formatting) and mypy (type checking) in pyproject.toml per constitution Development Workflow section
- [x] T004 [P] Create tests/conftest.py with shared fixtures: mock kubernetes.client.ApiClient, mock CustomObjectsApi, mock httpx responses for Dashboard API

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Implement error hierarchy in src/kuberay_sdk/errors.py: KubeRayError base, ClusterError, ClusterNotFoundError, ClusterAlreadyExistsError, JobError, JobNotFoundError, ServiceError, DashboardUnreachableError, KubeRayOperatorNotFoundError, AuthenticationError, ValidationError, ResourceConflictError, TimeoutError. Include K8s-to-domain error translation helper (FR-037, FR-038)
- [x] T006 [P] Implement shared types in src/kuberay_sdk/models/common.py: ResourceRequirements, ClusterState/JobState/JobMode/ServiceState enums, Condition dataclass
- [x] T007 [P] Implement StorageVolume pydantic model in src/kuberay_sdk/models/storage.py with validation: mutually exclusive size/existing_claim, absolute mount_path, valid access_mode
- [x] T008 [P] Implement RuntimeEnv pydantic model in src/kuberay_sdk/models/runtime_env.py with validation: mutually exclusive pip/conda, valid pip requirement strings
- [x] T009 Implement retry logic in src/kuberay_sdk/retry.py: exponential backoff decorator, configurable max_attempts/backoff_factor/timeout, transient error detection (5xx, timeouts, throttling), idempotent create helper (FR-042, FR-043, FR-044)
- [x] T010 Implement SDKConfig pydantic model and namespace resolution in src/kuberay_sdk/config.py: auth delegation to kube-authkit (get_k8s_client), default namespace from kubeconfig context, KubeRay CRD presence check (FR-001, FR-002, FR-038)
- [x] T011 Create KubeRayClient skeleton in src/kuberay_sdk/client.py: constructor accepting SDKConfig, K8s client initialization, CustomObjectsApi setup, placeholder methods for cluster/job/service operations (FR-039)
- [x] T012 [P] Create src/kuberay_sdk/models/__init__.py re-exporting all model classes; create src/kuberay_sdk/__init__.py exporting KubeRayClient, AsyncKubeRayClient, and all public models
- [x] T013 [P] Create src/kuberay_sdk/services/__init__.py and src/kuberay_sdk/platform/__init__.py as empty init files

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Create and Manage Ray Clusters (Priority: P1) MVP

**Goal**: Users can create, list, get status, scale, and delete RayClusters using flat parameters (name, workers, gpus_per_worker) without K8s knowledge. Advanced users can pass worker_groups, labels, tolerations, node_selector, raw_overrides.

**Independent Test**: Create a cluster with `name="test", workers=2`, verify CRD is created correctly, call status(), scale(workers=4), then delete(). Verify all operations produce correct CustomObjectsApi calls.

### Tests for User Story 1

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T014 [P] [US1] Contract test: verify SDK-generated RayCluster CRD dict matches RAYCLUSTER_SCHEMA (apiVersion, kind, headGroupSpec, workerGroupSpecs structure, resource requests/limits, image, rayVersion) in tests/contract/test_cluster_crd.py
- [x] T015 [P] [US1] Unit test for RayCluster, ClusterStatus, WorkerGroup, HeadNodeConfig model validation (valid creation, mutual exclusivity of workers vs worker_groups, K8s name validation, defaults) in tests/unit/test_models.py
- [x] T016 [P] [US1] Unit test for ClusterService: create (simple + advanced), get, list, scale, delete, wait_until_ready using mocked CustomObjectsApi in tests/unit/test_cluster_service.py
- [x] T017 [P] [US1] Unit test for idempotent cluster create (existing identical → return handle, existing different → ResourceConflictError) in tests/unit/test_cluster_service.py

### Implementation for User Story 1

- [x] T018 [P] [US1] Implement RayCluster, ClusterStatus, WorkerGroup, HeadNodeConfig pydantic models in src/kuberay_sdk/models/cluster.py per data-model.md: field types, defaults, validation rules (K8s name regex, workers>=1, mutual exclusivity), to_crd_dict() method generating ray.io/v1 RayCluster manifest
- [x] T019 [US1] Implement ClusterService in src/kuberay_sdk/services/cluster_service.py: create_cluster (build CRD dict, apply via CustomObjectsApi), get_cluster, list_clusters, scale_cluster (patch workerGroupSpecs.replicas), delete_cluster (with running-job safety check), wait_until_ready (poll status.conditions for HeadPodReady) (FR-004 through FR-009, FR-045, FR-046)
- [x] T020 [US1] Implement idempotent create in ClusterService: on 409 Conflict, fetch existing, compare spec, return handle if identical or raise ClusterAlreadyExistsError if different (FR-043)
- [x] T021 [US1] Implement ClusterHandle class in src/kuberay_sdk/client.py: status() → ClusterStatus, scale(workers) → patch, delete(force) → safety check + delete, wait_until_ready(timeout) → poll with timeout
- [x] T022 [US1] Wire create_cluster, get_cluster, list_clusters into KubeRayClient in src/kuberay_sdk/client.py with namespace resolution (client default + per-call override) and retry decorator
- [x] T023 [US1] Add advanced K8s params support: labels, annotations, tolerations, node_selector applied to CRD metadata and pod templates; raw_overrides deep-merged into final CRD dict (FR-034, FR-035, FR-036)

**Checkpoint**: User Story 1 fully functional. `client.create_cluster("test", workers=4, gpus_per_worker=1)` creates a valid RayCluster CR. CRUD + scale + wait work end-to-end (mocked).

---

## Phase 4: User Story 2 — Submit and Manage Ray Jobs (Priority: P2)

**Goal**: Users can create RayJob CRs (disposable cluster) or submit jobs to existing clusters via Dashboard API. They can list, get status, stop, and wait for jobs.

**Independent Test**: Create a RayJob CRD with entrypoint and verify CRD structure. Submit a job via mocked Dashboard API and verify REST payload. Retrieve job status and logs.

**Dependencies**: US1 (ClusterHandle.submit_job needs cluster_service for Dashboard URL)

### Tests for User Story 2

- [x] T024 [P] [US2] Contract test: verify SDK-generated RayJob CRD dict matches RAYJOB_SCHEMA (entrypoint, runtimeEnvYAML, shutdownAfterJobFinishes, rayClusterSpec) in tests/contract/test_job_crd.py
- [x] T025 [P] [US2] Contract test: verify Dashboard job submission payload matches DASHBOARD_JOB_SUBMISSION_PAYLOAD format in tests/contract/test_dashboard_api.py
- [x] T026 [P] [US2] Unit test for RayJob, JobStatus model validation in tests/unit/test_models.py
- [x] T027 [P] [US2] Unit test for DashboardClient (submit, list, get, stop, logs) using pytest-httpx mocks in tests/unit/test_dashboard.py
- [x] T028 [P] [US2] Unit test for JobService (CRD mode + Dashboard mode) using mocked CustomObjectsApi and DashboardClient in tests/unit/test_job_service.py

### Implementation for User Story 2

- [x] T029 [P] [US2] Implement RayJob, JobStatus pydantic models in src/kuberay_sdk/models/job.py: field types, defaults, validation (entrypoint non-empty, cluster_name vs workers mutual exclusivity), to_crd_dict() for CRD mode
- [x] T030 [US2] Implement DashboardClient in src/kuberay_sdk/services/dashboard.py: httpx-based client for POST /api/jobs/ (submit), GET /api/jobs/ (list), GET /api/jobs/{id} (status), POST /api/jobs/{id}/stop (stop), GET /api/jobs/{id}/logs (full logs), GET /api/jobs/{id}/logs with tail param (FR-011, FR-016, FR-019)
- [x] T031 [US2] Implement PortForwardManager in src/kuberay_sdk/services/port_forward.py: subprocess-based kubectl port-forward to head service port 8265, lifecycle management (start/stop/cleanup), local URL generation (FR-027)
- [x] T032 [US2] Implement JobService in src/kuberay_sdk/services/job_service.py: create_job (CRD mode via CustomObjectsApi), submit_job (Dashboard mode via DashboardClient), list_jobs (CRD + Dashboard), get_job, stop_job, wait_for_job (FR-010 through FR-015)
- [x] T033 [US2] Implement JobHandle class in src/kuberay_sdk/client.py: status(), logs(stream, follow, tail), stop(), wait(timeout), progress()
- [x] T034 [US2] Wire create_job, get_job, list_jobs into KubeRayClient; wire submit_job and list_jobs into ClusterHandle in src/kuberay_sdk/client.py

**Checkpoint**: US2 fully functional. `client.create_job("train", entrypoint="python train.py", workers=2)` creates RayJob CR. `cluster.submit_job(entrypoint="python train.py")` submits via Dashboard. Job logs retrievable.

---

## Phase 5: User Story 3 — Stream Logs and Download Artifacts (Priority: P3)

**Goal**: Users can stream logs in real-time from running jobs and download output artifacts via Dashboard API or PVC copy.

**Independent Test**: Mock SSE stream from Dashboard, verify logs iterator yields lines in real-time. Mock artifact download and verify files saved to local path.

**Dependencies**: US2 (DashboardClient and JobHandle must exist)

### Tests for User Story 3

- [x] T035 [P] [US3] Unit test for SSE log streaming (stream=True, follow=True) with mock text/event-stream responses in tests/unit/test_dashboard.py; include latency assertion that first log line is yielded within 2 seconds of call (SC-007)
- [x] T036 [P] [US3] Unit test for artifact download (Dashboard API mode + PVC copy mode) in tests/unit/test_dashboard.py

### Implementation for User Story 3

- [x] T037 [US3] Implement SSE log streaming in DashboardClient: GET /api/jobs/{id}/logs/tail with httpx streaming, yield lines as iterator, follow mode blocks until job completes in src/kuberay_sdk/services/dashboard.py (FR-017)
- [x] T038 [US3] Implement artifact download in DashboardClient: download via Dashboard API artifacts endpoint + PVC copy via kubectl cp to local destination in src/kuberay_sdk/services/dashboard.py (FR-018)
- [x] T039 [US3] Wire logs(stream=True, follow=True) and download_artifacts(destination) into JobHandle in src/kuberay_sdk/client.py

**Checkpoint**: `job.logs(stream=True, follow=True)` yields log lines in real-time. `job.download_artifacts("./output")` saves artifacts locally.

---

## Phase 6: User Story 4 — Ray Serve: Deploy and Manage Serving Applications (Priority: P4)

**Goal**: Users can create, update, get status, and delete RayService CRs for deploying Ray Serve applications including LLM serving.

**Independent Test**: Create a RayService CR with import_path and num_replicas, verify CRD structure matches RAYSERVICE_SCHEMA. Call status(), update(num_replicas=4), delete().

**Dependencies**: None (independent of US1-US3, uses same Foundation)

### Tests for User Story 4

- [x] T040 [P] [US4] Contract test: verify SDK-generated RayService CRD dict matches RAYSERVICE_SCHEMA (serveConfigV2, rayClusterConfig) in tests/contract/test_service_crd.py
- [x] T041 [P] [US4] Unit test for RayService, ServiceStatus model validation in tests/unit/test_models.py
- [x] T042 [P] [US4] Unit test for ServiceService CRUD operations using mocked CustomObjectsApi in tests/unit/test_service_service.py

### Implementation for User Story 4

- [x] T043 [P] [US4] Implement RayService, ServiceStatus pydantic models in src/kuberay_sdk/models/service.py: field types, defaults, validation (import_path vs serve_config_v2 mutual exclusivity), to_crd_dict() generating serveConfigV2 YAML and rayClusterConfig
- [x] T044 [US4] Implement ServiceService in src/kuberay_sdk/services/service_service.py: create_service (build CRD, apply), get_service, list_services, update_service (patch serveConfigV2 or rayClusterConfig), delete_service (FR-020 through FR-023)
- [x] T045 [US4] Implement ServiceHandle class in src/kuberay_sdk/client.py: status() → ServiceStatus, update(num_replicas, import_path, runtime_env), delete()
- [x] T046 [US4] Wire create_service, get_service, list_services into KubeRayClient in src/kuberay_sdk/client.py

**Checkpoint**: `client.create_service("my-llm", import_path="serve_app:deployment", num_replicas=2)` creates valid RayService CR. CRUD + update works.

---

## Phase 7: User Story 5 — Storage and Runtime Environment Configuration (Priority: P5)

**Goal**: Users can attach PVCs (new or existing) and configure runtime_env (pip, conda, env_vars, working_dir) on clusters, jobs, and services.

**Independent Test**: Create a cluster with storage volumes, verify PVC specs and volumeMounts in generated CRD. Create a job with runtime_env, verify runtimeEnvYAML in CRD. Verify invalid runtime_env raises ValidationError.

**Dependencies**: US1, US2, US4 (needs create_cluster, create_job, create_service to exist for integration)

### Tests for User Story 5

- [x] T047 [P] [US5] Unit test for StorageVolume → PVC spec + volumeMount generation in tests/unit/test_models.py
- [x] T048 [P] [US5] Unit test for RuntimeEnv → runtimeEnvYAML serialization and local validation (FR-026) in tests/unit/test_models.py
- [x] T049 [P] [US5] Contract test: cluster CRD with storage has correct volumes/volumeMounts; job CRD with runtime_env has correct runtimeEnvYAML in tests/contract/test_cluster_crd.py and tests/contract/test_job_crd.py

### Implementation for User Story 5

- [x] T050 [US5] Implement PVC spec generation and volumeMount injection in ClusterService: StorageVolume → PVC manifest + volumeMount entries added to all containers in head and worker pod templates (FR-024)
- [x] T051 [US5] Implement runtime_env validation (local check before submission: pip format, conda mutual exclusivity, working_dir existence) and YAML serialization for runtimeEnvYAML field in src/kuberay_sdk/models/runtime_env.py (FR-025, FR-026)
- [x] T052 [US5] Integrate storage and runtime_env into JobService.create_job and ServiceService.create_service CRD generation in src/kuberay_sdk/services/job_service.py and src/kuberay_sdk/services/service_service.py

**Checkpoint**: `client.create_cluster("c", workers=2, storage=[StorageVolume(name="data", size="100Gi", mount_path="/data")])` generates CRD with PVC. `runtime_env={"pip": ["torch"]}` serializes into runtimeEnvYAML.

---

## Phase 8: User Story 6 — Dashboard Metrics and Job Monitoring (Priority: P6)

**Goal**: Users can get the Dashboard URL (with auto Route/Ingress detection + port-forward fallback), fetch cluster metrics, and get job progress.

**Independent Test**: Mock Route/Ingress API responses, verify dashboard_url() returns Route URL when available, falls back to port-forward. Mock Dashboard metrics endpoints, verify metrics() returns structured data.

**Dependencies**: US2 (DashboardClient and PortForwardManager must exist)

### Tests for User Story 6

- [x] T053 [P] [US6] Unit test for dashboard_url() with Route detection, Ingress detection, and port-forward fallback in tests/unit/test_dashboard.py
- [x] T054 [P] [US6] Unit test for cluster metrics and job progress fetching in tests/unit/test_dashboard.py

### Implementation for User Story 6

- [x] T055 [US6] Implement Route/Ingress detection in PortForwardManager: check for OpenShift Route (route.openshift.io/v1) for cluster head service, then K8s Ingress (networking.k8s.io/v1), return URL if found, else start port-forward in src/kuberay_sdk/services/port_forward.py (FR-027)
- [x] T056 [US6] Implement cluster metrics fetching (CPU, GPU, memory utilization, active tasks) via Dashboard API in src/kuberay_sdk/services/dashboard.py (FR-028)
- [x] T057 [US6] Implement job progress fetching via Dashboard API in src/kuberay_sdk/services/dashboard.py (FR-029)
- [x] T058 [US6] Wire dashboard_url() and metrics() into ClusterHandle; wire progress() into JobHandle in src/kuberay_sdk/client.py

**Checkpoint**: `cluster.dashboard_url()` returns Route URL on OpenShift, port-forward URL on vanilla K8s. `cluster.metrics()` returns resource utilization dict.

---

## Phase 9: User Story 7 — OpenShift Integration (Priority: P7)

**Goal**: Users on OpenShift can use hardware profiles for GPU config, Kueue queues for job scheduling, and auto-created Routes for service endpoints.

**Independent Test**: Mock HardwareProfile CR, verify SDK resolves it to correct resource requests + node selectors. Mock Kueue API, verify queue label injection. Mock Route creation for RayService.

**Dependencies**: US1, US4 (needs create_cluster and create_service for integration)

### Tests for User Story 7

- [x] T059 [P] [US7] Unit test for platform detection (OpenShift via API groups, Kueue via API groups) in tests/unit/test_platform.py
- [x] T060 [P] [US7] Unit test for HardwareProfile resolution (read CR → extract identifiers → resource requests, scheduling → node selectors/tolerations or Kueue labels) in tests/unit/test_platform.py
- [x] T061 [P] [US7] Unit test for Kueue label injection (queue-name label, priority-class label, shutdownAfterJobFinishes constraint, 7-worker-group limit) in tests/unit/test_platform.py

### Implementation for User Story 7

- [x] T062 [P] [US7] Implement platform detection in src/kuberay_sdk/platform/detection.py: is_openshift() checking route.openshift.io + config.openshift.io API groups, is_kueue_available() checking kueue.x-k8s.io API group, has_hardware_profiles() checking infrastructure.opendatahub.io CRD (FR-003)
- [x] T063 [P] [US7] Implement HardwareProfile resolution in src/kuberay_sdk/platform/openshift.py: read HardwareProfile CR from configurable namespace, extract identifiers → resource requests/limits, extract scheduling.node → nodeSelector/tolerations, extract scheduling.kueue → Kueue labels (FR-030)
- [x] T064 [P] [US7] Implement Kueue integration in src/kuberay_sdk/platform/kueue.py: inject kueue.x-k8s.io/queue-name label, optional priority-class label, enforce shutdownAfterJobFinishes=true for RayJobs, enforce 7-worker-group limit, list_queues() for available LocalQueues (FR-031)
- [x] T065 [US7] Implement Route creation for RayService endpoints in src/kuberay_sdk/platform/openshift.py: create route.openshift.io/v1 Route targeting serve service, edge TLS termination (FR-032)
- [x] T066 [US7] Integrate platform features into creation flows: hardware_profile resolution in ClusterService/JobService, queue label injection in ClusterService/JobService/ServiceService, auto Route creation in ServiceService (conditional on is_openshift) in src/kuberay_sdk/services/cluster_service.py, src/kuberay_sdk/services/job_service.py, src/kuberay_sdk/services/service_service.py

**Checkpoint**: `client.create_cluster("c", workers=2, hardware_profile="gpu-large")` resolves profile to GPU resources + node selectors. `client.create_job("j", entrypoint="...", queue="training-queue")` adds Kueue labels. RayService gets auto Route on OpenShift.

---

## Phase 10: User Story 8 — Experiment Tracking Integration (Priority: P8)

**Goal**: Users can configure MLflow experiment tracking at the job or cluster level by injecting tracking config into the runtime environment.

**Independent Test**: Create a job with experiment_tracking config, verify MLFLOW_TRACKING_URI and MLFLOW_EXPERIMENT_NAME are injected into runtime_env env_vars in the generated CRD.

**Dependencies**: US5 (RuntimeEnv model and env_vars injection must work)

### Tests for User Story 8

- [x] T067 [P] [US8] Unit test for ExperimentTracking model validation and env var injection into RuntimeEnv in tests/unit/test_models.py

### Implementation for User Story 8

- [x] T068 [P] [US8] Implement ExperimentTracking pydantic model in src/kuberay_sdk/models/runtime_env.py: provider validation (mlflow only), tracking_uri required, to_env_vars() method generating MLFLOW_TRACKING_URI, MLFLOW_EXPERIMENT_NAME, plus additional env_vars (FR-033)
- [x] T069 [US8] Integrate experiment_tracking into JobService: merge ExperimentTracking env vars into RuntimeEnv before CRD generation or Dashboard submission in src/kuberay_sdk/services/job_service.py

**Checkpoint**: `client.create_job("j", entrypoint="...", experiment_tracking={"provider": "mlflow", "tracking_uri": "http://mlflow:5000"})` injects MLflow env vars into runtimeEnvYAML.

---

## Phase 11: User Story 9 — Ray Agentic Workloads (Priority: P9)

**Goal**: Users can deploy agentic AI applications (LLM endpoint + tool execution workers) via RayService with heterogeneous worker groups.

**Independent Test**: Create a RayService with heterogeneous worker_groups (GPU group for LLM, CPU group for tools), verify CRD has correct multi-group workerGroupSpecs.

**Dependencies**: US4 (RayService CRUD), US1 (heterogeneous worker_groups support)

### Tests for User Story 9

- [x] T070 [P] [US9] Unit test for RayService creation with heterogeneous worker_groups (GPU workers + CPU workers) verifying generated CRD has multiple workerGroupSpecs with correct resources in tests/unit/test_service_service.py

### Implementation for User Story 9

- [x] T071 [US9] Validate and document that RayService creation with worker_groups=[WorkerGroup(name="llm", replicas=1, gpus=1, memory="16Gi"), WorkerGroup(name="tools", replicas=4, cpus=4)] works correctly through existing ServiceService in src/kuberay_sdk/services/service_service.py — add any missing heterogeneous worker group support if needed

**Checkpoint**: Agentic workloads deploy via `client.create_service("agent", import_path="agent_app:app", worker_groups=[...])` with mixed GPU/CPU groups.

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Async client, comprehensive error tests, type checking, quickstart validation

- [x] T072 Implement AsyncKubeRayClient in src/kuberay_sdk/async_client.py: mirror all KubeRayClient methods with async/await using httpx.AsyncClient for Dashboard calls, async K8s operations via threading executor for kubernetes client (FR-040, FR-041)
- [x] T073 [P] Unit test for AsyncKubeRayClient (verify identical method signatures, async create/get/list operations) in tests/unit/test_client.py
- [x] T074 [P] Unit test for error translation: verify all K8s ApiException status codes map to domain-specific KubeRayError subclasses with user-friendly messages in tests/unit/test_errors.py
- [x] T075 [P] Unit test for retry logic: verify exponential backoff, transient error detection, max attempts, configurable timeout in tests/unit/test_retry.py
- [x] T076 Run ruff check and mypy type checking across entire codebase; fix all issues
- [x] T077 Run quickstart.md code examples against mocked K8s client to validate API ergonomics
- [x] T078 Review all public API docstrings include usage examples per Constitution Principle I
- [x] T079 [P] Integration test for cluster lifecycle (create → wait_until_ready → scale → status → delete) with mocked K8s API in tests/integration/test_cluster_lifecycle.py
- [x] T080 [P] Integration test for job lifecycle (create_job CRD mode → wait → logs → status; submit_job Dashboard mode → stream logs → stop) with mocked K8s + Dashboard APIs in tests/integration/test_job_lifecycle.py
- [x] T081 [P] Integration test for service lifecycle (create_service → status → update → delete) with mocked K8s API in tests/integration/test_service_lifecycle.py
- [x] T082 [P] Integration test for OpenShift features (hardware_profile resolution → cluster create, Kueue queue injection → job create, Route auto-creation → service create) with mocked K8s + OpenShift APIs in tests/integration/test_openshift.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Phase 12)**: Depends on all desired user stories being complete

### User Story Dependencies

```text
Phase 2 (Foundation)
    ├── US1 (Clusters)     ← Independent, MVP
    ├── US2 (Jobs)         ← Needs US1 for ClusterHandle.submit_job
    │   ├── US3 (Logs)     ← Needs US2 DashboardClient
    │   └── US6 (Metrics)  ← Needs US2 DashboardClient + PortForwardManager
    ├── US4 (Serve)        ← Independent
    │   └── US9 (Agentic)  ← Needs US4 RayService
    ├── US5 (Storage/Env)  ← Independent (enhances US1, US2, US4)
    │   └── US8 (MLflow)   ← Needs US5 RuntimeEnv
    └── US7 (OpenShift)    ← Independent (enhances US1, US2, US4)
```

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Models before services
3. Services before client wiring
4. Core implementation before integration with other stories

### Parallel Opportunities

- **Phase 1**: T003, T004 in parallel
- **Phase 2**: T006, T007, T008, T012, T013 all in parallel
- **After Phase 2**: US1, US4, US5, US7 can all start in parallel (independent paths)
- **After US2**: US3 and US6 can start in parallel
- **Within each US**: All test tasks marked [P] in parallel; all model tasks marked [P] in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests in parallel (different files):
Task: T014 "Contract test for RayCluster CRD in tests/contract/test_cluster_crd.py"
Task: T015 "Unit test for cluster models in tests/unit/test_models.py"
Task: T016 "Unit test for ClusterService in tests/unit/test_cluster_service.py"
Task: T017 "Unit test for idempotent create in tests/unit/test_cluster_service.py"

# After tests fail, launch model implementation:
Task: T018 "Implement cluster models in src/kuberay_sdk/models/cluster.py"

# Then sequential service + client wiring:
Task: T019 "Implement ClusterService in src/kuberay_sdk/services/cluster_service.py"
Task: T020 "Implement idempotent create in src/kuberay_sdk/services/cluster_service.py"
Task: T021 "Implement ClusterHandle in src/kuberay_sdk/client.py"
Task: T022 "Wire cluster methods into KubeRayClient"
Task: T023 "Add advanced K8s params support"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (Cluster CRUD)
4. **STOP and VALIDATE**: Test US1 independently — create, list, scale, delete clusters
5. Deploy/demo if ready — this alone delivers core value

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (Clusters) → Test independently → **MVP!**
3. Add US2 (Jobs) → Test independently → Core job submission works
4. Add US3 (Logs) → Real-time log streaming available
5. Add US4 (Serve) → Model serving via RayService
6. Add US5 (Storage/Env) → PVCs and runtime_env across all resources
7. Add US6 (Metrics) → Dashboard monitoring
8. Add US7 (OpenShift) → Hardware profiles, Kueue, Routes
9. Add US8 (MLflow) → Experiment tracking
10. Add US9 (Agentic) → Agentic workload validation
11. Polish → Async client, error coverage, type checking, docs

### Parallel Team Strategy

With multiple developers after Phase 2 completes:

- **Developer A**: US1 → US2 → US3 (cluster → jobs → logs pipeline)
- **Developer B**: US4 → US9 (serving → agentic pipeline)
- **Developer C**: US5 → US8 (storage/env → experiment tracking)
- **Developer D**: US7 → US6 (OpenShift → metrics)

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story independently completable and testable
- Tests MUST fail before implementing (Constitution Principle IV)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Total: 82 tasks across 12 phases
