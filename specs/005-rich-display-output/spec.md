# Feature Specification: Rich Display & Notebook Integration

**Feature Branch**: `005-rich-display-output`
**Created**: 2026-03-07
**Status**: Draft
**Input**: User description: "Deeper integration with notebooks and rich terminal output — progress bars, beautified tables, buttons, colored logs and outputs in notebooks. Optional/extra package if needed."

## Clarifications

### Session 2026-03-08

- Q: Should rich display be opt-out (auto-activates when extra installed) or opt-in (user must explicitly enable)? → A: Opt-out — auto-activates when the extra is installed; users suppress with `progress=False` or `KUBERAY_DISPLAY=plain`.
- Q: Where should rich table rendering activate — CLI only, or also in the Python API? → A: CLI renders rich tables; notebook handles use `_repr_html_()`; a standalone `kuberay_sdk.display()` utility renders any resource list as a rich table in REPL/terminal. The Python API continues to return raw data objects.
- Q: How should multiple concurrent wait operations display progress bars? → A: Stacked — each concurrent wait gets its own independent progress bar, displayed vertically stacked.
- Q: What level of notebook compatibility should the spec target? → A: Full widget support (ipywidgets progress bars, action buttons) for Jupyter and JupyterLab. HTML-only fallback (styled tables, colored logs) for Colab and VS Code notebooks — interactive widgets may not work in those environments.
- Q: What should happen when a user hits Ctrl+C during an active progress bar? → A: Clean up the display (restore terminal state), cancel the underlying wait operation, and re-raise `KeyboardInterrupt` (standard Python behavior).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Rich Terminal Progress Bars (Priority: P1)

When a user calls a blocking wait operation (e.g., `wait_until_ready()`) from a terminal, they currently see no output unless they wire up a custom progress callback. The SDK should provide a built-in rich progress bar that activates automatically in terminal environments, showing elapsed time, current state, and a visual progress indicator.

**Why this priority**: Silent blocking is the top frustration point for terminal users. A visual progress bar immediately communicates that the SDK is working and how long the user has been waiting. This is the highest-impact improvement for the terminal experience.

**Independent Test**: Call `wait_until_ready()` from a terminal without any custom callback and verify a progress bar is displayed showing state transitions, elapsed time, and a spinner/bar animation.

**Acceptance Scenarios**:

1. **Given** a user calls a blocking wait operation from a terminal with the rich display extra installed, **When** the operation is in progress, **Then** a live progress bar is displayed showing the current resource state, elapsed time, and a visual animation.
2. **Given** a user calls a blocking wait operation without the rich display extra installed, **When** the operation is in progress, **Then** the behavior is unchanged from the current SDK (silent blocking or plain-text callback).
3. **Given** a user explicitly passes `progress=False` to a wait operation, **When** the operation runs, **Then** no progress bar is displayed regardless of whether the rich extra is installed.
4. **Given** a long-running wait operation completes successfully, **When** the progress bar finishes, **Then** it shows a completion indicator with total elapsed time.
5. **Given** a wait operation fails or times out, **When** the progress bar stops, **Then** it shows an error indicator with the failure reason and last known state.

---

### User Story 2 — Beautified Terminal Tables (Priority: P2)

When a user lists clusters, jobs, or services via the SDK or CLI, the current output is a plain-text aligned table with no visual separation between headers and rows, no color coding for resource states, and no borders. The SDK should render tables with styled headers, state-based color coding (e.g., green for RUNNING, red for FAILED, yellow for CREATING), and optional borders.

**Why this priority**: Table output is the most frequent visual interaction in both CLI and SDK usage. Beautified tables improve scanability and help users quickly identify resource states.

**Independent Test**: Call `client.list_clusters()` and print the result; verify the output renders with colored state indicators and visually distinct headers.

**Acceptance Scenarios**:

