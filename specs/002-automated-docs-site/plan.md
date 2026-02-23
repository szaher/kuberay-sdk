# Implementation Plan: Automated Documentation Site

**Branch**: `002-automated-docs-site` | **Date**: 2026-02-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-automated-docs-site/spec.md`

## Summary

Build an automated documentation site for the kuberay-sdk using MkDocs with Material theme. The site has two audience-specific sections (User Guide for data scientists/ML engineers, Developer Guide for contributors), auto-generated API reference from Python docstrings via mkdocstrings, rendered Jupyter notebook examples, versioned documentation via mike, and a GitHub Actions CI pipeline for automated deployment to GitHub Pages. Guide pages are hand-authored markdown; API reference pages are auto-generated from source code on every build using static analysis (griffe) — no runtime dependencies required.

## Technical Context

**Language/Version**: Python 3.10+ (documentation tooling), Markdown (content)
**Primary Dependencies**: MkDocs (1.6.x), Material for MkDocs (9.7.x), mkdocstrings[python] (1.0.x), mkdocs-gen-files (0.6.x), mkdocs-literate-nav (0.6.x), mkdocs-section-index (0.3.x), mkdocs-jupyter (0.25.x), mike (2.1.x)
**Storage**: N/A (static site — HTML files on GitHub Pages)
**Testing**: `mkdocs build --strict` (build validation), link checking via strict mode warnings-as-errors
**Target Platform**: Static HTML site served via GitHub Pages, viewable on desktop and tablet browsers
**Project Type**: Documentation site (static site generator configuration + markdown content)
**Performance Goals**: Build completes in under 60 seconds (SC-003); search returns results for 90% of SDK terms (SC-005)
**Constraints**: API reference generation must work without importing the SDK module (static analysis only); docs dependencies must not require SDK runtime dependencies
**Scale/Scope**: ~25 hand-authored guide pages, ~23 auto-generated API reference pages, 7 example pages (6 scripts + 1 notebook), versioned deployment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Check

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. API-First Design | PASS | This feature documents the existing API. The build contract is defined in `contracts/build_interface.md` before implementation. No new SDK API surface. |
| II. User-Centric Abstraction | PASS | Documentation is organized by user task (Cluster Management, Job Submission), not by internal module structure. User Guide is separate from Developer Guide. K8s complexity is hidden in user-facing guides. |
| III. Progressive Disclosure | PASS | Getting Started and Quick Start pages require no K8s knowledge. Advanced Configuration, OpenShift, and Developer Guide pages are separate sections for power users. |
| IV. Test-First (NON-NEGOTIABLE) | PASS | Build validation (`mkdocs build --strict`) serves as the test suite for documentation. Broken links, missing API entries, and invalid config are caught at build time. The build script and configuration will be validated before content is written. |
| V. Simplicity & YAGNI | PASS | Uses established tooling (MkDocs + Material) — no custom theme, no custom plugins. Dependencies are minimal and each justified (see research.md). No features "for future use." |

### Post-Design Re-check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. API-First Design | PASS | Build interface contract defined. API reference auto-generated from existing docstrings. |
| II. User-Centric Abstraction | PASS | Site structure is task-oriented. Code examples are copy-pasteable. |
| III. Progressive Disclosure | PASS | 4 sections with clear audience targeting. Beginners start at Getting Started, experts go to API Reference or Developer Guide. |
| IV. Test-First | PASS | `mkdocs build --strict` validates all content. CI pipeline ensures validation on every PR. |
| V. Simplicity & YAGNI | PASS | 8 documentation dependencies, all widely-used MkDocs ecosystem packages. No custom code beyond the standard `gen_ref_pages.py` script. |

### No violations. Gate PASSED.

## Project Structure

### Documentation (this feature)

```text
specs/002-automated-docs-site/
├── plan.md              # This file
├── research.md          # Phase 0 output (tooling research)
├── data-model.md        # Phase 1 output (content model)
├── quickstart.md        # Phase 1 output (build/deploy scenarios)
├── contracts/
│   └── build_interface.md  # Build CLI and site structure contract
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
docs/
├── index.md                        # Landing page
├── user-guide/
│   ├── getting-started/
│   │   ├── installation.md         # Prerequisites, pip install, auth setup
│   │   └── quick-start.md          # 3 core operations (cluster, job, service)
│   ├── cluster-management.md       # Create, scale, monitor, delete clusters
│   ├── job-submission.md           # Standalone RayJob + Dashboard submission
│   ├── ray-serve.md                # Service creation, updates, endpoints
│   ├── storage-runtime-env.md      # PVCs, pip/conda, env vars
│   ├── openshift.md                # Hardware profiles, Kueue, Routes
│   ├── experiment-tracking.md      # MLflow integration
│   ├── async-usage.md              # AsyncKubeRayClient patterns
│   ├── error-handling.md           # Error hierarchy, recovery patterns
│   └── configuration.md            # SDKConfig fields, namespace, auth
├── developer-guide/
│   ├── architecture.md             # Module structure, Handle pattern, CRD flow
│   ├── development-setup.md        # Clone, venv, install, run tests
│   ├── testing.md                  # Unit/contract/integration, fixtures
│   ├── code-style.md               # Ruff, mypy, docstring conventions
│   └── contributing.md             # Branch naming, commits, PR process
├── examples/
│   ├── index.md                    # Examples gallery (listing with descriptions)
│   ├── cluster-basics.md           # Wrapper for examples/cluster_basics.py
│   ├── job-submission.md           # Wrapper for examples/job_submission.py
│   ├── advanced-config.md          # Wrapper for examples/advanced_config.py
│   ├── async-client.md             # Wrapper for examples/async_client.py
│   ├── ray-serve-deployment.md     # Wrapper for examples/ray_serve_deployment.py
│   └── openshift-features.md       # Wrapper for examples/openshift_features.py
├── changelog.md                    # What's New / changelog for current version
├── 404.md                          # Custom 404 page
└── overrides/                      # Material theme overrides (if any)

