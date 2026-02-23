# Tasks: CI Pipeline, Release Automation & Developer Guides

**Input**: Design documents from `/specs/003-ci-release-contributing/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, contracts/makefile_interface.md, contracts/ci_workflow_interface.md, quickstart.md

**Tests**: No test tasks generated — not explicitly requested in the feature specification. CI validation (workflow syntax, `make check` parity) serves as the test suite per plan.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — add test dependencies and create e2e test directory structure

- [x] T001 [P] Create `tests/e2e/` directory with `tests/e2e/__init__.py` and `tests/e2e/conftest.py` (empty placeholder with docstring describing e2e fixture purpose)
- [x] T002 [P] Add `pytest-cov>=5.0.0` and `pytest-timeout>=2.3.0` to `[project.optional-dependencies] dev` in `pyproject.toml`, then run `uv lock` to update `uv.lock`

---

## Phase 2: User Story 1 — Automated Code Quality Checks on Pull Requests (Priority: P1) MVP

**Goal**: Deliver a CI workflow that runs linting (ruff) and type checking (mypy) on every pull request, with file-path and line-number annotations, blocking merge on failure.

**Independent Test**: Open a PR with a lint violation, verify the `lint` check fails with specific file/line annotations. Fix it, verify it passes.

### Implementation for User Story 1

- [x] T003 [US1] Create `.github/workflows/ci.yml` with `lint` job (ruff check --output-format=github, ruff format --check) and `typecheck` job (mypy src/), both running on Python 3.10, triggered on pull_request and push to main — per contracts/ci_workflow_interface.md lint and typecheck job specs

**Checkpoint**: Lint and typecheck CI checks appear on PRs. Violations produce GitHub annotations with file paths and line numbers (FR-001, FR-002, FR-003, FR-004).

---

## Phase 3: User Story 2 — Automated Test Execution on Pull Requests (Priority: P2)

**Goal**: Add a test matrix job to the CI workflow that runs unit, contract, and integration tests across Python 3.10–3.13, with coverage reporting.

**Independent Test**: Open a PR with a failing test, verify the `test` check fails. Verify coverage is reported.

### Implementation for User Story 2

- [x] T004 [US2] Add `test` job to `.github/workflows/ci.yml` with Python version matrix [3.10, 3.11, 3.12, 3.13], `needs: [lint, typecheck]`, separate steps for unit tests (with --cov), contract tests, and integration tests, plus codecov upload on Python 3.12 — per contracts/ci_workflow_interface.md test job spec (FR-005, FR-006, FR-007, FR-008, FR-009, FR-010)

**Checkpoint**: PR checks show lint, typecheck, and test (4 Python versions) status checks. Coverage is reported. All existing 502 tests pass in CI.

---

## Phase 4: User Story 3 — Local Development Tooling and Guides (Priority: P3)

**Goal**: Deliver a Makefile for local quality checks and contributing/development guides for onboarding new contributors.

**Independent Test**: Clone the repo, follow CONTRIBUTING.md to set up the environment, run `make check` — all checks pass locally.

### Implementation for User Story 3

- [x] T005 [P] [US3] Create `Makefile` at repository root with all 14 targets (help, install, lint, typecheck, format, test-unit, test-contract, test-integration, test-e2e, test, check, coverage, build, clean) using `uv run` — per contracts/makefile_interface.md
- [x] T006 [P] [US3] Create `CONTRIBUTING.md` at repository root with: prerequisites (Python 3.10+, Make, uv), development setup (`git clone` → `make install` → `make check`), branch naming convention, commit message format (Conventional Commits per constitution), PR process, required CI checks, code style (ruff + mypy strict), and reference to DEVELOPMENT.md (FR-012)
- [x] T007 [P] [US3] Create `DEVELOPMENT.md` at repository root with: repository structure diagram (src/kuberay_sdk/ modules), key modules and responsibilities (models/, services/, platform/, errors.py), test categories (unit/contract/integration/e2e) with how to run each, how to add new tests, how to build and preview docs locally, and Makefile target reference table (FR-013)

**Checkpoint**: `make help` shows all targets. `make check` runs lint + typecheck + tests. CONTRIBUTING.md and DEVELOPMENT.md guide new contributors (FR-011, FR-014, SC-002, SC-005).

---

## Phase 5: User Story 4 — Automated Release and Package Publishing (Priority: P4)

**Goal**: Deliver a release pipeline that builds, validates, releases, and publishes the package to PyPI when a version tag is pushed.

**Independent Test**: Push a version tag matching pyproject.toml version. Verify GitHub Release is created with auto-generated notes and package is published to PyPI.

### Implementation for User Story 4

- [x] T008 [P] [US4] Create `.github/release.yml` (NOT a workflow — release note category configuration) with categories: Breaking Changes, Features, Bug Fixes, Documentation, Dependencies, Other Changes, and exclude label `skip-changelog` — per contracts/ci_workflow_interface.md release notes configuration
- [x] T009 [US4] Create `.github/workflows/release.yml` with 5 jobs: quality-gate (lint+typecheck+test on Python 3.12), build (python -m build, upload artifact), version-check (tag version vs pyproject.toml version), create-release (softprops/action-gh-release@v2 with generate_release_notes and dist/* files), publish-pypi (pypa/gh-action-pypi-publish@release/v1 with environment: pypi and id-token: write) — per contracts/ci_workflow_interface.md release.yml spec (FR-015, FR-016, FR-017, FR-018, FR-019)

**Checkpoint**: Version tag push triggers release pipeline. Version mismatch is caught. GitHub Release created with categorized PR notes. Package published to PyPI via OIDC (SC-003, SC-007).

---

## Phase 6: User Story 5 — End-to-End Test Execution in CI (Priority: P5)

**Goal**: Deliver e2e tests and a CI workflow that provisions a Kind cluster, installs KubeRay operator, runs SDK e2e tests, and cleans up.

**Independent Test**: Trigger the e2e workflow manually via workflow_dispatch. Verify Kind cluster is created, KubeRay operator installed, tests run, and cluster is deleted.

### Implementation for User Story 5

- [x] T010 [US5] Create `tests/e2e/test_smoke.py` with smoke tests that validate core SDK operations: create a RayCluster, verify it reaches ready state, submit a RayJob and verify completion, deploy a RayService and verify it becomes serving — using the SDK's KubeRayClient against the real cluster (FR-021)
- [x] T011 [US5] Update `tests/e2e/conftest.py` with e2e fixtures: cluster readiness check (wait for KubeRay operator deployment), namespace creation/cleanup per test session, SDK client initialization with in-cluster kubeconfig
- [x] T012 [US5] Create `.github/workflows/e2e.yml` with workflow_dispatch and push to release/* triggers, single job: Kind cluster creation (helm/kind-action@v1), KubeRay operator installation via Helm, operator readiness wait, pytest tests/e2e/ execution, and kind delete cluster (if: always) — per contracts/ci_workflow_interface.md e2e.yml spec (FR-020, FR-022, FR-023)

**Checkpoint**: E2E workflow provisions cluster, runs SDK smoke tests, and cleans up. Manual trigger works from Actions tab (SC-006).

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, cross-story integration checks, and quickstart scenario verification

- [x] T013 Verify `make check` output matches CI pipeline: lint, typecheck, and test results should be equivalent to what ci.yml runs
- [x] T014 Validate quickstart.md scenarios: local check (Scenario 1), individual targets (Scenario 2), PR quality gate (Scenario 3), lint violation detection (Scenario 4), new contributor onboarding (Scenario 8)
- [x] T015 Verify all 3 GitHub Actions workflow files (ci.yml, release.yml, e2e.yml) have valid YAML syntax and correct trigger configurations

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **US1 (Phase 2)**: Depends on Setup. Creates ci.yml — MUST complete before US2 (same file).
- **US2 (Phase 3)**: Depends on US1 (adds test job to ci.yml created by US1). Depends on T002 (pytest-cov dependency).
- **US3 (Phase 4)**: Depends on Setup. Independent of US1/US2 but benefits from CI being in place for parity validation.
- **US4 (Phase 5)**: Depends on Setup. Independent of other stories (release.yml is a separate file).
- **US5 (Phase 6)**: Depends on T001 (tests/e2e/ directory). Independent of other stories.
- **Polish (Phase 7)**: Depends on all user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Can start after Setup — standalone, delivers the MVP
- **US2 (P2)**: Depends on US1 (extends ci.yml) — sequential after US1
- **US3 (P3)**: Can start after Setup — fully independent from US1/US2
- **US4 (P4)**: Can start after Setup — fully independent (separate workflow file)
- **US5 (P5)**: Can start after T001 — fully independent (separate workflow file + test directory)

### Within Each User Story

- US1: Single task (T003)
- US2: Single task (T004), depends on T003 (same file)
- US3: All 3 tasks (T005–T007) are independent and marked [P]
- US4: T008 (config) and T009 (workflow) — T008 is [P], T009 sequential (references T008's config)
- US5: T010 → T011 → T012 sequential (tests → fixtures → workflow)

### Parallel Opportunities

- **Phase 1**: T001 and T002 can run in parallel (different files)
- **Phase 4 (US3)**: All 3 tasks (T005, T006, T007) can run in parallel (different files)
- **Cross-story**: After Setup completes, US1, US3, US4, and US5 can all start in parallel. US2 must wait for US1.

---

## Parallel Example: After Setup

```bash
# Launch independent user stories in parallel:
Task: "Create ci.yml with lint and typecheck jobs" (T003 — US1)
Task: "Create Makefile" (T005 — US3)
Task: "Create CONTRIBUTING.md" (T006 — US3)
Task: "Create DEVELOPMENT.md" (T007 — US3)
Task: "Create .github/release.yml config" (T008 — US4)
Task: "Create .github/workflows/release.yml" (T009 — US4)
Task: "Create tests/e2e/test_smoke.py" (T010 — US5)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: User Story 1 (T003)
3. **STOP and VALIDATE**: Open a PR, verify lint and typecheck checks appear
4. Contributors get fast feedback on code quality violations

### Incremental Delivery

1. Complete Setup → Dependencies ready
2. Add US1 (Code Quality CI) → **MVP delivered** — linting and type checking on every PR
3. Add US2 (Test CI) → Full test matrix on every PR with coverage
4. Add US3 (Makefile + Guides) → Contributors can validate locally and onboard easily
5. Add US4 (Release Pipeline) → Automated publishing to PyPI on tag push
6. Add US5 (E2E Tests) → Real cluster validation in CI
7. Polish → Final validation, parity checks, quickstart scenarios

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup together
2. Once Setup is done:
   - Developer A: US1 (CI lint+typecheck, 1 task) then US2 (CI testing, 1 task)
   - Developer B: US3 (Makefile + guides, 3 tasks)
   - Developer C: US4 (Release pipeline, 2 tasks) then US5 (E2E, 3 tasks)
3. All stories integrate independently via separate files

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- No test tasks generated — CI pipeline validation serves as the test suite
- ci.yml is shared between US1 (lint+typecheck) and US2 (test job), requiring sequential execution
- release.yml and e2e.yml are separate workflow files, enabling parallel development
- Existing docs.yml workflow is unchanged
- Commit after each task or logical group
- Stop at any checkpoint to validate the story independently
