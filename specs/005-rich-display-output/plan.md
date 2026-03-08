# Implementation Plan: Rich Display & Notebook Integration

**Branch**: `005-rich-display-output` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-rich-display-output/spec.md`

## Summary

Add optional rich terminal output and Jupyter notebook integration to the KubeRay SDK. When installed via `pip install kuberay-sdk[rich]` or `[notebook]`, the SDK auto-detects the runtime environment and renders progress bars, styled tables, colored logs, and interactive notebook widgets. Without the extras, all features degrade gracefully to plain text. The implementation introduces a `DisplayBackend` abstraction with three implementations (Rich/Notebook/Plain) and integrates with the existing `ProgressStatus` callback mechanism from feature 004.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**:
- Existing: `kubernetes`, `kube-authkit`, `httpx`, `pydantic`, `PyYAML`, `click`
- New (optional): `rich>=13.0` (terminal display), `ipywidgets>=8.0` (notebook widgets)
**Storage**: N/A
**Testing**: pytest, pytest-cov, ruff, mypy
**Target Platform**: Any environment with Python 3.10+ (terminals, Jupyter, JupyterLab, Colab, VS Code notebooks)
**Project Type**: Library (pip-installable SDK with optional extras)
**Performance Goals**: Display rendering must add <50ms overhead per operation; import time for optional deps must not slow core SDK startup
**Constraints**: Core SDK must never import `rich` or `ipywidgets` unconditionally; all optional imports must use try/except or lazy loading
**Scale/Scope**: 3 display backends, ~15 new source files, ~800 lines of new code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. API-First Design | PASS | Public API contracts defined first: `DisplayBackend` protocol, `display()` function signature, `_repr_html_()` on handles, `progress` parameter on wait methods |
| II. User-Centric Abstraction | PASS | Rich display hides rendering complexity; users see progress bars and styled tables without understanding display backends |
| III. Progressive Disclosure | PASS | Basic usage auto-activates; advanced control via `progress=False`, `KUBERAY_DISPLAY` env var, custom callbacks |
| IV. Test-First | PASS | TDD approach: tests for each backend, fallback behavior, environment detection |
| V. Simplicity & YAGNI | PASS | Three backends justified by three distinct environments (terminal, notebook, plain). No custom themes, no TUI dashboards. `display()` helper is a thin wrapper, not a framework |
| Tech Stack: Minimal deps | PASS | `rich` and `ipywidgets` are optional extras, not core dependencies. Zero impact on users who don't install them |
| Tech Stack: Python 3.10+ | PASS | Uses 3.10+ features (match statements not required; union types via `|` syntax already in codebase) |
| Dev Workflow: Tests before merge | PASS | All backends testable without live cluster; mock-based unit tests + notebook integration tests |

No violations. Gate passed.

## Project Structure

### Documentation (this feature)

```text
specs/005-rich-display-output/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research output
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 quickstart guide
├── contracts/           # Phase 1 public API contracts
│   ├── display-backend.md
│   ├── display-helper.md
│   └── handle-repr-html.md
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/kuberay_sdk/
├── __init__.py                    # Updated: add `display` to lazy imports
├── client.py                      # Updated: add `progress` param to wait methods, add `_repr_html_` to handles
├── display/                       # NEW: display subsystem
│   ├── __init__.py                # Public API: get_backend(), display()
│   ├── _detect.py                 # Environment detection (terminal/notebook/plain)
│   ├── _colors.py                 # StateColorScheme — state-to-color mapping
│   ├── _backend.py                # DisplayBackend protocol + PlainBackend
│   ├── _rich_backend.py           # RichBackend (terminal: tables, progress, logs)
│   ├── _notebook_backend.py       # NotebookBackend (Jupyter: HTML tables, ipywidgets, action buttons)
│   └── _log_renderer.py           # Log colorization for terminal and notebook
├── cli/
│   └── formatters.py              # Updated: delegate to display backend when rich is available

tests/
├── unit/
│   ├── display/
│   │   ├── test_detect.py         # Environment detection tests
│   │   ├── test_colors.py         # State color scheme tests
│   │   ├── test_plain_backend.py  # PlainBackend fallback tests
│   │   ├── test_rich_backend.py   # RichBackend tests (mocked rich)
│   │   ├── test_notebook_backend.py # NotebookBackend tests (mocked ipywidgets)
│   │   ├── test_display_helper.py # display() function tests
│   │   └── test_log_renderer.py   # Log colorization tests
│   └── test_handle_repr.py       # _repr_html_() tests on handles
├── integration/
│   └── test_notebook_rendering.py # Notebook integration tests (optional, needs jupyter)
```

**Structure Decision**: Follows the existing single-project layout under `src/kuberay_sdk/`. The new `display/` subpackage is a self-contained module that other parts of the SDK import from. All display modules are private (`_prefixed`) except the `__init__.py` public API. This keeps the public surface minimal per Constitution Principle V.

## Complexity Tracking

No violations to justify. All constitution gates passed.
