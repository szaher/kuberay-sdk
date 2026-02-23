# Feature Specification: CI Pipeline, Release Automation & Developer Guides

**Feature Branch**: `003-ci-release-contributing`
**Created**: 2026-02-23
**Status**: Draft
**Input**: User description: "add CI jobs for linting, tests, integration tests, e2e tests. Add Make file to run these locally if needed. Add Contributing guide and local development guide. add release CI and publishing to pypi CI jobs"

## User Scenarios & Testing

### User Story 1 - Automated Code Quality Checks on Pull Requests (Priority: P1)

As a contributor, I want every pull request to automatically run linting and type checking so that code quality standards are enforced consistently and I get fast feedback on style or type errors before review.

**Why this priority**: Code quality gates are the foundation of a healthy CI pipeline. The project constitution mandates that PRs MUST pass linting and type checking in CI. This is the minimum viable CI and the first gate every PR must pass.

**Independent Test**: Open a PR with a linting violation (e.g., unused import) and verify the CI check fails with a clear error message. Fix the violation and verify the check passes.

**Acceptance Scenarios**:

1. **Given** a contributor opens a PR against `main`, **When** the PR contains a linting violation, **Then** the CI check fails and reports the specific violation with file and line number.
2. **Given** a contributor opens a PR against `main`, **When** the PR contains a type error, **Then** the CI check fails and reports the type error with file and line number.
3. **Given** a contributor opens a PR with clean code, **When** the CI pipeline runs, **Then** both linting and type checking pass and the PR shows a green status.
4. **Given** a contributor pushes additional commits to an open PR, **When** the commits fix previously reported violations, **Then** the CI re-runs and passes.

---

### User Story 2 - Automated Test Execution on Pull Requests (Priority: P2)

As a contributor, I want every pull request to automatically run unit tests, contract tests, and integration tests so that I know my changes don't break existing functionality before the PR is merged.

**Why this priority**: Tests catch regressions and validate behavior changes. Running tests automatically on every PR prevents broken code from reaching the main branch. This builds on US1 (quality gates) to provide a complete PR validation pipeline.

**Independent Test**: Open a PR that introduces a failing test and verify the CI check fails. Fix the test and verify the check passes. Verify that unit, contract, and integration test results are reported separately.

**Acceptance Scenarios**:

1. **Given** a contributor opens a PR, **When** the CI pipeline runs, **Then** unit tests, contract tests, and integration tests each run as distinct steps with separate pass/fail status.
2. **Given** a PR introduces a breaking change that causes a unit test to fail, **When** the CI pipeline runs, **Then** the unit test step fails and the specific test failure is reported.
3. **Given** a PR introduces a breaking change that causes a contract test to fail, **When** the CI pipeline runs, **Then** the contract test step fails and the specific test failure is reported.
4. **Given** all tests pass, **When** the CI pipeline completes, **Then** the PR shows a green status for the testing check.
5. **Given** the CI pipeline runs tests, **When** tests complete, **Then** test coverage is measured and reported.
6. **Given** the project supports multiple Python versions, **When** the CI pipeline runs, **Then** tests execute against all supported Python versions and results are reported per version.

---

### User Story 3 - Local Development Tooling and Guides (Priority: P3)

As a new contributor, I want a single command to run all quality checks locally and a step-by-step guide to set up my development environment so that I can contribute effectively without needing to understand the CI configuration or project internals.

**Why this priority**: Developer experience directly impacts contribution velocity. A command runner provides a consistent interface for common tasks, and a contributing guide reduces onboarding friction. This is independent of CI (US1/US2) but complements it by enabling local validation before pushing.

**Independent Test**: Clone the repository, follow the contributing guide to set up a development environment, and run the command runner to verify all checks pass locally. A new contributor can go from clone to running tests without external help.

**Acceptance Scenarios**:

