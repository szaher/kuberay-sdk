# Implementation Plan: Comprehensive Documentation for New SDK Features (US14)

**Branch**: `004-sdk-ux-enhancements` | **Date**: 2026-02-24 | **Spec**: [spec.md](spec.md)
**Input**: US14 amendment to feature specification — documentation for 8 new SDK capabilities.

**Note**: This plan covers **only US14** (Comprehensive Documentation for New Features). The prior plan covered US1–US13 implementation, which is complete (62 tasks, 692 tests passing). This is a documentation-only plan — no new source code.

## Summary

All 8 new SDK capabilities (dry-run mode, presets, progress callbacks, CLI tool, capability discovery, compound operations, config file/env var support, convenience re-exports) shipped without documentation updates. This plan covers updating the README, creating a new user guide page, writing standalone example scripts, and adding a CLI command reference page to the docs site. All examples must be standalone (no live cluster required) and include version annotations per the clarification session.

## Technical Context

**Language/Version**: Python 3.10+ (example scripts), Markdown (documentation)
**Primary Dependencies**: MkDocs (1.6.x), Material for MkDocs (9.7.x), ruff (syntax validation of examples)
**Storage**: N/A (static documentation files)
**Testing**: `ruff check examples/` for example syntax validation (SC-014)
**Target Platform**: GitHub Pages (docs site), pip-installed package (README bundled)
**Project Type**: Documentation (no new source code)
**Performance Goals**: N/A
**Constraints**: Must follow existing doc site style and MkDocs conventions; examples must be standalone (clarification session)
**Scale/Scope**: 8 features to document across 3 documentation targets (README, user guide, example scripts) + 1 CLI reference page

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. API-First Design | PASS | "Every public function and class MUST include docstrings with usage examples." US14 documents the public API usage of 8 new features. No new API surface introduced. |
| II. User-Centric Abstraction | PASS | Documentation must hide Kubernetes complexity. Examples use SDK abstractions (presets, dry-run, config files), not raw K8s manifests. |
| III. Progressive Disclosure | PASS | "Documentation MUST clearly separate 'Getting Started' from 'Advanced Configuration'." The README covers quick-start snippets; the user guide page provides detailed usage. |
| IV. Test-First | PASS | Example scripts are validated by `ruff check examples/` (SC-014). No implementation code to TDD — this is documentation only. |
| V. Simplicity & YAGNI | PASS | Each example script covers one feature with minimal code. No speculative documentation beyond the 8 shipped features. |

All gates pass. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/004-sdk-ux-enhancements/
├── plan.md              # This file (US14 documentation plan)
├── research.md          # Phase 0 output (US14 addendum)
├── data-model.md        # Phase 1 output (documentation artifacts model)
├── quickstart.md        # Phase 1 output (already complete from prior plan)
├── contracts/           # Phase 1 output (documentation contracts)
│   └── documentation.md # New: documentation structure contract
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (documentation deliverables)

```text
# Files to CREATE
docs/user-guide/new-features.md              # New user guide page for 8 features
docs/user-guide/cli-reference.md             # CLI command reference page

examples/dry_run_preview.py                  # Standalone dry-run example
examples/presets_usage.py                    # Preset configuration example
examples/progress_callbacks.py               # Progress callback example
examples/cli_usage.sh                        # CLI tool usage example (shell script)
examples/capability_discovery.py             # Capability discovery example
examples/compound_operations.py              # Compound operation example
examples/config_and_env_vars.py              # Config file and env var example
examples/convenience_imports.py              # Top-level import example

# Files to MODIFY
README.md                                    # Add 8 new feature sections
mkdocs.yml                                   # Add nav entries for new pages
docs/examples/index.md                       # Add links to new example scripts

# Existing files (NO changes needed for US14)
docs/user-guide/configuration.md             # Already covers SDKConfig basics
docs/user-guide/error-handling.md            # Already covers error hierarchy
docs/user-guide/troubleshooting.md           # US12 deliverable
docs/user-guide/migration.md                 # US13 deliverable
```

**Structure Decision**: Documentation-only plan. No new source code directories. New files follow existing conventions: docs pages in `docs/user-guide/`, example scripts in `examples/`.

## Documentation Gap Analysis

### What EXISTS (pre-US14)

| Area | Coverage |
|------|----------|
| README | Core features: handle-based API, cluster/job/service CRUD, OpenShift, Kueue, async client, retry, auth delegation. **No mention** of dry-run, presets, progress callbacks, CLI, capabilities, compound ops, config file/env vars, convenience imports. |
| docs/user-guide/ | 12 pages covering: installation, quick-start, cluster management, job submission, Ray Serve, storage, OpenShift, experiment tracking, async usage, error handling, configuration, migration, troubleshooting. **None** cover the 8 new features. Configuration page covers `SDKConfig` constructor but NOT config files or env vars. |
| examples/ | 7 scripts: cluster_basics.py, job_submission.py, advanced_config.py, async_client.py, openshift_features.py, ray_serve_deployment.py, mnist_training.ipynb. **None** demonstrate the 8 new features. |
| docs site nav | No entries for CLI reference, new features guide, or new example scripts. |

