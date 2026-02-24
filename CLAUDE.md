# kuberay-sdk Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-23

## Active Technologies
- Python 3.10+ (documentation tooling), Markdown (content) + MkDocs (1.6.x), Material for MkDocs (9.7.x), mkdocstrings[python] (1.0.x), mkdocs-gen-files (0.6.x), mkdocs-literate-nav (0.6.x), mkdocs-section-index (0.3.x), mkdocs-jupyter (0.25.x), mike (2.1.x) (002-automated-docs-site)
- N/A (static site — HTML files on GitHub Pages) (002-automated-docs-site)
- Python 3.10+ (existing project requirement) + GitHub Actions, ruff (linting), mypy (type checking), pytest (testing), uv (dependency management), hatchling (build backend) (003-ci-release-contributing)
- Python 3.10+ + `kubernetes` (official Python client), `kube-authkit` (auth delegation), `httpx` (Dashboard REST), `pydantic` (model validation), `PyYAML` (config files), `click` (CLI framework — new dependency) (004-sdk-ux-enhancements)
- `~/.kuberay/config.yaml` (user-level YAML config file — new) (004-sdk-ux-enhancements)
- Python 3.10+ (example scripts), Markdown (documentation) + MkDocs (1.6.x), Material for MkDocs (9.7.x), ruff (syntax validation of examples) (004-sdk-ux-enhancements)
- N/A (static documentation files) (004-sdk-ux-enhancements)

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
- 004-sdk-ux-enhancements: Added Python 3.10+ (example scripts), Markdown (documentation) + MkDocs (1.6.x), Material for MkDocs (9.7.x), ruff (syntax validation of examples)
- 004-sdk-ux-enhancements: Added Python 3.10+ + `kubernetes` (official Python client), `kube-authkit` (auth delegation), `httpx` (Dashboard REST), `pydantic` (model validation), `PyYAML` (config files), `click` (CLI framework — new dependency)
- 003-ci-release-contributing: Added Python 3.10+ (existing project requirement) + GitHub Actions, ruff (linting), mypy (type checking), pytest (testing), uv (dependency management), hatchling (build backend)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
