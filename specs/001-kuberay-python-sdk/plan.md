# Implementation Plan: KubeRay Python SDK

**Branch**: `001-kuberay-python-sdk` | **Date**: 2026-02-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-kuberay-python-sdk/spec.md`

## Summary

Build a Python SDK that enables data scientists, AI/ML practitioners, and AI engineers to manage Ray clusters, jobs, and services on Kubernetes and OpenShift without requiring Kubernetes knowledge. The SDK wraps KubeRay CRDs (`ray.io/v1`) and the Ray Dashboard REST API behind a user-friendly Python interface. Authentication is delegated to `kube-authkit`. The SDK auto-detects the platform (vanilla K8s vs OpenShift) and adapts behavior accordingly — using Routes or Ingress for Dashboard access, supporting Hardware Profiles for GPU configuration, and integrating with Kueue for job queuing.

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**: `kubernetes` (official Python client), `kube-authkit` (v0.4.0+, auth delegation), `httpx` (Dashboard REST API calls, sync+async), `pydantic` (model validation)
**Storage**: N/A (PVC lifecycle managed via Kubernetes API, no local storage)
**Testing**: pytest, pytest-asyncio, pytest-httpx (Dashboard API mocking)
**Target Platform**: Any environment with kubeconfig access to a Kubernetes cluster running KubeRay operator v1.1+
**Project Type**: Library (pip-installable package)
**Performance Goals**: Log streaming begins within 2s of call (SC-007); KubeRay operator detection on first API call (SC-008)
**Constraints**: Minimal dependencies (each must be justified); support two most recent KubeRay operator minor versions; Python 3.9+ compatibility
**Scale/Scope**: SDK library — 46 functional requirements, 6 key entities, 9 user stories; target audience: data scientists and AI/ML engineers

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Check

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. API-First Design | PASS | Public API contracts defined in `contracts/` before implementation. All public classes/functions include docstrings with usage examples. Semantic versioning planned. |
| II. User-Centric Abstraction | PASS | Flat parameters (`workers`, `gpus_per_worker`) for common cases. No K8s manifests required. Errors translated to Ray/ML domain terms (FR-037). Namespace handled via config with per-call override (FR-002). Auth configured once via kube-authkit (FR-001). |
| III. Progressive Disclosure | PASS | Simple defaults for basic usage (FR-004, FR-045). Advanced params (`worker_groups`, `labels`, `tolerations`, `node_selector`) via keyword arguments only (FR-034, FR-035, FR-046). Raw CRD overrides available (FR-036). |
| IV. Test-First (NON-NEGOTIABLE) | PASS | TDD planned: contract tests verify CRD schema compliance, unit tests cover all public methods, integration tests validate end-to-end workflows. pytest as framework. |
| V. Simplicity & YAGNI | PASS | Minimal dependencies (4 runtime). No features "for future use." Cloud storage out of scope. CLI tool out of scope. Composable primitives (cluster, job, service) over specialized helpers. |

### Post-Design Re-check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. API-First Design | PASS | Contracts defined in `contracts/api.py` (type stubs) and `contracts/crd_schemas.py` (CRD validation). |
| II. User-Centric Abstraction | PASS | All models use Python-native types. Status objects return human-readable strings. Error hierarchy uses domain terms. |
| III. Progressive Disclosure | PASS | `create_cluster("my-cluster", workers=4)` works. `create_cluster("my-cluster", worker_groups=[...], tolerations=[...])` also works. No positional args for advanced options. |
| IV. Test-First | PASS | Test categories defined: unit (models, services), contract (CRD schema compliance), integration (live cluster). |
| V. Simplicity & YAGNI | PASS | `pydantic` justified for model validation (runtime_env, storage configs). `httpx` justified for sync+async HTTP (Dashboard API). No unnecessary abstractions. |

### No violations. Gate PASSED.

## Project Structure

### Documentation (this feature)

```text
specs/001-kuberay-python-sdk/
├── plan.md              # This file
├── research.md          # Phase 0 output (technology research)
├── data-model.md        # Phase 1 output (entity definitions)
├── quickstart.md        # Phase 1 output (getting-started guide)
├── contracts/           # Phase 1 output (public API contracts)
│   ├── api.py           # Public API type stubs
│   └── crd_schemas.py   # KubeRay CRD schema contracts
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/kuberay_sdk/
├── __init__.py              # Public re-exports: KubeRayClient, AsyncKubeRayClient, models
├── client.py                # KubeRayClient (sync) — main entry point
├── async_client.py          # AsyncKubeRayClient (async) — mirrors sync client
├── config.py                # SDKConfig, namespace resolution, platform detection
├── models/
│   ├── __init__.py          # Re-exports all model classes
│   ├── cluster.py           # RayCluster, ClusterStatus, WorkerGroup, HeadNodeConfig
│   ├── job.py               # RayJob, JobStatus, JobSubmission
│   ├── service.py           # RayService, ServiceStatus
│   ├── storage.py           # StorageVolume (new PVC, existing PVC)
│   ├── runtime_env.py       # RuntimeEnv (pip, conda, env_vars, working_dir)
│   └── common.py            # Shared types: ResourceRequirements, Labels, Annotations
├── services/
│   ├── __init__.py
│   ├── cluster_service.py   # Cluster CRUD (CRD operations)
│   ├── job_service.py       # Job CRUD (CRD + Dashboard submission)
│   ├── service_service.py   # RayService CRUD (CRD operations)
│   ├── dashboard.py         # Dashboard API client (REST calls, log streaming)
│   └── port_forward.py      # Port-forward management for Dashboard access
├── platform/
│   ├── __init__.py
│   ├── detection.py         # K8s vs OpenShift detection, Kueue detection
│   ├── openshift.py         # Route CRUD, HardwareProfile resolution
│   └── kueue.py             # Kueue label injection, queue listing
├── errors.py                # Error hierarchy, K8s error translation (FR-037)
└── retry.py                 # Exponential backoff, idempotent create logic

