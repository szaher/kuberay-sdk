# Research: Automated Documentation Site

**Feature**: 002-automated-docs-site
**Date**: 2026-02-23

## Decision 1: Documentation Framework

**Decision**: MkDocs with Material for MkDocs theme (v9.7.x)

**Rationale**:
- Markdown-native — low friction for hand-authored guide pages.
- Material theme provides best-in-class responsive design, dark mode, built-in search (lunr.js), content tabs, code copy buttons, and admonitions out of the box.
- Consistent with the kuberay-sdk dependency ecosystem: Pydantic, httpx, and FastAPI all use MkDocs + Material.
- Simple single-file configuration (`mkdocs.yml`) and single-command build (`mkdocs build`).
- Active community, well-documented, stable (v9.7.x is LTS through November 2026).

**Alternatives considered**:
- **Sphinx + furo/pydata-sphinx-theme**: More mature autodoc but steeper learning curve (rST), slower builds, harder Jupyter integration. Better for legacy Python projects (NumPy, Django, Flask) but overkill for a new SDK.
- **Docusaurus**: React-based, poor Python API reference auto-generation. Wrong ecosystem fit.

## Decision 2: API Reference Auto-Generation

**Decision**: mkdocstrings[python] (v1.0.x) with griffe (static analysis)

**Rationale**:
- Auto-generates API reference from Python docstrings and type annotations.
- Uses griffe for static analysis — does NOT require importing the module, meaning:
  - No side effects from imports during build.
  - No need for runtime dependencies (kubernetes, kube-authkit) on the build machine.
  - Safe for CI environments.
- Supports Google docstring style (matching the SDK's existing conventions).
- Cross-links between classes, methods, and types.
- Shows method signatures, parameter types, defaults, return types, raised exceptions, and embedded usage examples.

**Alternatives considered**:
- **Sphinx autodoc**: More mature but requires importing the module (dynamic analysis). Would need all runtime dependencies installed during build.

## Decision 3: API Reference Page Auto-Discovery

**Decision**: mkdocs-gen-files + mkdocs-literate-nav + mkdocs-section-index

**Rationale**:
- `mkdocs-gen-files` runs a Python script at build time that walks `src/kuberay_sdk/` and generates a virtual `.md` file for each module/class.
- `mkdocs-literate-nav` builds the navigation tree from the generated `SUMMARY.md` rather than hardcoding it in `mkdocs.yml`.
- `mkdocs-section-index` allows section index pages for clean URLs.
- Together, adding a new public module automatically includes it in the API reference on the next build — no manual nav updates needed.

**Alternatives considered**:
- **mkdocs-api-autonav**: Single plugin replacing all three, but less widely documented and fewer customization options.
- **Manual nav entries**: Would require updating `mkdocs.yml` every time a module is added or renamed. Violates the "automated" requirement.

## Decision 4: Jupyter Notebook Rendering

**Decision**: mkdocs-jupyter (v0.25.x)

**Rationale**:
- Renders `.ipynb` files directly as MkDocs pages during build.
- Preserves code cells, outputs, and markdown cells.
- `include_source: true` adds a download link for the original `.ipynb` file.
- `execute: false` — notebooks are not re-executed during build (they contain outputs from real cluster runs with real credentials).
- Simple configuration — reference `.ipynb` files in nav as if they were `.md` files.

**Alternatives considered**:
- **nbsphinx / myst-nb**: Sphinx ecosystem. More setup friction, worse integration with Material theme.
- **Manual nbconvert + markdown**: Too much manual work, no auto-discovery.

## Decision 5: Versioned Documentation

**Decision**: mike (v2.1.x)

**Rationale**:
- Deploys each version to a subdirectory on the `gh-pages` branch (e.g., `/0.1/`, `/0.2/`, `/latest/`).
- Native integration with Material for MkDocs — adds a version selector dropdown in the header.
- Frozen HTML — old versions never need to be regenerated.
- Alias support (`latest` always points to the current stable release, `dev` for unreleased).
- Simple CLI: `mike deploy --push --update-aliases 0.1 latest`.

**Alternatives considered**:
- **sphinx-multiversion**: Sphinx ecosystem, more complex, harder to configure.
- **ReadTheDocs versioning**: Locks into ReadTheDocs hosting. The project should stay hosting-agnostic.
- **Manual subdirectory deployment**: Too much manual work, error-prone.

## Decision 6: Hosting Platform

**Decision**: GitHub Pages (via `gh-pages` branch)

**Rationale**:
- The project repository is already on GitHub.
- Free for public repositories.
- Integrates directly with `mike` and `mkdocs gh-deploy`.
- CI workflow with GitHub Actions is straightforward.
- Custom domain support if needed later.

**Alternatives considered**:
- **ReadTheDocs**: Good for open-source but locks into their build system and has occasional availability issues. MkDocs + mike on GitHub Pages provides equivalent features with more control.
- **Netlify/Vercel**: Overkill for a static docs site. No meaningful advantage over GitHub Pages.

## Decision 7: Link Validation

**Decision**: `mkdocs build --strict` mode

**Rationale**:
- MkDocs strict mode treats warnings as errors.
- Catches broken cross-links, missing pages, and orphaned references.
- Built-in, no additional plugin needed.
- Can be combined with a dedicated link checker in CI for external links.

## Decision 8: Python Script Rendering in Examples

**Decision**: Include `.py` files in docs via code fences with `pymdownx.snippets` or direct inclusion in hand-authored example pages

**Rationale**:
- Python example scripts should be rendered as syntax-highlighted pages (per spec clarification).
- Each script can be included in a hand-authored wrapper page that provides context and a download link.
- `pymdownx.snippets` can include external files directly into markdown.
- Alternative: reference `.py` files directly in nav with mkdocs-jupyter (supports Jupytext `.py` files).

## Technology Stack Summary

| Component | Tool | Version |
|-----------|------|---------|
| Site generator | MkDocs | 1.6.x |
| Theme | Material for MkDocs | 9.7.x |
| API reference | mkdocstrings[python] | 1.0.x |
| Static analysis | griffe | 1.6.x |
| Page auto-generation | mkdocs-gen-files | 0.6.x |
| Nav auto-generation | mkdocs-literate-nav | 0.6.x |
| Section indexing | mkdocs-section-index | 0.3.x |
| Notebook rendering | mkdocs-jupyter | 0.25.x |
| Versioning | mike | 2.1.x |
| Hosting | GitHub Pages | N/A |
| CI | GitHub Actions | N/A |
| Link validation | mkdocs --strict | N/A |