1. **Given** a developer clones the repository, **When** they follow the contributing guide, **Then** they can set up a working development environment and run all tests within the documented steps.
2. **Given** a developer has a working development environment, **When** they run a single command, **Then** all linting, type checking, and tests execute locally with clear pass/fail output.
3. **Given** a developer wants to run only linting, **When** they run the linting command, **Then** only linting checks execute.
4. **Given** a developer wants to run only unit tests, **When** they run the unit test command, **Then** only unit tests execute.
5. **Given** a developer reads the contributing guide, **When** they want to submit a PR, **Then** the guide explains the branch naming convention, commit message format, PR process, and required CI checks.
6. **Given** a developer reads the local development guide, **When** they want to understand the project structure, **Then** the guide explains the directory layout, key modules, and how to run common development tasks.

---

### User Story 4 - Automated Release and Package Publishing (Priority: P4)

As a maintainer, I want releases to be automatically built and published to the Python package registry when a version tag is pushed so that end users always have access to the latest stable version without manual publishing steps.

**Why this priority**: Automated publishing eliminates human error in the release process and ensures reproducible builds. This depends on a working CI pipeline (US1/US2) and follows the constitution's requirement for semantic versioning.

**Independent Test**: Create a version tag (e.g., `v0.1.0`), push it, and verify the package is built, all checks pass, and the package is published. Verify the published package can be installed by end users.

**Acceptance Scenarios**:

1. **Given** a maintainer pushes a version tag matching `v*.*.*`, **When** the release pipeline runs, **Then** the package is built and published to the package registry.
2. **Given** a maintainer pushes a version tag, **When** the release pipeline runs, **Then** a release artifact is created with auto-generated release notes summarizing changes since the last release.
3. **Given** the package is published, **When** a user installs the package, **Then** they receive the version matching the tag.
4. **Given** a version tag is pushed, **When** any quality check or test fails, **Then** the package is NOT published and the maintainer is notified of the failure.
5. **Given** a release pipeline is triggered, **When** the tag version does not match the version declared in project metadata, **Then** the pipeline fails with a clear version mismatch error.

---

### User Story 5 - End-to-End Test Execution in CI (Priority: P5)

As a maintainer, I want end-to-end tests to run against a real Kubernetes cluster in CI so that I can validate the SDK works correctly with actual KubeRay infrastructure before releasing.

**Why this priority**: E2E tests provide the highest confidence that the SDK works in production-like conditions. However, they are slower and more complex to set up (requiring a Kubernetes cluster), so they are lower priority than the faster test suites. They run on a separate trigger (manual or release branches) rather than every PR.

**Independent Test**: Trigger the e2e test pipeline and verify it provisions a test cluster, installs the KubeRay operator, runs e2e tests, and reports results. Verify the cluster is cleaned up after tests complete.

**Acceptance Scenarios**:

1. **Given** the e2e pipeline is triggered, **When** it runs, **Then** a temporary Kubernetes cluster with the KubeRay operator is provisioned for testing.
2. **Given** a test cluster is running, **When** e2e tests execute, **Then** they validate core SDK operations (create cluster, submit job, deploy service) against the real cluster.
3. **Given** e2e tests complete (pass or fail), **When** the pipeline finishes, **Then** the test cluster is cleaned up and no orphaned resources remain.
4. **Given** a maintainer wants to run e2e tests, **When** they trigger the pipeline manually, **Then** e2e tests run on demand without requiring a code change or tag push.

---

### Edge Cases

- What happens when CI runs on a fork? Fork PRs should run quality checks and tests but must not have access to publishing credentials or secrets.
- What happens when a maintainer pushes a tag that doesn't match the package version in project metadata? The release pipeline should fail with a clear version mismatch error before attempting to publish.
- What happens when package publishing fails (e.g., version already exists in the registry)? The pipeline should report the error clearly and not retry automatically.
- What happens when e2e cluster provisioning fails? The pipeline should fail fast with a clear error and ensure no orphaned resources remain.
- What happens when a contributor runs command runner tasks without the development dependencies installed? The commands should fail with a message indicating which dependencies are missing.
- What happens when tests pass on one Python version but fail on another? The CI pipeline should test against all supported Python versions and report per-version results, with any single failure blocking the PR.

## Requirements

### Functional Requirements

**CI — Code Quality (US1)**

- **FR-001**: The CI pipeline MUST run linting checks on every pull request targeting the main branch.
- **FR-002**: The CI pipeline MUST run type checking on every pull request targeting the main branch.
- **FR-003**: The CI pipeline MUST report specific file paths and line numbers for any violations.
- **FR-004**: The CI pipeline MUST block PR merging when linting or type checking fails (via required status checks).