tests/
├── conftest.py              # Shared fixtures (mock K8s client, mock Dashboard)
├── unit/
│   ├── test_models.py       # Model validation, serialization
│   ├── test_client.py       # Client initialization, config
│   ├── test_cluster_service.py
│   ├── test_job_service.py
│   ├── test_service_service.py
│   ├── test_dashboard.py
│   ├── test_errors.py
│   ├── test_retry.py
│   └── test_platform.py
├── contract/
│   ├── test_cluster_crd.py  # Generated CRDs match RayCluster schema
│   ├── test_job_crd.py      # Generated CRDs match RayJob schema
│   ├── test_service_crd.py  # Generated CRDs match RayService schema
│   └── test_dashboard_api.py # Dashboard API payloads match expected format
└── integration/
    ├── test_cluster_lifecycle.py
    ├── test_job_lifecycle.py
    ├── test_service_lifecycle.py
    └── test_openshift.py

pyproject.toml               # Project metadata, dependencies, build config
```

**Structure Decision**: Single project layout (Option 1). This is a Python library with no frontend, backend, or mobile components. The `src/` layout uses the standard `src`-based package structure recommended by PyPA. The package is `kuberay_sdk` (underscore for Python import, hyphen `kuberay-sdk` for pip). Tests are split into `unit/` (fast, mocked), `contract/` (schema validation), and `integration/` (live cluster).

## Complexity Tracking

> No constitution violations. No complexity justifications needed.

| Aspect | Decision | Justification |
|--------|----------|---------------|
| `pydantic` dependency | Added | Required for model validation (runtime_env, storage configs). Prevents invalid CRDs from being submitted. Widely used in Python data ecosystem (familiar to target users). |
| `httpx` dependency | Added | Required for sync+async HTTP client to Ray Dashboard API. `requests` is sync-only; `aiohttp` is async-only. `httpx` provides both with identical API, supporting FR-039/FR-040 (sync+async clients). |
| `platform/` sub-package | Added | Isolates OpenShift/Kueue-specific code from core SDK. Keeps the core package clean for vanilla K8s users. Detection is lazy (only runs when needed). |
