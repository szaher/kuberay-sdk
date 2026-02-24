# Tasks: SDK UX & Developer Experience Enhancements

**Input**: Design documents from `/specs/004-sdk-ux-enhancements/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included per constitution principle IV (Test-First, NON-NEGOTIABLE). Tests MUST be written first and confirmed to fail before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add new dependency and create directory scaffolding for new modules

- [x] T001 Add `click>=8.1` to project dependencies in pyproject.toml and register `kuberay` console script entry point (`kuberay_sdk.cli.main:cli`)
- [x] T002 [P] Create CLI package scaffolding with empty `__init__.py` files in src/kuberay_sdk/cli/__init__.py
- [x] T003 [P] Create empty model files: src/kuberay_sdk/models/progress.py, src/kuberay_sdk/models/capabilities.py
- [x] T004 [P] Create empty test directory tests/docs/ with __init__.py for documentation validation tests
- [x] T005 Run `uv lock` to update uv.lock with new click dependency

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No cross-cutting foundational work required — all user stories are independently implementable after Phase 1 setup.

**Checkpoint**: Setup complete — user story implementation can begin.

---

## Phase 3: User Story 1 — Actionable Error Messages (Priority: P1) MVP

**Goal**: Every SDK error includes a `remediation` attribute with actionable recovery instructions (kubectl commands, documentation links).

**Independent Test**: Trigger each error type and verify `.remediation` is a non-empty string with kubectl commands.

### Tests for User Story 1

- [x] T006 [P] [US1] Write unit tests for remediation attribute on KubeRayError base class and all subclasses in tests/unit/test_errors.py (extend existing file): test every error class has non-empty `remediation`, test remediation contains kubectl commands for ClusterNotFoundError/DashboardUnreachableError/AuthenticationError/TimeoutError/KubeRayOperatorNotFoundError, test backward compatibility (KubeRayError with no remediation defaults to empty string)

### Implementation for User Story 1

- [x] T007 [US1] Add `remediation` parameter to `KubeRayError.__init__()` in src/kuberay_sdk/errors.py (default `""`), update all error subclasses to pass remediation strings with kubectl commands and doc links per contracts/errors.md
- [x] T008 [US1] Update `translate_k8s_error()` in src/kuberay_sdk/errors.py to include remediation hints in translated errors (401/403/404/409/422/5xx paths)

**Checkpoint**: All errors have actionable `.remediation` attribute. Existing tests still pass.

---

## Phase 4: User Story 2 — Progress Feedback for Long Operations (Priority: P2)

**Goal**: Blocking wait methods accept an optional `progress_callback` invoked at each poll cycle with `ProgressStatus`.

**Independent Test**: Call `wait_until_ready()` with a callback, verify callback is invoked with ProgressStatus objects.

### Tests for User Story 2

- [x] T009 [P] [US2] Write ProgressStatus model tests in tests/unit/test_progress.py: test model creation, validation (elapsed_seconds >= 0), default values
- [x] T010 [P] [US2] Write progress callback unit tests in tests/unit/test_client.py (extend existing): test callback invoked during wait, test no callback = silent, test callback exception is caught and logged, test TimeoutError includes last_status

### Implementation for User Story 2

- [x] T011 [US2] Implement ProgressStatus pydantic model in src/kuberay_sdk/models/progress.py per data-model.md, re-export from src/kuberay_sdk/models/__init__.py
- [x] T012 [US2] Add `progress_callback` parameter to `ClusterService.wait_until_ready()` in src/kuberay_sdk/services/cluster_service.py: invoke callback each poll cycle with ProgressStatus, catch callback exceptions
- [x] T013 [US2] Add `progress_callback` parameter to `JobService.wait()` and `JobService.wait_dashboard_job()` in src/kuberay_sdk/services/job_service.py
- [x] T014 [US2] Add `progress_callback` parameter to `ClusterHandle.wait_until_ready()` and `JobHandle.wait()` in src/kuberay_sdk/client.py, pass through to service layer
- [x] T015 [US2] Add `progress_callback` parameter to `AsyncClusterHandle.wait_until_ready()` and `AsyncJobHandle.wait()` in src/kuberay_sdk/async_client.py
- [x] T016 [US2] Update `TimeoutError.__init__()` in src/kuberay_sdk/errors.py to accept optional `last_status: ProgressStatus | None = None` attribute

**Checkpoint**: Wait methods support optional progress callbacks. Default behavior unchanged.

---

## Phase 5: User Story 3 — Configuration File and Environment Variable Support (Priority: P3)

**Goal**: SDK loads config from `~/.kuberay/config.yaml` and `KUBERAY_*` env vars with proper precedence chain.

**Independent Test**: Set env vars / create config file, instantiate `KubeRayClient()` without args, verify config is loaded.

### Tests for User Story 3

- [x] T017 [P] [US3] Write config file and env var loading tests in tests/unit/test_config_file.py: test load from YAML file, test env var loading (KUBERAY_NAMESPACE, KUBERAY_TIMEOUT, KUBERAY_RETRY_MAX_ATTEMPTS, KUBERAY_RETRY_BACKOFF_FACTOR), test precedence (explicit > env > file > defaults), test missing file = no error, test invalid YAML raises ValidationError, test invalid env var type raises ValidationError, test KUBERAY_CONFIG overrides default path, test config path is directory raises error

### Implementation for User Story 3

- [x] T018 [US3] Implement `load_config_file()`, `load_env_vars()`, and `resolve_config()` functions in src/kuberay_sdk/config.py per contracts/config.md
- [x] T019 [US3] Update `KubeRayClient.__init__()` in src/kuberay_sdk/client.py to call `resolve_config()` when config is None, and `AsyncKubeRayClient.__init__()` in src/kuberay_sdk/async_client.py similarly

**Checkpoint**: SDK auto-loads config from file and env vars. No changes when neither exists.

---

## Phase 6: User Story 4 — Better Handle Representations (Priority: P4)

**Goal**: Handle objects display name, namespace, and mode in `repr()` output.

**Independent Test**: Create handles and verify `repr()` output format.

### Tests for User Story 4

- [x] T020 [P] [US4] Write handle `__repr__` tests in tests/unit/test_handles_repr.py: test ClusterHandle repr shows name and namespace, test JobHandle repr shows name, namespace, and mode, test ServiceHandle repr shows name and namespace, test AsyncClusterHandle/AsyncJobHandle/AsyncServiceHandle repr matches sync versions

### Implementation for User Story 4

- [x] T021 [US4] Add `__repr__` methods to ClusterHandle, JobHandle, ServiceHandle in src/kuberay_sdk/client.py per contracts/handles.md (use only constructor-time values, no API calls)
- [x] T022 [US4] Add `__repr__` methods to AsyncClusterHandle, AsyncJobHandle, AsyncServiceHandle in src/kuberay_sdk/async_client.py

**Checkpoint**: All handles display informative repr in REPL/notebook.

---

## Phase 7: User Story 5 — Convenience Re-exports (Priority: P5)

**Goal**: Common types importable directly from `kuberay_sdk` package.

**Independent Test**: `from kuberay_sdk import WorkerGroup, RuntimeEnv, StorageVolume` succeeds.

### Tests for User Story 5

- [x] T023 [P] [US5] Write import tests in tests/unit/test_imports.py: test `from kuberay_sdk import WorkerGroup`, `RuntimeEnv`, `StorageVolume`, `ClusterConfig`, `JobConfig`, `ServiceConfig` all resolve, test they are the same objects as the deep imports, test `__all__` includes all re-exported names

### Implementation for User Story 5

- [x] T024 [US5] Add re-exports for WorkerGroup, RuntimeEnv, StorageVolume, ClusterConfig, JobConfig, ServiceConfig, HeadNodeConfig, ExperimentTracking to src/kuberay_sdk/__init__.py and update `__all__` list

**Checkpoint**: Common types importable from top-level package.

---

## Phase 8: User Story 6 — Dry-Run and Validation Mode (Priority: P6)

**Goal**: `create_cluster/job/service(..., dry_run=True)` returns CRD manifest without creating resources.

**Independent Test**: Call with `dry_run=True`, verify DryRunResult returned, no API call made.

### Tests for User Story 6

- [x] T025 [P] [US6] Write DryRunResult model tests in tests/unit/test_dry_run.py: test to_dict(), test to_yaml() produces valid YAML with apiVersion/kind, test validation rejects manifest without required keys
- [x] T026 [P] [US6] Write dry-run integration tests in tests/unit/test_dry_run.py: test create_cluster(dry_run=True) returns DryRunResult, test no K8s API call is made, test invalid params raise ValidationError before returning, test create_job(dry_run=True) works, test create_service(dry_run=True) works

### Implementation for User Story 6

- [x] T027 [US6] Implement DryRunResult class in src/kuberay_sdk/models/common.py per data-model.md: `to_dict()`, `to_yaml()` methods, manifest validation, re-export from src/kuberay_sdk/models/__init__.py
- [x] T028 [US6] Add `dry_run: bool = False` parameter to `create_cluster()`, `create_job()`, `create_service()` in src/kuberay_sdk/client.py: when True, build config model, call `to_crd_dict()`, return DryRunResult
- [x] T029 [US6] Add `dry_run: bool = False` parameter to `create_cluster()`, `create_job()`, `create_service()` in src/kuberay_sdk/async_client.py

**Checkpoint**: Users can preview CRD manifests before creating resources.

---

## Phase 9: User Story 7 — Preset Configurations (Priority: P7)

**Goal**: Built-in presets (dev, gpu-single, data-processing) simplify cluster creation.

**Independent Test**: `create_cluster("test", preset="dev", dry_run=True)` returns manifest with preset defaults.

### Tests for User Story 7

- [x] T030 [P] [US7] Write preset tests in tests/unit/test_presets.py: test list_presets() returns >= 3 presets, test get_preset("dev") returns correct defaults, test get_preset("nonexistent") raises ValueError, test Preset model fields and validation
- [x] T031 [P] [US7] Write preset integration tests in tests/unit/test_presets.py: test create_cluster with preset applies defaults (using dry_run=True), test explicit params override preset values, test preset as string vs Preset object

### Implementation for User Story 7

- [x] T032 [US7] Implement Preset model, built-in presets (dev, gpu-single, data-processing), `get_preset()`, and `list_presets()` in src/kuberay_sdk/presets.py per data-model.md and contracts/presets.md
- [x] T033 [US7] Add `preset: str | Preset | None = None` parameter to `create_cluster()` in src/kuberay_sdk/client.py and src/kuberay_sdk/async_client.py: resolve preset, merge with explicit params (explicit wins)

**Checkpoint**: Users can create clusters with preset names.

---

## Phase 10: User Story 8 — Compound Operations (Priority: P8)

**Goal**: `create_cluster_and_submit_job()` chains create → wait → submit in one call.

**Independent Test**: Call compound method, verify cluster created, waited, job submitted.

### Tests for User Story 8

- [x] T034 [P] [US8] Write compound operation tests in tests/unit/test_compound.py: test create_cluster_and_submit_job returns JobHandle, test wait timeout leaves cluster intact (not deleted) and raises error, test error includes cluster handle for cleanup

### Implementation for User Story 8

- [x] T035 [US8] Implement `create_cluster_and_submit_job()` method on KubeRayClient in src/kuberay_sdk/client.py per contracts and research.md: create cluster, wait_until_ready, submit_job_to_cluster, return JobHandle; on failure raise with cluster handle attached
- [x] T036 [US8] Implement `create_cluster_and_submit_job()` method on AsyncKubeRayClient in src/kuberay_sdk/async_client.py

**Checkpoint**: Most common workflow is a single method call.

---

## Phase 11: User Story 9 — Retry Jitter (Priority: P9)

**Goal**: Retry delays include random jitter to prevent thundering herd.

**Independent Test**: Run multiple retries, verify delays are non-deterministic.

### Tests for User Story 9

- [x] T037 [P] [US9] Write jitter tests in tests/unit/test_retry.py (extend existing): test that retry delays are non-deterministic (run twice, delays differ), test maximum delay does not exceed 2x base exponential delay, test jitter is bounded (delay >= 0)

### Implementation for User Story 9

- [x] T038 [US9] Add full jitter to exponential backoff delay calculation in src/kuberay_sdk/retry.py line 69: `import random; delay = random.uniform(0, backoff_factor * (2 ** (attempt - 1)))` per research.md R5

**Checkpoint**: Retry jitter prevents thundering herd. One-line change.

---

## Phase 12: User Story 10 — CLI Tool (Priority: P10)

**Goal**: `kuberay` CLI with cluster/job/service subcommands for terminal usage.

**Independent Test**: `kuberay cluster list` outputs a table of clusters.

### Tests for User Story 10

- [x] T039 [P] [US10] Write CLI tests in tests/unit/test_cli.py: test `kuberay --help` shows cluster/job/service subcommands, test `kuberay --version` shows SDK version, test `kuberay cluster list` with mock returns table output, test `kuberay cluster list --output json` returns valid JSON, test `kuberay cluster create` with mock, test error output includes remediation hint on stderr

### Implementation for User Story 10

- [x] T040 [US10] Implement table/JSON output formatters in src/kuberay_sdk/cli/formatters.py: `format_table(headers, rows)` and `format_json(data)` functions
- [x] T041 [US10] Implement Click CLI entry point and global options in src/kuberay_sdk/cli/main.py: `cli` group with `--namespace`, `--output`, `--config`, `--version` options per contracts/cli.md
- [x] T042 [US10] Implement `kuberay cluster` subcommands (create, list, get, delete, scale) in src/kuberay_sdk/cli/cluster.py
- [x] T043 [US10] Implement `kuberay job` subcommands (create, list, get, delete) in src/kuberay_sdk/cli/job.py
- [x] T044 [US10] Implement `kuberay service` subcommands (create, list, get, delete) in src/kuberay_sdk/cli/service.py
- [x] T045 [US10] Implement `kuberay capabilities` subcommand in src/kuberay_sdk/cli/main.py (depends on US11 capability discovery — use basic version if US11 not yet complete)

**Checkpoint**: `kuberay` CLI fully functional from terminal.

---

## Phase 13: User Story 11 — Capability Discovery (Priority: P11)

**Goal**: `client.get_capabilities()` returns ClusterCapabilities with KubeRay, GPU, Kueue, OpenShift detection.

**Independent Test**: Call with mocked K8s API, verify capability flags match mock data.

### Tests for User Story 11

- [x] T046 [P] [US11] Write ClusterCapabilities model tests in tests/unit/test_capabilities.py: test model creation with all fields, test default values (all False/None/empty)
- [x] T047 [P] [US11] Write capability discovery tests in tests/unit/test_capabilities.py: test full-capability cluster returns all True, test minimal cluster returns kuberay only, test RBAC error returns None for affected field, test network error raises KubeRayError

### Implementation for User Story 11

- [x] T048 [US11] Implement ClusterCapabilities pydantic model in src/kuberay_sdk/models/capabilities.py per data-model.md, re-export from src/kuberay_sdk/models/__init__.py
- [x] T049 [US11] Implement capability detection logic in src/kuberay_sdk/capabilities.py: detect KubeRay version, GPU availability, Kueue CRDs, OpenShift platform — handle RBAC errors gracefully per contracts/capabilities.md
- [x] T050 [US11] Add `get_capabilities()` method to KubeRayClient in src/kuberay_sdk/client.py and AsyncKubeRayClient in src/kuberay_sdk/async_client.py

**Checkpoint**: Users can programmatically discover cluster capabilities.

---

## Phase 14: User Story 12 — Troubleshooting Documentation (Priority: P12)

**Goal**: Troubleshooting guide with >= 5 common issues and resolutions.

**Independent Test**: Verify docs/user-guide/troubleshooting.md exists with >= 5 issue sections.

### Tests for User Story 12

- [x] T051 [P] [US12] Write documentation validation test in tests/docs/test_troubleshooting.py: test troubleshooting.md exists, test it contains at least 5 issue headings, test it covers: cluster stuck creating, dashboard unreachable, auth failures, operator not found, job timeout

### Implementation for User Story 12

- [x] T052 [US12] Write troubleshooting guide at docs/user-guide/troubleshooting.md covering: cluster stuck in creating state, dashboard unreachable, authentication failures, KubeRay operator not found, job timeout — each with symptoms, causes, and step-by-step resolution
- [x] T053 [US12] Add troubleshooting page to mkdocs.yml nav under User Guide section

**Checkpoint**: Troubleshooting documentation complete and linked in nav.

---

## Phase 15: User Story 13 — Migration Guide (Priority: P13)

**Goal**: "If you know kubectl" guide mapping >= 10 kubectl commands to SDK equivalents.

**Independent Test**: Verify docs/user-guide/migration.md exists with >= 10 command mappings.

### Tests for User Story 13

- [x] T054 [P] [US13] Write migration guide validation test in tests/docs/test_migration.py: test migration.md exists, test it contains at least 10 kubectl-to-SDK mappings, test it covers CRUD for clusters, jobs, and services

### Implementation for User Story 13

- [x] T055 [US13] Write migration guide at docs/user-guide/migration.md with side-by-side kubectl vs SDK examples covering: list/get/create/delete clusters, list/get/create/delete jobs, list/get/create/delete services, scale cluster, get dashboard URL
- [x] T056 [US13] Add migration guide page to mkdocs.yml nav under User Guide section

**Checkpoint**: Migration guide complete and linked in nav.

---

## Phase 16: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, validation, and cleanup

- [x] T057 Update src/kuberay_sdk/models/__init__.py to re-export all new models (ProgressStatus, DryRunResult, ClusterCapabilities) and update `__all__`
- [x] T058 [P] Run `ruff check src/ tests/` and fix any linting issues across all new files
- [x] T059 [P] Run `mypy src/kuberay_sdk/` and fix any type errors across all new files
- [x] T060 Run full test suite `pytest tests/` and verify all tests pass (existing 502 + new tests)
- [x] T061 Verify quickstart.md scenarios work by reviewing implementation matches documented examples in specs/004-sdk-ux-enhancements/quickstart.md
- [x] T062 Verify all new public classes and functions have docstrings per constitution Principle I (API-First Design): scan src/kuberay_sdk/presets.py, src/kuberay_sdk/capabilities.py, src/kuberay_sdk/models/progress.py, src/kuberay_sdk/models/capabilities.py, src/kuberay_sdk/cli/*.py for missing docstrings

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: No foundational work needed — proceed to stories
- **User Stories (Phase 3–15)**: All depend on Phase 1 setup completion
  - Most stories are fully independent and can proceed in parallel
  - See inter-story dependencies below
- **Polish (Phase 16)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Errors, P1)**: Independent — can start after Phase 1
- **US2 (Progress, P2)**: Independent — can start after Phase 1. Adds `last_status` to TimeoutError (modifies errors.py after US1 changes)
- **US3 (Config, P3)**: Independent — can start after Phase 1
- **US4 (Handles, P4)**: Independent — can start after Phase 1
- **US5 (Imports, P5)**: Independent — can start after Phase 1. Should run AFTER other stories add new models to avoid merge conflicts in `__init__.py`
- **US6 (Dry-Run, P6)**: Independent — can start after Phase 1
- **US7 (Presets, P7)**: Independent — can start after Phase 1
- **US8 (Compound, P8)**: Soft dependency on US2 (progress_callback param) — can implement without it using `None` default
- **US9 (Jitter, P9)**: Independent — can start after Phase 1
- **US10 (CLI, P10)**: Soft dependency on US3 (config loading) and US7 (presets). Can implement with basic functionality first, integrate later.
- **US11 (Capabilities, P11)**: Independent — can start after Phase 1. US10 T045 has soft dependency.
- **US12 (Troubleshooting, P12)**: Independent — can start after Phase 1
- **US13 (Migration, P13)**: Independent — can start after Phase 1

### Within Each User Story

- Tests MUST be written first and confirmed to FAIL before implementation
- Models before services
- Services before client methods
- Sync before async variants

### Parallel Opportunities

- All test tasks marked [P] within a story can run in parallel
- The following stories can proceed fully in parallel (different files):
  - US1 (errors.py) + US3 (config.py) + US4 (client.py handles) + US9 (retry.py) + US12 + US13
- US2, US6, US7, US8, US10 all modify client.py — sequence these or coordinate carefully

---

## Parallel Example: User Story 1

```bash
# Launch test tasks in parallel:
Task: "Write unit tests for remediation attribute in tests/unit/test_errors.py"