**CI — Testing (US2)**

- **FR-005**: The CI pipeline MUST run unit tests on every pull request.
- **FR-006**: The CI pipeline MUST run contract tests on every pull request.
- **FR-007**: The CI pipeline MUST run integration tests on every pull request.
- **FR-008**: The CI pipeline MUST report unit, contract, and integration test results as distinguishable categories.
- **FR-009**: The CI pipeline MUST test against all supported Python versions (3.10, 3.11, 3.12, 3.13).
- **FR-010**: The CI pipeline MUST measure and report test coverage.

**Local Development Tooling (US3)**

- **FR-011**: A command runner MUST provide individual commands for: linting, type checking, unit tests, contract tests, integration tests, all tests, and all checks combined.
- **FR-012**: A contributing guide MUST document: development environment setup, branch naming convention, commit message format (Conventional Commits per project constitution), PR process, and required CI checks.
- **FR-013**: A local development guide MUST document: repository structure, key modules, how to run tests, and how to add new tests.
- **FR-014**: The command runner MUST work with only Python and Make installed (standard on Linux/macOS).

**Release & Publishing (US4)**

- **FR-015**: The release pipeline MUST build and publish the package to the Python package registry when a version tag (`v*.*.*`) is pushed.
- **FR-016**: The release pipeline MUST create a release artifact with auto-generated release notes when a version tag is pushed.
- **FR-017**: The release pipeline MUST verify all quality checks and tests pass before publishing.
- **FR-018**: The release pipeline MUST validate that the tag version matches the package version declared in project metadata.
- **FR-019**: The release pipeline MUST use secure, non-secret-based authentication for package publishing (trusted publishers / OIDC).

**E2E Testing (US5)**

- **FR-020**: The e2e test pipeline MUST provision a temporary Kubernetes cluster with the KubeRay operator installed.
- **FR-021**: The e2e test pipeline MUST run SDK end-to-end tests validating core operations (cluster creation, job submission, service deployment).
- **FR-022**: The e2e test pipeline MUST clean up the test cluster after tests complete, regardless of test outcome.
- **FR-023**: The e2e test pipeline MUST be triggerable manually and optionally on release branches.

## Assumptions

- The project already has a working test suite organized into unit, contract, and integration test directories.
- The project already has linting and type checking configuration in `pyproject.toml`.
- Fork PRs have read-only access and cannot trigger publishing or access repository secrets.
- E2E tests use an ephemeral in-CI Kubernetes cluster for cluster provisioning, as this is the standard approach for Kubernetes SDK testing.
- The Makefile is the command runner (as specified by the user). It is standard on Linux/macOS; Windows contributors can use WSL or equivalent.
- Test coverage thresholds are not enforced initially but coverage is measured and reported for visibility.
- The existing documentation CI workflow is unchanged by this feature — documentation CI remains separate.
- The project follows semantic versioning as mandated by the project constitution.
- The contributing guide (CONTRIBUTING.md) at the repository root is the canonical contributor onboarding document. It may reference the documentation site's developer guide for detailed information.
- Conventional Commits format is documented in CONTRIBUTING.md but not enforced via CI in this iteration. CI enforcement (e.g., PR title validation) is deferred to a future iteration.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of pull requests are validated by linting, type checking, and test execution before merge is possible.
- **SC-002**: A new contributor can go from cloning the repository to running all checks locally by following the contributing guide, in a self-service manner without external help.
- **SC-003**: Package releases are published to the registry within one automated pipeline run after a version tag is pushed, with zero manual steps required.
- **SC-004**: All quality checks and tests run across all 4 supported Python versions (3.10, 3.11, 3.12, 3.13) on every PR.
- **SC-005**: The command runner provides at least 7 distinct commands for individual development tasks (lint, type check, unit tests, contract tests, integration tests, all tests, all checks).
- **SC-006**: E2E tests validate core SDK operations (cluster creation, job submission, service deployment) against a real Kubernetes cluster in CI.
- **SC-007**: Failed quality checks, test failures, or version mismatches prevent package publishing with clear error messages.
