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

## Phase 16: Polish & Cross-Cutting Concerns (US1–US13)

**Purpose**: Final integration, validation, and cleanup for US1–US13 implementation

- [x] T057 Update src/kuberay_sdk/models/__init__.py to re-export all new models (ProgressStatus, DryRunResult, ClusterCapabilities) and update `__all__`
- [x] T058 [P] Run `ruff check src/ tests/` and fix any linting issues across all new files
- [x] T059 [P] Run `mypy src/kuberay_sdk/` and fix any type errors across all new files
- [x] T060 Run full test suite `pytest tests/` and verify all tests pass (existing 502 + new tests)
- [x] T061 Verify quickstart.md scenarios work by reviewing implementation matches documented examples in specs/004-sdk-ux-enhancements/quickstart.md
- [x] T062 Verify all new public classes and functions have docstrings per constitution Principle I (API-First Design): scan src/kuberay_sdk/presets.py, src/kuberay_sdk/capabilities.py, src/kuberay_sdk/models/progress.py, src/kuberay_sdk/models/capabilities.py, src/kuberay_sdk/cli/*.py for missing docstrings

**Checkpoint**: All US1–US13 implementation tasks complete. 692 tests passing, ruff+mypy clean.

---

## Phase 17: User Story 14 — Comprehensive Documentation for New Features (Priority: P14)

**Goal**: Document all 8 new SDK capabilities (dry-run, presets, progress callbacks, CLI, capability discovery, compound ops, config file/env vars, convenience imports) in README, user guide, and example scripts so users can discover and adopt them.

**Independent Test**: Review README for 8 new feature sections with code snippets (SC-013). Run `ruff check examples/` to validate all example scripts pass syntax validation (SC-014). Verify docs site pages render correctly.

### Phase 17a: Example Scripts (FR-035)

**Purpose**: Create 8 standalone example scripts demonstrating each new feature. All scripts must be runnable without a live cluster where possible; cluster-dependent steps annotated with comments.

- [ ] T063 [P] [US14] Create standalone example script for convenience re-exports in examples/convenience_imports.py: import WorkerGroup, RuntimeEnv, StorageVolume, SDKConfig, KubeRayClient from top-level package, print types to verify, include before/after comparison in comments
- [ ] T064 [P] [US14] Create standalone example script for config file and env vars in examples/config_and_env_vars.py: write temp ~/.kuberay/config.yaml, set KUBERAY_NAMESPACE env var, show precedence (explicit > env > file > defaults), include credential warning comment, clean up temp file
- [ ] T065 [P] [US14] Create standalone example script for dry-run mode in examples/dry_run_preview.py: call create_cluster(dry_run=True), print result.to_dict() and result.to_yaml(), show validation error on invalid params — fully standalone, no cluster needed
- [ ] T066 [P] [US14] Create standalone example script for presets in examples/presets_usage.py: call list_presets() and print each preset, create cluster with preset="dev" using dry_run=True, show explicit param override of preset defaults
- [ ] T067 [P] [US14] Create example script for progress callbacks in examples/progress_callbacks.py: define a progress callback function that prints ProgressStatus fields, show wait_until_ready(progress_callback=on_progress) usage with `# NOTE: Requires a running KubeRay cluster` annotation
- [ ] T068 [P] [US14] Create example script for compound operations in examples/compound_operations.py: show create_cluster_and_submit_job() method signature and usage with `# NOTE: Requires a running KubeRay cluster` annotation, include error handling showing partial failure behavior
- [ ] T069 [P] [US14] Create example script for capability discovery in examples/capability_discovery.py: show client.get_capabilities() usage with conditional logic (GPU/Kueue detection), annotate cluster-required step with `# NOTE: Requires a running KubeRay cluster`
- [ ] T070 [P] [US14] Create CLI usage example shell script in examples/cli_usage.sh: demonstrate kuberay cluster list, kuberay cluster create, kuberay job create, kuberay capabilities, kuberay --help, kuberay cluster list --output json — annotate cluster-dependent commands with `# Requires: live KubeRay cluster`

### Phase 17b: README Updates (FR-034, FR-036)

**Purpose**: Add 8 new feature sections to README.md with quick-start code snippets, version annotations, and config precedence diagram with credential warning.

- [ ] T071 [US14] Add 8 new feature sections to README.md after the existing "Async Client" section. Each section has a heading, `*Added in v0.2.0*` version annotation, 1-2 sentence description, and runnable code snippet. Sections in order: (1) Convenience Imports, (2) Configuration File & Environment Variables (with precedence order and credential warning per FR-036), (3) Dry-Run Mode, (4) Presets, (5) Progress Callbacks, (6) Compound Operations, (7) Capability Discovery, (8) CLI Tool (with link to docs site CLI reference page)

### Phase 17c: Docs Site Pages (FR-034, FR-037)

**Purpose**: Create new user guide page and CLI reference page on the MkDocs docs site.

- [ ] T072 [P] [US14] Create comprehensive user guide page at docs/user-guide/new-features.md covering all 8 new features with detailed usage examples, configuration options, edge cases, and cross-links to existing docs (configuration.md, error-handling.md). Each feature section has `*Added in v0.2.0*` version annotation. Include config precedence diagram with credential warning per FR-036
- [ ] T073 [P] [US14] Create CLI command reference page at docs/user-guide/cli-reference.md per FR-037 and contracts/documentation.md: overview command tree, global options (--namespace, --output, --config), per-subcommand sections for cluster/job/service with synopsis, options table, and example output (table + JSON), kuberay capabilities command

### Phase 17d: Navigation and Index Updates

**Purpose**: Wire new pages into MkDocs nav and update example index.

- [ ] T074 [US14] Update mkdocs.yml nav to add: `New Features: user-guide/new-features.md` (under User Guide, after Configuration), `CLI Reference: user-guide/cli-reference.md` (under User Guide, after New Features), and new example page entries under Examples section
- [ ] T075 [P] [US14] Update docs/examples/index.md to add links and descriptions for all 8 new example scripts (convenience_imports.py, config_and_env_vars.py, dry_run_preview.py, presets_usage.py, progress_callbacks.py, compound_operations.py, capability_discovery.py, cli_usage.sh)

### Phase 17e: Validation (SC-013, SC-014)

**Purpose**: Verify all documentation deliverables meet success criteria.

- [ ] T076 [US14] Run `ruff check examples/` to validate all example scripts (including 8 new scripts) pass syntax validation (SC-014). Fix any issues found.
- [ ] T077 [US14] Verify all 8 new features are documented in README.md with at least one runnable code snippet per feature (SC-013). Verify version annotations present on all new sections. Verify config credential warning present. Verify CLI reference link works.

**Checkpoint**: All US14 documentation deliverables complete. 8 features documented in README, user guide page created, CLI reference page created, 8 example scripts pass ruff check.

---

## Phase 18: Final Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all US1–US14 deliverables

- [ ] T078 Run full test suite `pytest tests/` to verify existing 692 tests still pass after documentation changes
- [ ] T079 [P] Run `ruff check src/ tests/ examples/` to verify all Python files pass linting
- [ ] T080 Verify quickstart.md scenarios in specs/004-sdk-ux-enhancements/quickstart.md match the documented examples in README.md and docs/user-guide/new-features.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: No foundational work needed — proceed to stories
- **User Stories (Phase 3–15)**: All depend on Phase 1 setup completion
  - Most stories are fully independent and can proceed in parallel
  - See inter-story dependencies below
- **Polish US1–US13 (Phase 16)**: Depends on all US1–US13 stories being complete ✅ DONE
- **US14 Documentation (Phase 17)**: Depends on Phase 16 completion (documents implemented features)
- **Final Polish (Phase 18)**: Depends on Phase 17 completion

### User Story Dependencies

- **US1 (Errors, P1)**: Independent — can start after Phase 1 ✅ DONE
- **US2 (Progress, P2)**: Independent — can start after Phase 1. Adds `last_status` to TimeoutError (modifies errors.py after US1 changes) ✅ DONE
- **US3 (Config, P3)**: Independent — can start after Phase 1 ✅ DONE
- **US4 (Handles, P4)**: Independent — can start after Phase 1 ✅ DONE
- **US5 (Imports, P5)**: Independent — can start after Phase 1. Should run AFTER other stories add new models to avoid merge conflicts in `__init__.py` ✅ DONE
- **US6 (Dry-Run, P6)**: Independent — can start after Phase 1 ✅ DONE
- **US7 (Presets, P7)**: Independent — can start after Phase 1 ✅ DONE
- **US8 (Compound, P8)**: Soft dependency on US2 (progress_callback param) — can implement without it using `None` default ✅ DONE
- **US9 (Jitter, P9)**: Independent — can start after Phase 1 ✅ DONE
- **US10 (CLI, P10)**: Soft dependency on US3 (config loading) and US7 (presets). Can implement with basic functionality first, integrate later. ✅ DONE
- **US11 (Capabilities, P11)**: Independent — can start after Phase 1. US10 T045 has soft dependency. ✅ DONE
- **US12 (Troubleshooting, P12)**: Independent — can start after Phase 1 ✅ DONE
- **US13 (Migration, P13)**: Independent — can start after Phase 1 ✅ DONE
- **US14 (Documentation, P14)**: Depends on US1–US13 completion (documents all implemented features). Can start after Phase 16.

### Within US14

- Example scripts (T063–T070) can all run in parallel — different files
- README update (T071) can run in parallel with docs site pages (T072, T073) — different files
- Nav updates (T074, T075) depend on T072 and T073 (pages must exist first)
- Validation (T076, T077) depends on all prior US14 tasks

### Within Each User Story (US1–US13)

- Tests MUST be written first and confirmed to FAIL before implementation
- Models before services
- Services before client methods
- Sync before async variants

### Parallel Opportunities

- All test tasks marked [P] within a story can run in parallel
- The following stories can proceed fully in parallel (different files):
  - US1 (errors.py) + US3 (config.py) + US4 (client.py handles) + US9 (retry.py) + US12 + US13
- US2, US6, US7, US8, US10 all modify client.py — sequence these or coordinate carefully
- **US14 parallelism**: All 8 example scripts (T063–T070) can run simultaneously. README (T071), user guide (T072), and CLI reference (T073) can also run simultaneously — all different files.

---

## Parallel Example: US14 Example Scripts

```bash
# Launch all 8 example script tasks in parallel (different files, no dependencies):
Task T063: "Create examples/convenience_imports.py"
Task T064: "Create examples/config_and_env_vars.py"
Task T065: "Create examples/dry_run_preview.py"
Task T066: "Create examples/presets_usage.py"
Task T067: "Create examples/progress_callbacks.py"
Task T068: "Create examples/compound_operations.py"
Task T069: "Create examples/capability_discovery.py"
Task T070: "Create examples/cli_usage.sh"
```

## Parallel Example: US14 Documentation Pages

```bash
# Launch documentation tasks in parallel (different files):
Task T071: "Update README.md with 8 new feature sections"
Task T072: "Create docs/user-guide/new-features.md"
Task T073: "Create docs/user-guide/cli-reference.md"
```

---

## Implementation Strategy

### US1–US13 (Complete)

All 62 implementation tasks (T001–T062) are complete with 692 tests passing, ruff+mypy clean.

### US14 Delivery (Current Focus)

1. **Phase 17a**: Create 8 example scripts in parallel (T063–T070) — all different files, max parallelism
2. **Phase 17b**: Update README with 8 new sections (T071) — can run in parallel with Phase 17c
3. **Phase 17c**: Create user guide page (T072) + CLI reference page (T073) in parallel
4. **Phase 17d**: Wire nav entries (T074, T075) — depends on 17c completion
5. **Phase 17e**: Validate SC-013 and SC-014 (T076, T077)
6. **Phase 18**: Final polish and cross-validation (T078–T080)

### Parallel Team Strategy for US14

With multiple developers:

1. Developer A: Example scripts (T063–T070) — 8 files, all parallel
2. Developer B: README updates (T071) — single file, sequential edits
3. Developer C: Docs site pages (T072, T073) — 2 files, parallel
4. Once all content done: Developer A does nav updates (T074, T075) and validation (T076–T080)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- US1–US13: Constitution requires tests first (TDD) — write and verify failure before implementing
- US14: Documentation-only — no TDD required, validation via `ruff check` and content review
- Commit after each completed user story or logical group
- Stop at any checkpoint to validate story independently
- client.py is modified by US2, US6, US7, US8, US10, US11 — coordinate changes to avoid conflicts
- US14 example scripts must be standalone (no live cluster required) per clarification session
- US14 version annotation format: `*Added in v0.2.0*` per research.md R13
- US14 CLI reference lives on docs site (not README) per clarification session
- US14 config docs must include credential warning per clarification session
- Total tasks: 80 (T001–T062 complete, T063–T080 pending for US14)
