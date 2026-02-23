# Implementation Plan: CI Pipeline, Release Automation & Developer Guides

**Branch**: `003-ci-release-contributing` | **Date**: 2026-02-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-ci-release-contributing/spec.md`

## Summary

Add CI workflows for code quality (linting, type checking), multi-version test execution, automated PyPI publishing via OIDC trusted publishers, and Kubernetes e2e testing. Provide a Makefile as a local command runner and a CONTRIBUTING.md guide for developer onboarding.

## Technical Context

**Language/Version**: Python 3.10+ (existing project requirement)
**Primary Dependencies**: GitHub Actions, ruff (linting), mypy (type checking), pytest (testing), uv (dependency management), hatchling (build backend)
**Storage**: N/A
**Testing**: pytest with directory-based separation (tests/unit/, tests/contract/, tests/integration/, tests/e2e/)
**Target Platform**: GitHub Actions runners (ubuntu-latest), local development on Linux/macOS
**Project Type**: Python library (pip-installable SDK)
**Performance Goals**: CI pipeline completes lint+typecheck in under 2 minutes; full test matrix in under 10 minutes
**Constraints**: Makefile must work with only Python and Make installed; PyPI publishing must use OIDC (no stored secrets)
**Scale/Scope**: 4 supported Python versions (3.10–3.13), 3 CI workflow files, 1 Makefile, 2 documentation files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. API-First Design | N/A | CI/tooling feature — no public API changes |
| II. User-Centric Abstraction | PASS | Makefile abstracts CI commands; CONTRIBUTING.md guides new contributors without K8s knowledge |
| III. Progressive Disclosure | PASS | Basic `make check` for common use; individual targets for advanced use |
| IV. Test-First (NON-NEGOTIABLE) | PASS | CI enforces test execution on every PR; e2e tests validate real cluster behavior |
| V. Simplicity & YAGNI | PASS | Minimal workflow files; no extra abstractions (tox, nox, invoke); Makefile wraps existing tools |
| Development Workflow | PASS | PRs validated by lint+typecheck+tests; Conventional Commits documented in CONTRIBUTING.md |

**Post-design re-check**: All gates still pass. No constitution violations.

## Project Structure

### Documentation (this feature)

```text
specs/003-ci-release-contributing/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── makefile_interface.md
│   └── ci_workflow_interface.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
.github/
├── release.yml                     # Release note category configuration (not a workflow)
└── workflows/
    ├── ci.yml                      # PR quality gates: lint, typecheck, test matrix
    ├── docs.yml                    # (existing) Documentation build/deploy
    ├── release.yml                 # Tag-triggered: quality gate, build, release, publish
    └── e2e.yml                     # Manual/release-branch: Kind + KubeRay e2e tests

Makefile                            # Local development command runner
CONTRIBUTING.md                     # Contributor onboarding guide
DEVELOPMENT.md                      # Local development guide (project structure, running tests)

tests/
├── unit/                           # (existing) Unit tests
├── contract/                       # (existing) Contract tests
├── integration/                    # (existing) Integration tests
└── e2e/                            # (new) End-to-end tests against real cluster
    ├── __init__.py
    ├── conftest.py                 # E2E fixtures (cluster readiness, cleanup)
    └── test_smoke.py               # Smoke test: create cluster, submit job, deploy service
```

**Structure Decision**: This feature adds CI/tooling files at the repository root level and under `.github/`. The existing `src/` and `tests/` structure is unchanged except for the new `tests/e2e/` directory. No new source code packages are created.

## Architecture

### CI Workflow Design

```
ci.yml (on: pull_request to main, push to main)
├── job: lint (single Python version — 3.10)
│   ├── ruff check --output-format=github src/ tests/
│   └── ruff format --check src/ tests/
├── job: typecheck (single Python version — 3.10)
│   └── mypy src/
└── job: test (matrix: [3.10, 3.11, 3.12, 3.13], needs: [lint, typecheck])
    ├── pytest tests/unit/ --cov=src/kuberay_sdk --cov-report=xml
    ├── pytest tests/contract/ -v
    ├── pytest tests/integration/ -v
    └── Upload coverage to codecov

release.yml (on: push tags v*.*.*)
├── job: quality-gate (reuse lint + typecheck + test)
├── job: build (python -m build, upload dist/ as artifact)
├── job: version-check (validate tag matches pyproject.toml version)
├── job: create-release (needs: [quality-gate, build, version-check])
│   └── softprops/action-gh-release@v2 with generate_release_notes
└── job: publish-pypi (needs: [create-release])
    ├── environment: pypi
    ├── permissions: id-token: write
    └── pypa/gh-action-pypi-publish@release/v1

e2e.yml (on: workflow_dispatch, push to release/*)
└── job: e2e
    ├── helm/kind-action@v1 (create cluster)
    ├── helm install kuberay-operator
    ├── kubectl wait for operator ready
    ├── pytest tests/e2e/ -v --timeout=300
    └── kind delete cluster (always)
```

### Makefile Design

All targets use `uv run` to execute in the project's managed virtual environment:

| Target | Description | CI Equivalent |
|--------|-------------|---------------|
| `help` | Self-documenting default target | — |
| `install` | `uv sync --all-extras` | — |
| `lint` | `ruff check` + `ruff format --check` | ci.yml lint job |
| `typecheck` | `mypy src/` | ci.yml typecheck job |
| `format` | `ruff format` + `ruff check --fix` | — (local only) |
| `test-unit` | `pytest tests/unit/` | ci.yml test job (unit step) |
| `test-contract` | `pytest tests/contract/` | ci.yml test job (contract step) |
| `test-integration` | `pytest tests/integration/` | ci.yml test job (integration step) |
| `test-e2e` | `pytest tests/e2e/` | e2e.yml |
| `test` | unit + contract + integration | ci.yml test job |
| `check` | lint + typecheck + test | Full ci.yml |
| `coverage` | pytest with --cov + HTML report | ci.yml coverage upload |
| `build` | `python -m build` | release.yml build job |
| `clean` | Remove build artifacts | — |

### Documentation Files

**CONTRIBUTING.md** (repo root): Quick-start for contributors. Covers:
- Prerequisites (Python 3.10+, Make, uv)
- Development setup (`git clone` → `make install` → `make check`)
- Branch naming convention
- Commit message format (Conventional Commits per constitution)
- PR process and required CI checks
- Code style (ruff + mypy strict)
- Reference to DEVELOPMENT.md for project internals

**DEVELOPMENT.md** (repo root): Detailed local development guide. Covers:
- Repository structure diagram
- Key modules and their responsibilities
- How to run individual test categories
- How to add new tests
- How to build and preview documentation locally
- Makefile target reference

## Key Technical Decisions

1. **uv over pip**: Project already uses uv (evidenced by `uv.lock`). Faster installs, reproducible environments.
2. **Directory-based test separation over markers**: Tests are already organized by directory. Simpler and more reliable than `-m` markers.
3. **Lint/typecheck on single Python version**: ruff and mypy produce identical results across Python versions when `target-version` is pinned. Saves CI time.
4. **Separate release workflow**: Tag-triggered workflow avoids complex conditional logic in the main CI workflow.
5. **Kind over k3d/Minikube**: De facto standard for ephemeral K8s clusters in CI. Runs in Docker natively.
6. **`softprops/action-gh-release` over manual `gh` CLI**: Declarative configuration, built-in support for auto-generated notes.
7. **OIDC trusted publishing over API tokens**: No stored secrets, short-lived tokens, PyPA recommended.

## Complexity Tracking

No constitution violations. No complexity justifications needed.
