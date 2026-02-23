# Research: CI Pipeline, Release Automation & Developer Guides

**Date**: 2026-02-23
**Feature**: 003-ci-release-contributing

## 1. GitHub Actions Python CI Pattern

**Decision**: Multi-job workflow with `lint` and `typecheck` as fast gatekeeping jobs, followed by a `test` job with Python version matrix (3.10–3.13). Use `uv` for dependency management (project already has `uv.lock`).

**Rationale**: Separate jobs give independent pass/fail signals in PR checks. Lint and typecheck run on a single Python version (results are version-independent when `target-version` is pinned). Matrix testing on the `test` job covers all supported versions. `uv` is faster than pip and already in use.

**Alternatives considered**:
- Single monolithic job: no separate pass/fail signals, slower feedback
- tox: extra abstraction layer; GitHub Actions matrix already handles version isolation
- pre-commit.ci: doesn't replace full CI pipeline with test matrix
- pip with caching: slower than uv; project already has uv.lock

## 2. PyPI Trusted Publishing (OIDC)

**Decision**: Use PyPI Trusted Publishing with `pypa/gh-action-pypi-publish@release/v1`. Configure a pending publisher on PyPI. Use a dedicated `pypi` GitHub environment with manual approval protection. Separate build and publish jobs — publish job gets `id-token: write` permission only.

**Rationale**: OIDC eliminates long-lived API tokens. Short-lived tokens (15-minute expiry) are issued per-workflow-run. This is the officially recommended approach by PyPI and PyPA. The `pypi` environment with required reviewers adds a human approval gate. FR-019 explicitly requires non-secret-based authentication.

**Alternatives considered**:
- PyPI API token as GitHub secret: long-lived, can be leaked, violates FR-019
- twine upload: lower-level; gh-action-pypi-publish wraps twine with OIDC + attestation
- TestPyPI for staging: complementary but not a replacement; can be added later

## 3. Kubernetes E2E Testing in CI

**Decision**: Use `helm/kind-action@v1` for ephemeral Kind cluster, install KubeRay operator via official Helm chart (`kuberay/kuberay-operator`). Separate workflow file (`e2e.yml`), manually triggerable via `workflow_dispatch`, optionally on release branches. Single Python version for e2e (3.12).

**Rationale**: Kind is the de facto standard for ephemeral K8s clusters in CI (runs in Docker, which GitHub Actions provides natively). `helm/kind-action` is the community standard action. KubeRay's official docs recommend Helm installation. E2E tests are slow (cluster provisioning + operator startup), so separate workflow avoids slowing every PR.

**Alternatives considered**:
- k3d: uses k3s which may differ from standard K8s behavior
- Minikube: heavier, requires VM driver, slower startup
- GKE/EKS real cluster: requires cloud credentials, costs money
- Running e2e on every PR: too slow and resource-intensive

## 4. Makefile Patterns

**Decision**: Makefile with `.PHONY` targets and self-documenting `help` as default goal. All targets use `uv run` to execute in the project's managed virtual environment. Targets: `help`, `install`, `lint`, `typecheck`, `format`, `test-unit`, `test-contract`, `test-integration`, `test-e2e`, `test`, `check`, `coverage`, `build`, `clean`.

**Rationale**: Make is ubiquitous on Linux/macOS (FR-014). `uv run` ensures correct virtual environment without manual activation. Self-documenting `help` target makes the Makefile discoverable. `check` target mirrors CI pipeline for local validation (SC-002).

**Alternatives considered**:
- Just/Task: not pre-installed; adds dependency
- Invoke: requires Python + invoke package (circular for initial setup)
- Shell scripts: less structured, no dependency tracking
- Poetry scripts: ties to specific package manager (project uses hatchling/uv)

## 5. GitHub Release Automation

**Decision**: Use `softprops/action-gh-release@v2` with `generate_release_notes: true`. Configure PR categorization via `.github/release.yml`. Create release before PyPI publish. Attach distribution artifacts (`.tar.gz`, `.whl`) to the GitHub Release.

**Rationale**: Most popular release action. GitHub's auto-generated release notes categorize merged PRs since the last tag. PR-based notes are more reliable than commit-based changelogs. `.github/release.yml` is a native GitHub feature for structured release notes. FR-016 requires auto-generated release notes.

**Alternatives considered**:
- Manual release creation: adds human step; spec requires full automation
- Conventional Commits changelog generator: more complex; PR-based notes more practical
- GitHub CLI (`gh release create`): more scripting, less declarative
