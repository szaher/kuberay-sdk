# Tasks: Rich Display & Notebook Integration

**Input**: Design documents from `/specs/005-rich-display-output/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included per constitution (Principle IV: Test-First is NON-NEGOTIABLE).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/kuberay_sdk/` at repository root
- **Tests**: `tests/unit/`, `tests/integration/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, optional dependency configuration, package structure

- [x] T001 Add `rich`, `notebook`, and `display` optional extras to `pyproject.toml` — `rich = ["rich>=13.0"]`, `notebook = ["ipywidgets>=8.0"]`, `display = ["rich>=13.0", "ipywidgets>=8.0"]`
- [x] T002 Create `src/kuberay_sdk/display/__init__.py` with public API stubs (`get_backend()`, `display()`) and `__all__` exports. All public functions MUST include docstrings with usage examples per Constitution Principle I.
- [x] T003 [P] Create `src/kuberay_sdk/display/_detect.py` — environment detection module with `detect_environment()` function returning `"notebook"`, `"terminal"`, or `"plain"` using `IPython.get_ipython()` and `sys.stdout.isatty()`. Support `KUBERAY_DISPLAY` env var override (`rich`, `notebook`, `plain`, `auto`). Detect Colab via `google.colab` module, VS Code via `VSCODE_PID` env var.
- [x] T004 [P] Create `src/kuberay_sdk/display/_colors.py` — `StateColorScheme` as a module-level frozen dict mapping resource states to color names. Groups: green (`RUNNING`, `READY`, `SUCCEEDED`, `COMPLETE`), yellow (`CREATING`, `PENDING`, `SCALING`, `INITIALIZING`, `SUBMITTING`), red (`FAILED`, `ERROR`, `CRASHED`, `TIMEOUT`, `UNKNOWN`). Include `get_state_color(state: str) -> str` helper that defaults unknown states to yellow.
- [x] T005 [P] Create `src/kuberay_sdk/display/_backend.py` — `DisplayBackend` Protocol, `ProgressContext` Protocol, and `ActionDef` dataclass (`label: str`, `callback: Callable[[], None]`, `destructive: bool = False`, `icon: str | None = None`) per `contracts/display-backend.md`. Include `PlainBackend` implementation: `render_table` delegates to `cli.formatters.format_table()`, `render_progress` returns a no-op `PlainProgressContext`, `render_log_line` prints plain text, `render_html_card` returns `None`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core display infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Write unit tests for environment detection in `tests/unit/display/test_detect.py` — test cases: TTY terminal returns `"terminal"`, Jupyter ZMQInteractiveShell returns `"notebook"`, non-TTY returns `"plain"`, `KUBERAY_DISPLAY=plain` override, `KUBERAY_DISPLAY=rich` override, Colab detection, VS Code detection. Mock `IPython.get_ipython`, `sys.stdout.isatty`, `os.environ`.
- [x] T007 [P] Write unit tests for state color scheme in `tests/unit/display/test_colors.py` — test all state groups map to correct colors, unknown state defaults to yellow, function returns valid color string.
- [x] T008 [P] Write unit tests for PlainBackend in `tests/unit/display/test_plain_backend.py` — test `render_table` produces aligned text output matching existing `format_table`, `render_progress` returns no-op context manager, `render_log_line` prints plain text, `render_html_card` returns `None`.
- [x] T009 Implement `get_backend()` in `src/kuberay_sdk/display/__init__.py` — uses `_detect.detect_environment()` to select backend. Returns `RichBackend` if terminal + rich available, `NotebookBackend` if notebook + ipywidgets available, `PlainBackend` otherwise. Cache result per session (module-level singleton).
- [x] T010 Write unit tests for `display()` helper in `tests/unit/display/test_display_helper.py` — test with list of mock ClusterStatus objects renders table, single handle renders card, empty list prints "No resources found", `format="json"` delegates to `format_json`. Also test FR-024: assert that `client.list_clusters()` return type is unchanged (raw data objects, not display-modified) when display extras are installed.
- [x] T011 Implement `display()` function in `src/kuberay_sdk/display/__init__.py` per `contracts/display-helper.md` — auto-detect backend, extract table data from resource objects, call `backend.render_table()` or `backend.render_html_card()`.
- [x] T012 Add `display` to lazy imports in `src/kuberay_sdk/__init__.py` — add `"display": ("kuberay_sdk.display", "display")` to `_LAZY_IMPORTS` dict and `"display"` to `__all__`.

**Checkpoint**: Foundation ready — environment detection, color scheme, PlainBackend, and display() helper all functional. User story implementation can now begin.

---

## Phase 3: User Story 1 — Rich Terminal Progress Bars (Priority: P1) MVP

**Goal**: Auto-display a rich progress bar during blocking wait operations in terminal environments when `kuberay-sdk[rich]` is installed.

**Independent Test**: Call `wait_until_ready()` from a terminal without any custom callback and verify a progress bar is displayed showing state, elapsed time, and spinner animation.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T013 [P] [US1] Write unit tests for RichBackend progress rendering in `tests/unit/display/test_rich_backend.py` — test `render_progress()` returns a context manager that wraps `rich.progress.Progress`, test `update()` calls update the progress display, test `complete()` shows success indicator, test `fail()` shows error indicator, test `__exit__` with `KeyboardInterrupt` cleans up and returns `False`. Mock `rich.progress.Progress`.
- [x] T014 [P] [US1] Write unit tests for wait method progress integration in `tests/unit/test_handle_progress.py` — test `wait_until_ready(progress=True)` auto-creates a progress callback, test `wait_until_ready(progress=False)` creates no callback, test explicit `progress_callback` takes precedence over `progress=True`, test `progress=True` without rich installed falls back to no-op.

### Implementation for User Story 1

- [x] T015 [US1] Create `src/kuberay_sdk/display/_rich_backend.py` — `RichBackend` class implementing `DisplayBackend` protocol. `render_progress(timeout)` returns a `RichProgressContext` that wraps `rich.progress.Progress` with a spinner task showing state, elapsed time, and indeterminate animation. Support stacked progress bars for concurrent waits. `render_table`, `render_log_line`, `render_html_card` can be stub/pass-through for now (implemented in US2/US4). Use `try: import rich; HAS_RICH = True except ImportError: HAS_RICH = False` pattern.
- [x] T016 [US1] Implement `RichProgressContext` in `src/kuberay_sdk/display/_rich_backend.py` — context manager wrapping `rich.progress.Progress`. `update(status)` updates task description with state and elapsed time. `complete(msg)` stops with green checkmark. `fail(msg)` stops with red X. `__exit__` with `KeyboardInterrupt`: stop progress, return `False` to re-raise.
- [x] T017 [US1] Add `progress: bool = True` parameter to `ClusterHandle.wait_until_ready()` in `src/kuberay_sdk/client.py` — when `progress=True` and no `progress_callback` provided, auto-create a progress callback using `get_backend().render_progress(timeout)`. When `progress=False`, pass `None` as callback. When explicit `progress_callback` is provided, use it (ignore `progress` flag).
- [x] T018 [US1] Add `progress: bool = True` parameter to `JobHandle.wait()` in `src/kuberay_sdk/client.py` — same logic as T017 for job wait operations.
- [x] T019 [US1] Update `get_backend()` in `src/kuberay_sdk/display/__init__.py` to return `RichBackend` when environment is terminal and `rich` is importable.

**Checkpoint**: Terminal users see a live progress bar during `wait_until_ready()` and `job.wait()` without writing any extra code. `progress=False` suppresses it. Ctrl+C cleans up and re-raises.

---

## Phase 4: User Story 2 — Beautified Terminal Tables (Priority: P2)

**Goal**: Render styled, color-coded tables for resource listings in terminal environments when `kuberay-sdk[rich]` is installed.

**Independent Test**: Call `display(client.list_clusters())` and verify styled table with color-coded states is rendered. Pipe output and verify no ANSI codes.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T020 [P] [US2] Write unit tests for RichBackend table rendering in `tests/unit/display/test_rich_backend.py` (append to existing) — test `render_table()` produces a `rich.table.Table` with styled headers, test state column values are color-coded using `StateColorScheme`, test non-TTY output strips ANSI codes.
- [x] T021 [P] [US2] Write unit tests for CLI formatter integration in `tests/unit/display/test_cli_formatter_integration.py` — test CLI `kuberay cluster list` uses RichBackend when available, test `--output json` bypasses rich rendering, test piped output has no ANSI codes.

### Implementation for User Story 2

- [x] T022 [US2] Implement `RichBackend.render_table()` in `src/kuberay_sdk/display/_rich_backend.py` — create a `rich.table.Table` with title, styled headers (bold), and aligned columns. When `state_column` is specified, apply color from `StateColorScheme` to state cell values. Use `rich.console.Console(force_terminal=stdout.isatty())` to auto-strip ANSI for piped output.
- [x] T023 [US2] Update `src/kuberay_sdk/cli/formatters.py` to delegate to RichBackend when available — add a `format_rich_table()` function that tries to use `get_backend()`. If backend is `RichBackend`, use it. Otherwise fall back to existing `format_table()`. Update CLI commands in `src/kuberay_sdk/cli/cluster.py`, `src/kuberay_sdk/cli/job.py`, `src/kuberay_sdk/cli/service.py` to use the new function for list output.

**Checkpoint**: `kuberay cluster list` renders a styled table with colored states. `display(clusters)` works from Python REPL. Piped output is clean.

---

## Phase 5: User Story 3 — Notebook Interactive Widgets (Priority: P3)

**Goal**: Render ipywidgets progress bars and HTML tables inline in Jupyter notebooks.

**Independent Test**: In a Jupyter notebook, call `wait_until_ready()` and verify an ipywidgets progress bar renders inline. Call `display(clusters)` and verify an HTML table appears.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T024 [P] [US3] Write unit tests for NotebookBackend in `tests/unit/display/test_notebook_backend.py` — test `render_table()` calls `IPython.display.display(HTML(...))` with styled HTML table, test alternating row colors, test state values are color-coded in HTML, test `render_progress()` returns ipywidgets-based context manager, test `update()` updates widget value, test fallback when ipywidgets not installed returns `None`/plain text.
- [x] T025 [P] [US3] Write unit tests for handle `_repr_html_()` in `tests/unit/test_handle_repr.py` — test `ClusterHandle._repr_html_()` returns HTML string with name, namespace, state when notebook extra installed, test returns `None` when extra not installed, test `JobHandle._repr_html_()` includes mode, test `ServiceHandle._repr_html_()` includes state.

### Implementation for User Story 3

- [x] T026 [US3] Create `src/kuberay_sdk/display/_notebook_backend.py` — `NotebookBackend` class implementing `DisplayBackend` protocol. Use `try: import ipywidgets; HAS_IPYWIDGETS = True except ImportError: HAS_IPYWIDGETS = False`. Detect Colab/VS Code for HTML-only fallback (no ipywidgets features).
- [x] T027 [US3] Implement `NotebookBackend.render_table()` in `src/kuberay_sdk/display/_notebook_backend.py` — generate HTML `<table>` with styled headers (bold, background color), alternating row colors, and color-coded state values using `StateColorScheme`. Call `IPython.display.display(IPython.display.HTML(html_string))`.
- [x] T028 [US3] Implement `NotebookBackend.render_progress()` in `src/kuberay_sdk/display/_notebook_backend.py` — return a `NotebookProgressContext` that creates an `ipywidgets.FloatProgress` (or `IntProgress`) with `ipywidgets.Label` showing state and elapsed time, wrapped in `ipywidgets.VBox`. `update()` sets progress value and label text in-place. `complete()` sets bar to 100% with green style. `fail()` sets bar style to danger. For Colab/VS Code fallback: use `IPython.display.clear_output()` + `print()`.
- [x] T029 [US3] Add `_repr_html_()` to `ClusterHandle` in `src/kuberay_sdk/client.py` — try to import `get_backend` from `kuberay_sdk.display`, call `backend.render_html_card()` with handle data (`name`, `namespace`, state from cached `__repr__` data). Return HTML string or `None` if notebook extra not installed. Do NOT make API calls.
- [x] T030 [US3] Add `_repr_html_()` to `JobHandle` and `ServiceHandle` in `src/kuberay_sdk/client.py` — same pattern as T029, including mode for JobHandle.
- [x] T031 [US3] Implement `NotebookBackend.render_html_card()` in `src/kuberay_sdk/display/_notebook_backend.py` — generate styled HTML card per `contracts/handle-repr-html.md` template with border, rounded corners, key-value table, and color-coded state.
- [x] T032 [US3] Update `get_backend()` in `src/kuberay_sdk/display/__init__.py` to return `NotebookBackend` when environment is notebook and `ipywidgets` is importable, or HTML-only `NotebookBackend` variant when in Colab/VS Code.

**Checkpoint**: Notebook users see inline progress bars and HTML tables. Handles display styled cards. Falls back to plain text when extras missing.

---

## Phase 6: User Story 4 — Colored Log Output (Priority: P4)

**Goal**: Render color-coded log output with source labels in terminal and notebook environments.

**Independent Test**: Stream logs from a job and verify log levels are color-coded (INFO white, WARNING yellow, ERROR red) with source labels.

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T033 [P] [US4] Write unit tests for log rendering in `tests/unit/display/test_log_renderer.py` — test log level detection (INFO, WARNING, ERROR, CRITICAL), test source label prefixing, test RichBackend colorizes by level, test NotebookBackend produces HTML with color spans, test PlainBackend prints plain text, test non-TTY strips ANSI.

### Implementation for User Story 4

- [x] T034 [US4] Create `src/kuberay_sdk/display/_log_renderer.py` — `parse_log_level(line: str) -> str` function that detects log level from line content (regex for `INFO`, `WARNING`, `ERROR`, `CRITICAL` patterns). `format_source_label(source: str) -> str` for source identification.
- [x] T035 [US4] Implement `RichBackend.render_log_line()` in `src/kuberay_sdk/display/_rich_backend.py` — use `rich.console.Console.print()` with color styles based on detected log level. Prefix with source label in distinct color when provided. Use `_log_renderer.parse_log_level()`.
- [x] T036 [US4] Implement `NotebookBackend.render_log_line()` in `src/kuberay_sdk/display/_notebook_backend.py` — generate HTML `<span>` with CSS color styles based on log level. Prefix with source label `<span>`. Call `IPython.display.display(IPython.display.HTML(...))`.
- [x] T037 [US4] Integrate log rendering into `JobHandle.logs(stream=True)` in `src/kuberay_sdk/client.py` — when streaming logs, pass each line through `get_backend().render_log_line()` with source label if available from log metadata.

**Checkpoint**: Log streaming shows color-coded output in terminals and HTML-styled output in notebooks. Source labels distinguish head from workers.

---

## Phase 7: User Story 5 — Notebook Action Buttons (Priority: P5)

**Goal**: Display interactive action buttons on resource handles in Jupyter notebooks.

**Independent Test**: Display a ClusterHandle in a Jupyter notebook and verify action buttons render. Click "Open Dashboard" and verify it displays the URL.

### Tests for User Story 5

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T038 [P] [US5] Write unit tests for action buttons in `tests/unit/display/test_action_buttons.py` — test `ActionDef` creation with label/callback/destructive flag, test button rendering creates `ipywidgets.Button` widgets, test destructive button shows confirmation before executing callback, test non-notebook environment skips buttons, test Colab/VS Code renders HTML card without buttons.

### Implementation for User Story 5

- [x] T039 *(Merged into T005 — `ActionDef` is now created in Phase 1 as part of `_backend.py`.)*
- [x] T040 [US5] Implement action button rendering in `NotebookBackend.render_html_card()` in `src/kuberay_sdk/display/_notebook_backend.py` — when `actions` list is provided and ipywidgets is available: create `ipywidgets.Button` for each action, attach `on_click` callbacks. For destructive actions: first click shows "Confirm?" button, second click executes. For Colab/VS Code: omit buttons from HTML card.
- [x] T041 [US5] Define action button sets for each handle type in `src/kuberay_sdk/display/_notebook_backend.py` — `ClusterHandle`: Delete (destructive), Scale Workers, Open Dashboard. `JobHandle`: Stop (destructive), View Logs, Download Artifacts. `ServiceHandle`: Delete (destructive), Update Replicas.
- [x] T042 [US5] Update `ClusterHandle._repr_html_()` in `src/kuberay_sdk/client.py` to pass `ActionDef` list to `render_html_card()` — create `ActionDef` instances that call `self.delete()`, `self.scale()`, `self.dashboard_url()` when clicked.
- [x] T043 [US5] Update `JobHandle._repr_html_()` and `ServiceHandle._repr_html_()` in `src/kuberay_sdk/client.py` to pass appropriate `ActionDef` lists.

**Checkpoint**: Notebook users see interactive action buttons on resource handles. Destructive actions require confirmation. Colab/VS Code get styled cards without buttons.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T044 [P] Add `KUBERAY_DISPLAY` env var documentation to config handling in `src/kuberay_sdk/config.py` — add `KUBERAY_DISPLAY` to `load_env_vars()` for consistency (even though display module reads it directly).
- [x] T045 [P] Verify CLI rich table coverage — confirm all list commands in `src/kuberay_sdk/cli/cluster.py`, `src/kuberay_sdk/cli/job.py`, `src/kuberay_sdk/cli/service.py` use the `format_rich_table()` function from T023. Fix any missed commands.
- [x] T046 [P] Write integration test in `tests/integration/test_notebook_rendering.py` — test that importing `kuberay_sdk` in a mocked Jupyter kernel activates notebook backend, test `_repr_html_()` returns valid HTML for all handle types, test `display()` renders HTML table.
- [x] T047 Run `ruff check src/kuberay_sdk/display/` and `mypy src/kuberay_sdk/display/` to verify lint and type compliance.
- [x] T048 Validate quickstart.md examples — ensure all code snippets in `specs/005-rich-display-output/quickstart.md` are syntactically valid and match implemented API signatures.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) completion — BLOCKS all user stories
- **User Stories (Phases 3-7)**: All depend on Foundational (Phase 2) completion
  - US1-US5 can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4 → P5)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1) — Progress Bars**: Can start after Phase 2. No dependencies on other stories. **MVP**.
- **US2 (P2) — Tables**: Can start after Phase 2. No dependencies on US1. Shares `RichBackend` file with US1 but different methods.
- **US3 (P3) — Notebook Widgets**: Can start after Phase 2. No dependencies on US1/US2. Creates `NotebookBackend`.
- **US4 (P4) — Colored Logs**: Can start after Phase 2. No dependencies on other stories. Creates `_log_renderer.py`.
- **US5 (P5) — Action Buttons**: Depends on US3 completion (needs `NotebookBackend` and `_repr_html_()` from US3).

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Protocol/models before backend implementations
- Backend implementation before client integration
- Core implementation before CLI integration

### Parallel Opportunities

- **Phase 1**: T003, T004, T005 can run in parallel (different files)
- **Phase 2**: T006, T007, T008 can run in parallel (test files); T010 depends on T009
- **Phase 3 (US1)**: T013 and T014 can run in parallel (test files)
- **Phase 4 (US2)**: T020 and T021 can run in parallel (test files)
- **Phase 5 (US3)**: T024 and T025 can run in parallel (test files)
- **Cross-story**: US1, US2, US3, US4 can all start in parallel after Phase 2

---

## Parallel Example: User Story 1 (MVP)

```bash
# After Phase 2 completion, launch US1 tests in parallel:
Task: T013 "Unit tests for RichBackend progress in tests/unit/display/test_rich_backend.py"
Task: T014 "Unit tests for wait method progress in tests/unit/test_handle_progress.py"