1. **Given** a user lists resources with the rich extra installed, **When** the results are displayed, **Then** the table includes styled headers, aligned columns, and color-coded state values.
2. **Given** resource states are displayed, **When** the state is a success state (e.g., RUNNING, READY, SUCCEEDED), **Then** it is rendered in green; warning states (CREATING, PENDING) in yellow; error states (FAILED, ERROR) in red.
3. **Given** a user lists resources without the rich extra installed, **When** the results are displayed, **Then** the current plain-text table format is used (graceful fallback).
4. **Given** a user is piping CLI output to a file or another command, **When** the output is not a TTY, **Then** color codes and special formatting are stripped automatically.

---

### User Story 3 — Notebook Interactive Widgets (Priority: P3)

When a user works in a Jupyter notebook, the SDK should provide notebook-native widgets: interactive progress bars (using ipywidgets), styled HTML tables for resource listings, and colored log output. These widgets should render inline in notebook cells and update live during long-running operations.

**Why this priority**: Data scientists are a primary audience and work predominantly in notebooks. Native notebook widgets provide a significantly better experience than plain text output.

**Independent Test**: In a Jupyter notebook, call `wait_until_ready()` and verify an ipywidgets progress bar renders inline and updates live. Call `list_clusters()` and verify an HTML-styled table is displayed.

**Acceptance Scenarios**:

1. **Given** a user calls a blocking wait operation in a Jupyter notebook, **When** the operation is in progress, **Then** an ipywidgets progress bar renders inline showing state, elapsed time, and percentage (if deterministic) or a pulsing animation (if indeterminate).
2. **Given** a user lists resources in a notebook, **When** the results are displayed, **Then** an HTML table with styled headers, alternating row colors, and color-coded states is rendered inline.
3. **Given** a user calls a wait operation in a notebook, **When** the state changes, **Then** the progress widget updates in-place without printing new lines.
4. **Given** the notebook widgets extra is not installed, **When** operations run in a notebook, **Then** the SDK falls back to plain text output (no errors raised).

---

### User Story 4 — Colored Log Output (Priority: P4)

When a user streams logs from a Ray cluster or job, the output is plain monochrome text. The SDK should provide colored log output that distinguishes log levels (INFO, WARNING, ERROR), timestamps, and source identifiers (head node vs. worker nodes) with different colors.

**Why this priority**: Log readability directly affects debugging speed. Color-coded logs help users quickly scan for errors and warnings in large log streams.

**Independent Test**: Stream logs from a job and verify that different log levels are rendered in distinct colors (INFO in default/white, WARNING in yellow, ERROR in red).

**Acceptance Scenarios**:

1. **Given** a user streams logs with the rich extra installed, **When** log entries are displayed, **Then** log levels are color-coded: INFO in default color, WARNING in yellow, ERROR/CRITICAL in red.
2. **Given** a user streams logs in a notebook, **When** log entries are displayed, **Then** they render as styled HTML with color-coded log levels.
3. **Given** a user streams logs without the rich extra, **When** log entries are displayed, **Then** plain text output is used (current behavior).
4. **Given** logs from multiple sources (head node, worker-0, worker-1), **When** displayed, **Then** each source is labeled and visually distinguishable.

---

### User Story 5 — Notebook Action Buttons (Priority: P5)

When a user inspects a resource handle in a Jupyter notebook, the SDK should display interactive action buttons alongside the resource summary. For example, a ClusterHandle displayed in a notebook cell should show buttons like "Delete", "Scale", "Open Dashboard" that trigger SDK operations when clicked.

**Why this priority**: Action buttons reduce the need to write boilerplate code for common follow-up actions. This is a convenience feature for notebook power users.

**Independent Test**: Display a ClusterHandle in a notebook cell and verify action buttons render. Click "Open Dashboard" and verify it triggers the dashboard URL display.

**Acceptance Scenarios**:

1. **Given** a user evaluates a ClusterHandle in a notebook cell, **When** the handle is displayed, **Then** it renders an HTML summary card with action buttons (e.g., "Delete", "Scale Workers", "Open Dashboard").
2. **Given** a user clicks an action button, **When** the action executes, **Then** the result is displayed in the notebook output and the resource summary updates.
3. **Given** a user evaluates a handle outside a notebook (terminal/REPL), **When** the handle is displayed, **Then** the standard `__repr__` text is used (no buttons).
4. **Given** a destructive action button (e.g., "Delete"), **When** clicked, **Then** a confirmation prompt is shown before executing.

