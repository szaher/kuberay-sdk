# Implementation Plan: SDK UX & Developer Experience Enhancements

**Branch**: `004-sdk-ux-enhancements` | **Date**: 2026-02-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-sdk-ux-enhancements/spec.md`

## Summary

This feature enhances the kuberay-sdk with 13 improvements across error handling, progress feedback, configuration, developer ergonomics, dry-run mode, presets, compound operations, retry jitter, a CLI tool, capability discovery, and documentation. The approach modifies existing modules (errors, retry, config, client, handles, `__init__`) and adds new modules (presets, CLI, capabilities). All changes extend the existing architecture without breaking the public API.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: `kubernetes` (official Python client), `kube-authkit` (auth delegation), `httpx` (Dashboard REST), `pydantic` (model validation), `PyYAML` (config files), `click` (CLI framework — new dependency)
**Storage**: `~/.kuberay/config.yaml` (user-level YAML config file — new)
**Testing**: pytest (unit, contract, integration, e2e)
**Target Platform**: Any environment with kubeconfig access to a KubeRay-enabled Kubernetes cluster
**Project Type**: Python library + CLI tool
**Performance Goals**: N/A (SDK operations are bound by Kubernetes API latency)
**Constraints**: Must not break existing public API. All new parameters must have defaults preserving current behavior.
**Scale/Scope**: 13 user stories, ~20 modified/new source files, ~15 new test files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. API-First Design** | PASS | All new public methods and classes defined as contracts before implementation. New types (`ProgressStatus`, `Preset`, `ClusterCapabilities`, `DryRunResult`) documented in data-model.md. |
| **II. User-Centric Abstraction** | PASS | Core goal of this feature. Remediation hints use Ray/ML terms. Presets hide K8s complexity. CLI provides non-Python access. |
| **III. Progressive Disclosure** | PASS | All new features are additive/optional — `dry_run`, `progress_callback`, `preset` are keyword-only parameters with defaults. Config file is opt-in. |
| **IV. Test-First (NON-NEGOTIABLE)** | PASS | TDD approach: tests written before implementation for each user story. |
| **V. Simplicity & YAGNI** | PASS | Each feature addresses a concrete current use case documented in the spec. No speculative abstractions. Click dependency justified by CLI requirement (US10). |
| **Tech Stack: Dependencies** | REQUIRES JUSTIFICATION | Adding `click` as new dependency for CLI (see Complexity Tracking). |
| **Tech Stack: Python 3.10+** | PASS | All code targets Python 3.10+. |
| **Development Workflow** | PASS | PR-based, tests required, ruff+mypy in CI, docstrings for public API. |

## Project Structure

### Documentation (this feature)

```text
specs/004-sdk-ux-enhancements/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── errors.md        # Remediation attribute contract
│   ├── progress.md      # Progress callback contract
│   ├── config.md        # Config file + env var contract
│   ├── handles.md       # Handle repr contract
│   ├── dry-run.md       # Dry-run mode contract
│   ├── presets.md       # Preset configurations contract
│   ├── cli.md           # CLI tool contract
│   └── capabilities.md  # Capability discovery contract
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/kuberay_sdk/
├── __init__.py              # MODIFY: Add convenience re-exports (US5)
├── errors.py                # MODIFY: Add remediation attribute (US1)
├── retry.py                 # MODIFY: Add jitter to backoff (US9)
├── config.py                # MODIFY: Add config file + env var loading (US3)
├── client.py                # MODIFY: Add dry_run, preset, compound ops, progress_callback (US2,6,7,8)
├── async_client.py          # MODIFY: Add dry_run, progress_callback (US2,6)
├── presets.py               # NEW: Preset configurations (US7)
├── capabilities.py          # NEW: Capability discovery (US11)
├── models/
│   ├── __init__.py          # MODIFY: Re-export new models
│   ├── progress.py          # NEW: ProgressStatus model (US2)
│   └── capabilities.py     # NEW: ClusterCapabilities model (US11)
├── cli/                     # NEW: CLI tool (US10)
│   ├── __init__.py
│   ├── main.py              # Click app entry point
│   ├── cluster.py           # kuberay cluster subcommands
│   ├── job.py               # kuberay job subcommands
│   ├── service.py           # kuberay service subcommands
│   └── formatters.py        # Table/JSON output formatting
└── services/                # Existing — no structural changes

tests/
├── unit/
│   ├── test_errors.py       # MODIFY: Test remediation attribute
│   ├── test_retry.py        # MODIFY: Test jitter
│   ├── test_config_file.py  # NEW: Config file loading tests
│   ├── test_handles_repr.py # NEW: Handle __repr__ tests
│   ├── test_imports.py      # NEW: Convenience import tests
│   ├── test_dry_run.py      # NEW: Dry-run mode tests
│   ├── test_presets.py      # NEW: Preset configuration tests
│   ├── test_compound.py     # NEW: Compound operations tests
│   ├── test_progress.py     # NEW: Progress callback tests
│   ├── test_capabilities.py # NEW: Capability discovery tests
│   └── test_cli.py          # NEW: CLI tests
├── contract/                # Existing — extend as needed
└── docs/
    ├── test_troubleshooting.py # NEW: Verify troubleshooting doc exists
    └── test_migration.py       # NEW: Verify migration guide exists

docs/
├── user-guide/
│   ├── troubleshooting.md   # NEW: Troubleshooting guide (US12)
│   └── migration.md         # NEW: Migration guide (US13)
```

**Structure Decision**: Extends existing single-project structure. New `cli/` subpackage under `src/kuberay_sdk/` for the CLI tool. New model files for new entities. Documentation files added under existing `docs/` MkDocs structure.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New dependency: `click` | CLI tool (US10) requires a CLI framework. Click is the most mature, stable option with extensive ecosystem support. | stdlib `argparse` was considered but lacks: subcommand groups, auto-help generation, shell completion, and produces significantly more boilerplate. |