# Then implement sequentially:
Task: T015 "Create RichBackend in src/kuberay_sdk/display/_rich_backend.py"
Task: T016 "Implement RichProgressContext"
Task: T017 "Add progress param to ClusterHandle.wait_until_ready()"
Task: T018 "Add progress param to JobHandle.wait()"
Task: T019 "Update get_backend() for RichBackend selection"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T012)
3. Complete Phase 3: User Story 1 — Progress Bars (T013-T019)
4. **STOP and VALIDATE**: Test progress bars in a terminal
5. Deploy/demo if ready — users immediately benefit from progress feedback

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (Progress Bars) → Test → Deploy (MVP!)
3. Add US2 (Tables) → Test → Deploy — CLI gets beautified output
4. Add US3 (Notebook Widgets) → Test → Deploy — notebook users get widgets
5. Add US4 (Colored Logs) → Test → Deploy — log streaming improved
6. Add US5 (Action Buttons) → Test → Deploy — notebook power users get buttons
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers after Phase 2:
- Developer A: US1 (Progress Bars) + US2 (Tables) — both use RichBackend
- Developer B: US3 (Notebook Widgets) — independent NotebookBackend
- Developer C: US4 (Colored Logs) — independent _log_renderer
- US5 (Action Buttons) starts after US3 completes

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Constitution Principle IV requires TDD — all tests written before implementation
- All optional imports use `try/except ImportError` — never unconditional
- `rich` and `ipywidgets` are optional extras — core SDK must work without them
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