---

### Edge Cases

- What happens when the terminal does not support ANSI color codes (e.g., a dumb terminal or CI/CD log viewer)?
- What happens when ipywidgets is installed but the notebook frontend does not support widgets (e.g., JupyterLab without the widget extension)?
- What happens when a progress bar is active and the user interrupts with Ctrl+C?
- What happens when multiple concurrent wait operations each try to display a progress bar?
- What happens when the rich extra is partially installed (e.g., `rich` is installed but `ipywidgets` is not)?
- What happens when a notebook cell is re-executed while an action button callback is still running?

## Requirements *(mandatory)*

### Functional Requirements

**Optional Package Structure**
- **FR-001**: The rich display features MUST be installable as an optional extra (e.g., `pip install kuberay-sdk[rich]` for terminal features, `pip install kuberay-sdk[notebook]` for notebook widgets, `pip install kuberay-sdk[display]` for both).
- **FR-002**: The core SDK MUST function correctly without the rich display extras installed — all rich features MUST degrade gracefully to plain text.
- **FR-003**: The SDK MUST auto-detect whether it is running in a Jupyter notebook, an interactive terminal, or a non-interactive environment and automatically select the appropriate display backend. *(Subsumes FR-020.)*

**Progress Bars (US1, US3)**
- **FR-004**: The SDK MUST provide a built-in rich progress bar for terminal environments that activates automatically (opt-out) during blocking wait operations when the `[rich]` extra is installed. Users suppress with `progress=False`.
- **FR-005**: The SDK MUST provide an ipywidgets-based progress bar for notebook environments that activates automatically during blocking wait operations when the `[notebook]` extra is installed.
- **FR-006**: Progress bars MUST show at minimum: current resource state, elapsed time, and a visual animation (spinner for indeterminate, bar for deterministic progress).
- **FR-007**: Users MUST be able to disable automatic progress display by passing `progress=False` to wait operations.
- **FR-008**: Progress bars MUST handle completion (success indicator), failure (error indicator with reason), and interruption (clean up display, cancel the underlying wait operation, re-raise `KeyboardInterrupt`) gracefully.
- **FR-008a**: When multiple concurrent wait operations run simultaneously, each MUST display its own independent progress bar, stacked vertically.

**Tables (US2, US3)**
- **FR-009**: The SDK MUST provide a rich table renderer for terminal environments with styled headers, column alignment, and color-coded resource states when the `[rich]` extra is installed.
- **FR-010**: The SDK MUST provide an HTML table renderer for notebook environments with styled headers, alternating row colors, and color-coded states when the `[notebook]` extra is installed.
- **FR-011**: Resource state colors MUST follow a consistent scheme: green for success states (RUNNING, READY, SUCCEEDED), yellow for transitional states (CREATING, PENDING, SCALING), red for failure states (FAILED, ERROR, CRASHED).
- **FR-012**: When output is piped (non-TTY), the SDK MUST strip ANSI color codes and special formatting automatically.

**Colored Logs (US4)**
- **FR-013**: The SDK MUST provide colored log output for terminal environments with log-level-based color coding when the `[rich]` extra is installed.
- **FR-014**: The SDK MUST provide styled HTML log output for notebook environments when the `[notebook]` extra is installed.
- **FR-015**: Log entries from multiple sources (head node, workers) MUST be visually distinguishable via labels or color differentiation.

**Notebook Widgets (US3, US5)**
- **FR-016**: Resource handles (ClusterHandle, JobHandle, ServiceHandle) MUST implement `_repr_html_()` to render styled HTML summary cards in notebook environments when the `[notebook]` extra is installed.
- **FR-017**: Notebook summary cards for resource handles MUST include interactive action buttons for common operations (e.g., delete, scale, open dashboard).
- **FR-018**: Action buttons for destructive operations MUST require a confirmation step before executing.
- **FR-019**: When the `[notebook]` extra is not installed, handles MUST fall back to the standard `__repr__` text representation.

