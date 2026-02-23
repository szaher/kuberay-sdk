# kuberay-sdk Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-23

## Active Technologies
- Python 3.10+ (documentation tooling), Markdown (content) + MkDocs (1.6.x), Material for MkDocs (9.7.x), mkdocstrings[python] (1.0.x), mkdocs-gen-files (0.6.x), mkdocs-literate-nav (0.6.x), mkdocs-section-index (0.3.x), mkdocs-jupyter (0.25.x), mike (2.1.x) (002-automated-docs-site)
- N/A (static site — HTML files on GitHub Pages) (002-automated-docs-site)

- Python 3.9+ + `kubernetes` (official Python client), `kube-authkit` (v0.4.0+, auth delegation), `httpx` (Dashboard REST API calls, sync+async), `pydantic` (model validation) (001-kuberay-python-sdk)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.9+: Follow standard conventions

## Recent Changes
- 002-automated-docs-site: Added Python 3.10+ (documentation tooling), Markdown (content) + MkDocs (1.6.x), Material for MkDocs (9.7.x), mkdocstrings[python] (1.0.x), mkdocs-gen-files (0.6.x), mkdocs-literate-nav (0.6.x), mkdocs-section-index (0.3.x), mkdocs-jupyter (0.25.x), mike (2.1.x)

- 001-kuberay-python-sdk: Added Python 3.9+ + `kubernetes` (official Python client), `kube-authkit` (v0.4.0+, auth delegation), `httpx` (Dashboard REST API calls, sync+async), `pydantic` (model validation)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
