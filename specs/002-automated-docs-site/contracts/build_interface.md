# Build Interface Contract: Automated Documentation Site

**Feature**: 002-automated-docs-site
**Date**: 2026-02-23

## Overview

The documentation site exposes two primary interfaces: the **build CLI** (used by developers and CI) and the **site structure** (consumed by end users via a browser). This contract defines the expected behavior of both.

## 1. Build CLI Interface

### Commands

| Command | Description | Exit Code | Output |
|---------|------------|-----------|--------|
| `mkdocs serve` | Start local dev server with hot reload on `http://127.0.0.1:8000` | 0 on success | Continuous server log |
| `mkdocs build --strict` | Build static site to `site/` directory, fail on any warnings | 0 on success, 1 on error | Build log with error details |
| `mike deploy --push --update-aliases <version> <alias>` | Deploy versioned docs to `gh-pages` branch | 0 on success | Deploy log |
| `mike set-default --push <alias>` | Set default version for root URL redirect | 0 on success | Confirmation |
| `mike serve` | Serve all versions locally for testing | 0 on success | Continuous server log |

### Build Preconditions

- Python 3.10+ installed.
- Documentation dependencies installed (via `pip install -e ".[docs]"`).
- SDK source code available at `src/kuberay_sdk/` (for API reference generation).
- SDK runtime dependencies (kubernetes, kube-authkit, httpx, pydantic) are NOT required (griffe uses static analysis).

### Build Outputs

The `mkdocs build` command produces:

```text
site/
├── index.html                  # Landing page
├── user-guide/
│   ├── getting-started/
│   │   ├── installation/index.html
│   │   └── quick-start/index.html
│   ├── cluster-management/index.html
│   ├── job-submission/index.html
│   ├── ray-serve/index.html
│   ├── storage-runtime-env/index.html
│   ├── openshift/index.html
│   ├── experiment-tracking/index.html
│   ├── async-usage/index.html
│   ├── error-handling/index.html
│   └── configuration/index.html
├── developer-guide/
│   ├── architecture/index.html
│   ├── development-setup/index.html
│   ├── testing/index.html
│   ├── code-style/index.html
│   └── contributing/index.html
├── reference/                  # Auto-generated API reference
│   ├── kuberay_sdk/
│   │   ├── index.html          # Package overview
│   │   ├── client/index.html   # KubeRayClient, ClusterHandle, JobHandle, ServiceHandle
│   │   ├── async_client/index.html
│   │   ├── config/index.html
│   │   ├── errors/index.html
│   │   ├── models/
│   │   │   ├── index.html
│   │   │   ├── cluster/index.html
│   │   │   ├── job/index.html
│   │   │   ├── service/index.html
│   │   │   ├── storage/index.html
│   │   │   ├── runtime_env/index.html
│   │   │   └── common/index.html
│   │   ├── services/
│   │   │   └── ...
│   │   └── platform/
│   │       └── ...
│   └── SUMMARY.md              # Auto-generated nav (build artifact)
├── examples/
│   ├── index.html              # Gallery page
│   ├── cluster-basics/index.html
│   ├── job-submission/index.html
│   ├── advanced-config/index.html
│   ├── async-client/index.html
│   ├── ray-serve-deployment/index.html
│   ├── openshift-features/index.html
│   └── mnist-training/index.html   # Rendered notebook
├── search/
│   └── search_index.json      # Client-side search index
├── 404.html                   # Custom 404 page
└── assets/                    # CSS, JS, fonts
```

### Build Failure Conditions

The build MUST fail (exit code 1) with a descriptive error message when:

1. **Broken cross-link**: A markdown link or mkdocstrings reference points to a non-existent page or symbol.
2. **Missing nav target**: A file referenced in `mkdocs.yml` nav does not exist.
3. **Invalid YAML**: `mkdocs.yml` contains syntax errors.
4. **Plugin error**: Any plugin (mkdocstrings, mkdocs-jupyter, gen-files) raises an exception.

### Build Warning Conditions

The build SHOULD emit a warning (and fail in strict mode) when:

1. **Missing docstring**: A public class or method exported from `__init__.py` has no docstring.
2. **Orphan page**: A markdown file exists in `docs/` but is not referenced in the navigation.

## 2. Site Structure Contract

### Navigation Structure

```text
Top-level navigation bar:
├── User Guide          → /user-guide/getting-started/installation/
├── Developer Guide     → /developer-guide/architecture/
├── API Reference       → /reference/kuberay_sdk/
├── Examples            → /examples/
└── Version Selector    → dropdown: [0.1, 0.2, latest, dev]
```

### URL Pattern

All pages follow the pattern: `/{version}/{section}/{page}/`

Examples:
- `/latest/user-guide/cluster-management/`
- `/0.1/reference/kuberay_sdk/client/`
- `/dev/examples/mnist-training/`

### Search Contract

- **Input**: User types a query in the search bar.
- **Output**: Ranked list of matching pages with title, section, and highlighted excerpt.
- **Scope**: Search indexes all pages across the current version (not across versions).
- **Implementation**: Client-side via lunr.js search index (`search/search_index.json`).

### 404 Page Contract

- **Trigger**: User navigates to a non-existent URL.
- **Content**: Custom 404 page with:
  - "Page not found" message.
  - Link to the search feature.
  - Link to the version selector (in case the page exists in a different version).
  - Link to the site home page.

## 3. Dependency Installation Contract

Documentation dependencies MUST be installable via the `[docs]` optional dependency group in `pyproject.toml`:

```bash
pip install -e ".[docs]"
```

This installs all documentation tooling without requiring the SDK's runtime dependencies to be functional (API reference generation uses static analysis).