**Display Helper (US2, US3)**
- **FR-022**: The SDK MUST provide a `display()` utility function that renders any resource list or single resource as a rich table in the current environment (rich table in terminal, HTML table in notebook, plain text as fallback).
- **FR-023**: The `display()` function MUST be importable from the top-level `kuberay_sdk` package.
- **FR-024**: The Python API MUST continue to return raw data objects from all methods; rich rendering MUST NOT alter return values.

**Environment Detection (US1-US5)**
- **FR-020**: *(Merged into FR-003 — environment auto-detection is covered there.)*
- **FR-021**: Users MUST be able to override environment auto-detection by setting a `KUBERAY_DISPLAY` environment variable (values: `rich`, `notebook`, `plain`, `auto`).

### Key Entities

- **DisplayBackend**: An abstraction that determines how output (tables, progress, logs) is rendered. Each backend provides `render_table()`, `render_progress()`, `render_log_line()`, and `render_html_card()` methods. Implementations: RichBackend (terminal), NotebookBackend (Jupyter), PlainBackend (fallback).
- **ProgressContext**: A context manager returned by `DisplayBackend.render_progress()` that wraps a wait loop, displaying and updating progress. Supports `update()`, `complete()`, and `fail()` operations. Has terminal (rich), notebook (ipywidgets), and plain-text variants.
- **DisplayHelper**: A top-level `display()` function that auto-selects the appropriate backend and renders resource data for the current environment.
- **ActionDef**: A definition for a notebook action button, specifying label, callback, and whether the action is destructive (requires confirmation).
- **StateColorScheme**: A mapping of resource states to display colors used consistently across all backends.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users see a live progress bar during all blocking wait operations without any additional code when the rich extra is installed.
- **SC-002**: Resource listings display color-coded states, allowing users to identify failed resources at a glance within 1 second of visual scanning.
- **SC-003**: Notebook users see inline HTML tables and ipywidgets progress bars that update in-place during operations.
- **SC-004**: All rich display features degrade gracefully — the SDK produces no errors and falls back to plain text when extras are not installed.
- **SC-005**: Log output with color coding allows users to identify ERROR-level entries at a glance without reading each line.
- **SC-006**: Notebook action buttons allow users to perform common follow-up operations (delete, scale, open dashboard) without writing additional code.
- **SC-007**: Piped or non-TTY output contains no ANSI escape codes or HTML tags.

## Assumptions

- The `rich` Python library is the display engine for terminal environments. It is a widely-adopted, well-maintained library with built-in support for tables, progress bars, and color output.
- The `ipywidgets` library is the widget engine for Jupyter notebook environments. It is the standard for interactive notebook widgets.
- Environment detection uses `IPython.get_ipython()` to detect notebook contexts and `sys.stdout.isatty()` to detect terminal contexts. Full interactive widget support targets Jupyter and JupyterLab. Google Colab and VS Code notebooks receive HTML-only rendering (styled tables, colored logs) without interactive widget features (action buttons, ipywidgets progress bars).
- The existing `ProgressStatus` model and `progress_callback` parameter from feature 004 serve as the foundation for rich progress rendering — the rich display layer wraps the existing callback mechanism.
- The existing `format_table` and `format_json` functions in `cli/formatters.py` are the fallback plain-text renderers.
- Button callbacks in notebooks execute SDK operations in the notebook's event loop. Long-running button actions display their own progress indicators.
- The `[display]` extra is a convenience alias that installs both `[rich]` and `[notebook]` dependencies.

## Out of Scope

- Custom themes or user-configurable color schemes — the SDK ships with a single consistent color scheme.
- Terminal UI (TUI) dashboards or full-screen terminal applications.
- Real-time streaming dashboards in notebooks (e.g., live-updating cluster metrics graphs).
- Full interactive widget support for non-Jupyter/JupyterLab notebook environments (e.g., Databricks notebooks, Zeppelin) — these receive HTML-only fallback at best.
- Audio or desktop notification alerts for completed operations.
- Custom widget development framework — only pre-built action buttons are provided.
