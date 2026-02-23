# Data Model: Automated Documentation Site

**Feature**: 002-automated-docs-site
**Date**: 2026-02-23

## Entities

This feature does not involve a traditional database or runtime data model. The "data" is the documentation content itself — markdown files, Python source files, Jupyter notebooks, and configuration. The entities below describe the content model that the build system processes.

### 1. Documentation Page

A single page of documentation content.

| Field | Type | Description |
|-------|------|-------------|
| path | string | Relative file path within `docs/` (e.g., `user-guide/cluster-management.md`) |
| title | string | Page title extracted from first `# heading` |
| section | enum | Top-level section: `user-guide`, `developer-guide`, `api-reference`, `examples` |
| format | enum | Content format: `markdown`, `notebook`, `python-script`, `auto-generated` |
| nav_position | int | Order within section (determined by `mkdocs.yml` nav or SUMMARY.md) |

**Validation rules**:
- Path must be unique within the docs directory.
- Title must be non-empty.
- All pages must belong to exactly one section.

### 2. API Reference Entry

An auto-generated documentation entry for a public Python symbol.

| Field | Type | Description |
|-------|------|-------------|
| qualified_name | string | Fully qualified Python name (e.g., `kuberay_sdk.KubeRayClient.create_cluster`) |
| symbol_type | enum | `class`, `method`, `function`, `constant`, `enum` |
| module | string | Parent module path (e.g., `kuberay_sdk.client`) |
| signature | string | Method/function signature with type annotations |
| docstring | string | Extracted docstring text |
| return_type | string | Return type annotation (if applicable) |
| exceptions | list[string] | Exception types that can be raised |
| cross_links | list[string] | Qualified names of related symbols to link to |

**Validation rules**:
- Every symbol exported from `kuberay_sdk.__init__` must have an entry.
- Symbols without docstrings generate a build warning.

### 3. Example

A runnable code sample included in the examples gallery.

| Field | Type | Description |
|-------|------|-------------|
| file_path | string | Path relative to repository root (e.g., `examples/cluster_basics.py`) |
| title | string | Derived from module docstring first line or notebook first markdown cell |
| description | string | One-line summary for gallery listing |
| format | enum | `python-script` or `jupyter-notebook` |
| download_url | string | Relative URL to download the original file |

**Validation rules**:
- File must exist in the `examples/` directory.
- Python scripts must have a module-level docstring (first line used as title).
- Notebooks must have a markdown cell as the first cell (first heading used as title).

### 4. Version

A labeled documentation snapshot tied to a release.

| Field | Type | Description |
|-------|------|-------------|
| version_label | string | Semantic version label (e.g., `0.1`, `0.2`, `dev`) |
| git_tag | string | Associated git tag (e.g., `v0.1.0`), or `HEAD` for dev |
| aliases | list[string] | URL aliases (e.g., `latest`, `dev`) |
| is_default | bool | Whether this version is shown by default when visiting the site |
| deploy_path | string | URL path prefix (e.g., `/0.1/`, `/latest/`) |

**Validation rules**:
- Exactly one version must have `is_default = true`.
- The `latest` alias must always exist and point to the most recent stable release.
- The `dev` alias points to the current main branch.

### 5. Build Configuration

The central configuration controlling the docs build.

| Field | Type | Description |
|-------|------|-------------|
| site_name | string | Documentation site title |
| site_url | string | Published site URL |
| repo_url | string | Source repository URL |
| theme | object | Material theme configuration (palette, features, icons) |
| plugins | list[object] | Ordered list of MkDocs plugins and their settings |
| nav | list[object] | Navigation tree (hand-authored sections + auto-generated API reference) |
| markdown_extensions | list[string] | Enabled markdown extensions (syntax highlighting, admonitions, etc.) |
| version_provider | string | Versioning backend (mike) |

**Validation rules**:
- Configuration must be valid YAML parseable by MkDocs.
- All referenced paths in `nav` must resolve to existing files or auto-generated pages.
- `mkdocs build --strict` must complete without errors.

## Relationships

```text
Build Configuration
    ├── Documentation Page (1:many)
    │   ├── API Reference Entry (auto-generated, 1:many)
    │   └── Example (rendered from examples/, 1:many)
    └── Version (deployed via mike, 1:many)
```

- A Build Configuration produces many Documentation Pages.
- API Reference Entries are auto-generated Documentation Pages (format = `auto-generated`).
- Examples are Documentation Pages (format = `python-script` or `jupyter-notebook`).
- Each Version is a frozen snapshot of all Documentation Pages at a point in time.