### What US14 DELIVERS

| Deliverable | Requirement | Details |
|-------------|-------------|---------|
| README updates | FR-034 | 8 new sections with quick-start snippets, version annotations |
| User guide page | FR-034, clarification | New `docs/user-guide/new-features.md` page on MkDocs site |
| CLI reference page | FR-037, clarification | New `docs/user-guide/cli-reference.md` on MkDocs site |
| Example scripts | FR-035 | 8 standalone scripts (no live cluster) with inline comments |
| Config precedence docs | FR-036 | Precedence diagram + credential warning in README and user guide |
| Version annotations | FR-034, clarification | "Added in vX.Y.Z" badge on each new feature section |
| MkDocs nav updates | — | Add nav entries for new pages and examples |

## Implementation Phases

### Phase A: README Updates (FR-034, FR-036)

Add 8 new sections to `README.md` after the existing "Async Client" section. Each section includes:
- Feature heading with version annotation (e.g., `*Added in v0.2.0*`)
- 1-2 sentence description
- Runnable code snippet (standalone, using dry-run where applicable)
- For CLI: shell command examples with sample output
- Config precedence section with explicit `>` ordering and credential warning

Sections to add (in order):
1. **Convenience Imports** — `from kuberay_sdk import WorkerGroup, RuntimeEnv, StorageVolume`
2. **Configuration File & Environment Variables** — `~/.kuberay/config.yaml`, `KUBERAY_*` env vars, precedence order, credential warning
3. **Dry-Run Mode** — `create_cluster(..., dry_run=True)`, `result.to_yaml()`
4. **Presets** — `preset="dev"`, `list_presets()`
5. **Progress Callbacks** — `wait_until_ready(progress_callback=...)`
6. **Compound Operations** — `create_cluster_and_submit_job()`
7. **Capability Discovery** — `client.get_capabilities()`
8. **CLI Tool** — `kuberay cluster list`, link to full CLI reference

### Phase B: User Guide Page (FR-034, FR-036)

Create `docs/user-guide/new-features.md` with detailed documentation for each feature:
- Configuration options and defaults
- Complete usage examples
- Edge cases and error handling
- Cross-links to existing docs (configuration.md, error-handling.md)

Create `docs/user-guide/cli-reference.md` (FR-037) with:
- Full command tree (`kuberay cluster|job|service` subcommands)
- All options and flags per subcommand
- Output format examples (table and JSON)
- Configuration via flags, env vars, and config file

### Phase C: Example Scripts (FR-035, SC-014)

Create 8 standalone example scripts in `examples/`:

| Script | Feature | Standalone Strategy |
|--------|---------|---------------------|
| `convenience_imports.py` | Convenience re-exports | Import validation only, no cluster needed |
| `config_and_env_vars.py` | Config file/env vars | Write temp config file, set env vars, show precedence |
| `dry_run_preview.py` | Dry-run mode | `dry_run=True` returns manifest without cluster |
| `presets_usage.py` | Presets | `list_presets()` + `dry_run=True` with preset |
| `progress_callbacks.py` | Progress callbacks | Define callback, annotate cluster-required wait step |
| `compound_operations.py` | Compound operations | Annotate cluster-required step with comments |
| `capability_discovery.py` | Capability discovery | Annotate cluster-required step with comments |
| `cli_usage.sh` | CLI tool | Shell script with commands and `# Requires: live cluster` annotations |

Each script:
- Has a module-level docstring explaining the feature
- Uses `if __name__ == "__main__":` guard
- Runs standalone where possible (dry-run, config, imports)
- Annotates cluster-dependent steps with `# NOTE: Requires a running KubeRay cluster`
- Passes `ruff check` (SC-014)

### Phase D: MkDocs Nav & Index Updates

Update `mkdocs.yml` nav to add:
- `user-guide/new-features.md` (under User Guide, after Configuration)
- `user-guide/cli-reference.md` (under User Guide, after New Features)
- New example entries under Examples section

Update `docs/examples/index.md` to link to the new example scripts.

### Phase E: Validation

- Run `ruff check examples/` to verify all example scripts pass syntax validation (SC-014)
- Verify all 8 features documented in README with code snippets (SC-013)
- Verify no broken cross-links in MkDocs pages
- Verify version annotations present on all new feature sections

## Complexity Tracking

No constitution violations. This is a documentation-only plan with no new abstractions, patterns, or dependencies.