# Then implement sequentially:
Task: "Add remediation to KubeRayError and all subclasses in src/kuberay_sdk/errors.py"
Task: "Update translate_k8s_error() with remediation hints in src/kuberay_sdk/errors.py"
```

## Parallel Example: Independent Stories

```bash
# These stories can run simultaneously (no file conflicts):
Story US1: errors.py modifications
Story US3: config.py modifications
Story US9: retry.py modifications
Story US12: docs/user-guide/troubleshooting.md (new file)
Story US13: docs/user-guide/migration.md (new file)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T005)
2. Complete Phase 3: User Story 1 — Actionable Errors (T006–T008)
3. **STOP and VALIDATE**: Verify all errors have `.remediation`, existing 502 tests pass
4. This alone provides significant UX improvement

### Incremental Delivery

1. Setup → US1 (errors) → **MVP!**
2. US9 (jitter, one-line fix) → US4 (handle repr) → US5 (imports) — quick wins
3. US3 (config files) → US2 (progress callbacks) — medium effort
4. US6 (dry-run) → US7 (presets) → US8 (compound ops) — build on each other
5. US10 (CLI) → US11 (capabilities) — larger features
6. US12 + US13 (docs) — can be done anytime in parallel
7. Polish → Complete

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup together (Phase 1)
2. Once Setup is done:
   - Developer A: US1 (errors) → US2 (progress) → US8 (compound)
   - Developer B: US3 (config) → US6 (dry-run) → US7 (presets)
   - Developer C: US9 (jitter) → US4 (handles) → US5 (imports) → US10 (CLI)
   - Developer D: US11 (capabilities) → US12 + US13 (docs)
3. Stories integrate independently via different files

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Constitution requires tests first (TDD) — write and verify failure before implementing
- Commit after each completed user story
- Stop at any checkpoint to validate story independently
- client.py is modified by US2, US6, US7, US8, US10, US11 — coordinate changes to avoid conflicts
