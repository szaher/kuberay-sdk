# Local Development Guide

This document covers repository layout, key modules, test strategy, documentation builds, and available Makefile targets.

---

## Repository Structure

```
kuberay-sdk/
├── src/kuberay_sdk/          # SDK source code
│   ├── __init__.py           # Public API exports
│   ├── client.py             # KubeRayClient (sync) and AsyncKubeRayClient
│   ├── errors.py             # Error hierarchy (KubeRayError, ClusterError, etc.)
│   ├── config.py             # SDKConfig (namespace, auth, defaults)
│   ├── models/               # Pydantic models (ClusterConfig, JobConfig, etc.)
│   ├── services/             # Business logic (cluster, job, service operations)
│   │   ├── cluster.py        # Cluster lifecycle management
│   │   ├── job.py            # Job submission and monitoring
│   │   ├── service.py        # Ray Serve deployment management
│   │   ├── dashboard.py      # Dashboard REST API client
│   │   └── crd_builder.py    # CRD YAML generation
│   └── platform/             # Platform-specific integrations
│       ├── openshift.py      # OpenShift routes, hardware profiles
│       └── kueue.py          # Kueue queue integration
├── tests/
│   ├── unit/                 # Fast, isolated unit tests
│   ├── contract/             # CRD schema validation tests
│   ├── integration/          # Lifecycle tests (mocked K8s API)
│   └── e2e/                  # End-to-end tests (real cluster)
├── docs/                     # MkDocs documentation site
├── examples/                 # Example scripts
├── Makefile                  # Development command runner
├── pyproject.toml            # Project configuration
└── mkdocs.yml               # Documentation site config
```

---

## Key Modules

### `client.py`

Entry point for all SDK usage. Provides two client classes:

- **`KubeRayClient`** -- synchronous client for scripts, notebooks, and CLI tools.
- **`AsyncKubeRayClient`** -- async client for FastAPI services and async workflows.

Both clients create handles for clusters, jobs, and services. They delegate authentication to `kube-authkit` and route calls to the appropriate service layer.

### `models/`

Pydantic models that define the SDK's data structures:

| Model                | Purpose                                      |
|----------------------|----------------------------------------------|
| `ClusterConfig`      | RayCluster specification (head, workers, etc.) |
| `JobConfig`          | RayJob submission parameters                 |
| `ServiceConfig`      | RayService / Ray Serve deployment config     |
| `WorkerGroupConfig`  | Worker group resources and scaling            |
| `StorageConfig`      | Persistent volume and mount definitions      |
| `RuntimeEnvConfig`   | Ray runtime environment (pip, env vars, etc.) |

### `services/`

Business logic layer. Each service handles one resource type:

- **`cluster.py`** -- Create, scale, delete, and monitor RayClusters.
- **`job.py`** -- Submit, cancel, and poll RayJobs.
- **`service.py`** -- Deploy, update, and roll back RayServices.
- **`dashboard.py`** -- Interact with the Ray Dashboard REST API via `httpx`.
- **`crd_builder.py`** -- Generate KubeRay CRD YAML from SDK models.

### `platform/`

Platform-specific integrations:

- **`openshift.py`** -- Detects OpenShift, creates Routes for Dashboard/client endpoints, maps hardware profiles to node selectors and tolerations.
- **`kueue.py`** -- Applies Kueue queue labels and resource constraints to generated CRDs.

### `errors.py`

Error hierarchy rooted at `KubeRayError`:

```
KubeRayError
├── ClusterError         # Cluster lifecycle failures
├── JobError             # Job submission / monitoring failures
├── ServiceError         # Ray Serve deployment failures
├── ValidationError      # Invalid configuration or input
└── AuthenticationError  # Credential or permission failures
```

---

## Test Categories

### Unit tests (`tests/unit/`)

Test individual functions and classes in isolation. No external dependencies (no network, no cluster). These must be fast.

```bash
make test-unit
```

### Contract tests (`tests/contract/`)

Verify that SDK-generated CRD YAML matches expected KubeRay schemas. These catch schema drift between SDK models and upstream KubeRay CRD definitions.

```bash
make test-contract
```

### Integration tests (`tests/integration/`)

Test end-to-end workflows with a mocked Kubernetes API. Validate that the client, services, and CRD builder work together correctly without requiring a live cluster.

```bash
make test-integration
```

### E2E tests (`tests/e2e/`)

Test against a real Kubernetes cluster with the KubeRay operator installed. These require cluster access and are typically run in CI or manually during release validation.

```bash
make test-e2e
```

---

## Adding New Tests

1. **Determine the category.** If the test needs no external state, put it in `tests/unit/`. If it validates CRD output, use `tests/contract/`. If it exercises multi-component flows with mocks, use `tests/integration/`. If it requires a live cluster, use `tests/e2e/`.

2. **Naming convention.** All test files must be named `test_*.py`. Test functions must start with `test_`. Example: `tests/unit/test_crd_builder.py`.

3. **Use existing fixtures.** Shared fixtures live in `conftest.py` files at each test directory level. Check `tests/conftest.py` and `tests/unit/conftest.py` before creating new fixtures. Reuse `sample_cluster_config`, `mock_k8s_client`, and similar fixtures where applicable.

4. **Run the relevant suite** to verify your new test passes in isolation before running the full suite:

```bash
make test-unit          # for unit tests
make test-contract      # for contract tests
make test-integration   # for integration tests
```

---

## Building Documentation Locally

Install all dependencies (including docs extras), then serve the site:

```bash
make install  # includes docs dependencies
uv run mkdocs serve
# Visit http://127.0.0.1:8000/kuberay-sdk/
```

The docs site uses MkDocs with Material theme. API reference pages are auto-generated from docstrings via `mkdocstrings`.

---

## Makefile Reference

| Target               | Description                                                  |
|-----------------------|--------------------------------------------------------------|
| `make help`           | Show all available targets with descriptions                 |
| `make install`        | Install project and all dependencies (including docs extras) |
| `make lint`           | Run ruff linter on the codebase                              |
| `make typecheck`      | Run mypy type checking                                       |
| `make format`         | Auto-format code with ruff                                   |
| `make test-unit`      | Run unit tests only                                          |
| `make test-contract`  | Run contract tests only                                      |
| `make test-integration` | Run integration tests only                                 |
| `make test-e2e`       | Run end-to-end tests (requires a live cluster)               |
| `make test`           | Run all tests (unit + contract + integration)                |
| `make check`          | Run lint + typecheck + test (full pre-commit validation)     |
| `make coverage`       | Run tests with coverage reporting                            |
| `make build`          | Build the Python package (sdist + wheel)                     |
| `make clean`          | Remove build artifacts, caches, and virtual environments     |
