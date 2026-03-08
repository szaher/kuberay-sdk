# Data Model: Rich Display & Notebook Integration

**Feature**: 005-rich-display-output
**Date**: 2026-03-08

## Entities

### DisplayBackend (Protocol)

The core abstraction that determines how output is rendered. Defined as a `typing.Protocol` — implementations are structurally typed (no inheritance required).

**Fields/Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `render_table` | `(headers: list[str], rows: list[list[str]], state_column: int \| None = None) -> None` | Render tabular data to the current output. `state_column` indicates which column index contains resource state values for color coding. |
| `render_progress` | `(timeout: float) -> ProgressContext` | Return a context manager that displays a progress bar. The returned object must support `update(status: ProgressStatus)` and clean up on exit. |
| `render_log_line` | `(line: str, source: str \| None = None) -> None` | Render a single log line with optional source label and log-level color coding. |
| `render_html_card` | `(data: dict[str, str], actions: list[ActionDef] \| None = None) -> str \| None` | Return an HTML string for notebook display, or None if not applicable. |

### ProgressContext (Protocol)

Returned by `DisplayBackend.render_progress()`. Used as a context manager wrapping a wait loop.

**Fields/Methods**:

| Method | Signature | Description |
|--------|-----------|-------------|
| `update` | `(status: ProgressStatus) -> None` | Update the progress display with new status. |
| `complete` | `(message: str) -> None` | Mark progress as successfully completed. |
| `fail` | `(message: str) -> None` | Mark progress as failed. |
| `__enter__` | `() -> ProgressContext` | Enter context, start display. |
| `__exit__` | `(exc_type, exc_val, exc_tb) -> bool` | Clean up display, handle KeyboardInterrupt (cancel + re-raise). Returns False (never swallows exceptions). |

### StateColorScheme

A mapping from resource state strings to color identifiers. Used by all backends for consistent color coding.

**State Groups**:

| Group | States | Color |
|-------|--------|-------|
| Success | `RUNNING`, `READY`, `SUCCEEDED`, `COMPLETE` | Green |
| Transitional | `CREATING`, `PENDING`, `SCALING`, `INITIALIZING`, `SUBMITTING` | Yellow |
| Failure | `FAILED`, `ERROR`, `CRASHED`, `TIMEOUT`, `UNKNOWN` | Red |

**Representation**: A frozen dict or module-level constant mapping `str -> str` (state -> color name). Color names are abstract (`"green"`, `"yellow"`, `"red"`) — each backend translates to its own color system (ANSI codes for terminal, CSS classes for HTML).

### ActionDef

Defines an action button for notebook display.

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `label` | `str` | Button display text (e.g., "Delete", "Scale Workers") |
| `callback` | `Callable[[], None]` | Function to execute when clicked |
| `destructive` | `bool` | If True, requires confirmation before executing |
| `icon` | `str \| None` | Optional icon identifier (e.g., "trash", "resize") |

### ProgressStatus (existing — from feature 004)

Already defined in `src/kuberay_sdk/models/progress.py`. No changes needed.

**Fields** (reference):

| Field | Type | Description |
|-------|------|-------------|
| `state` | `str` | Current resource state |
| `elapsed_seconds` | `float` | Time since operation started |
| `message` | `str` | Human-readable status message |
| `metadata` | `dict[str, Any]` | Additional key-value data |

## Relationships

```text
DisplayBackend (Protocol)
  ├── PlainBackend         (fallback, always available)
  ├── RichBackend          (requires `rich`)
  └── NotebookBackend      (requires `ipywidgets`)

DisplayBackend.render_progress() → ProgressContext (Protocol)
  ├── PlainProgressContext  (prints text updates)
  ├── RichProgressContext   (rich.progress.Progress wrapper)
  └── NotebookProgressContext (ipywidgets.FloatProgress wrapper)

StateColorScheme → used by all backends for consistent state coloring

ActionDef → used by NotebookBackend.render_html_card() for action buttons

ProgressStatus (existing) → consumed by ProgressContext.update()
```

## State Transitions

No new state machines. The `StateColorScheme` maps existing resource states (already defined in cluster/job/service models) to colors. Resource state transitions are unchanged.

## Validation Rules

- `StateColorScheme` must contain entries for all states defined in `ClusterStatus`, `JobStatus`, and `ServiceStatus` models. Unknown states default to the "Transitional" (yellow) color group.
- `ActionDef.callback` must not be None.
- `ActionDef.label` must be non-empty.
- `DisplayBackend` detection runs once per session and caches the result. The `KUBERAY_DISPLAY` env var overrides detection.