scripts/
└── gen_ref_pages.py                # API reference page auto-generation script

mkdocs.yml                          # MkDocs configuration (site root)

.github/
└── workflows/
    └── docs.yml                    # GitHub Actions CI for docs build + deploy
```

**Note**: The `reference/` section is NOT a directory in `docs/` — it is auto-generated at build time by `gen_ref_pages.py` via the `mkdocs-gen-files` plugin. The script walks `src/kuberay_sdk/` and creates virtual markdown pages containing `:::` directives that mkdocstrings resolves to API reference HTML.

**Note**: The notebook `examples/mnist_training.ipynb` is referenced directly in `mkdocs.yml` nav — `mkdocs-jupyter` renders it as a page without a wrapper markdown file.

**Structure Decision**: Single project layout with documentation added alongside the existing SDK source. Documentation files live in `docs/` at the repository root, configuration in `mkdocs.yml`, and the build script in `scripts/`. This keeps documentation close to the code it documents while maintaining a clean separation from `src/` and `tests/`.

## Complexity Tracking

> No constitution violations. No complexity justifications needed.

| Aspect | Decision | Justification |
|--------|----------|---------------|
| 8 docs dependencies | Added to `[docs]` optional group | Each serves a distinct, required function (see research.md). No overlap. Industry-standard MkDocs ecosystem packages. |
| `gen_ref_pages.py` script | Custom build script | Standard mkdocstrings recipe (documented in official mkdocstrings docs). ~30 lines. Enables fully automatic API reference discovery. |
| Example wrapper pages | Hand-authored `.md` files wrapping `.py` scripts | Each wrapper includes a brief description and uses `pymdownx.snippets` to include the script source. Enables context/annotations around raw code. |
