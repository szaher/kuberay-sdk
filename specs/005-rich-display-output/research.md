# Research: Rich Display & Notebook Integration

**Feature**: 005-rich-display-output
**Date**: 2026-03-08

## R1: Terminal Rich Display Library

**Decision**: Use `rich` (v13.0+) as the terminal display engine.

**Rationale**: `rich` is the de facto standard for Python terminal output. It provides tables, progress bars, spinners, color output, and automatic TTY detection out of the box. It handles ANSI stripping for non-TTY output (piped/redirected), which directly satisfies FR-012. The `rich.progress` module supports multiple concurrent progress bars (stacked), satisfying the clarification decision. `rich.live` enables in-place updates. The library is well-maintained (>50k GitHub stars, active development, Python 3.8+ support).

**Alternatives considered**:
- `tqdm`: Strong for progress bars but weak for tables and general styled output. Would require a second library for tables.
- `click.echo` + ANSI codes: Already a dependency, but lacks structured table/progress support. Manual ANSI management is error-prone.
- `textualize/textual`: Full TUI framework — overkill for our needs (progress bars and tables, not full-screen apps).

## R2: Notebook Widget Library

**Decision**: Use `ipywidgets` (v8.0+) for interactive notebook widgets.

**Rationale**: `ipywidgets` is the standard for Jupyter interactive widgets. It provides `IntProgress`, `FloatProgress`, `HTML`, `Button`, `VBox`, `HBox` — all needed for progress bars, HTML tables, and action buttons. Version 8.0+ has improved JupyterLab compatibility and supports the `comm` protocol. Works in Jupyter Notebook and JupyterLab natively.

**Alternatives considered**:
- `IPython.display.HTML` only: Sufficient for styled tables but lacks interactive progress bars and action buttons. Will be used as the HTML-only fallback for Colab/VS Code.
- `panel`/`voila`: Full dashboarding frameworks — too heavy for our use case.
- `anywidget`: Modern alternative but less mature ecosystem; `ipywidgets` has broader compatibility.

## R3: Environment Detection Strategy

**Decision**: Use a three-tier detection approach: (1) `IPython.get_ipython()` for notebook detection, (2) `sys.stdout.isatty()` for terminal detection, (3) plain text fallback.

**Rationale**: This is the standard pattern used by `rich`, `tqdm`, `pandas`, and other Python libraries that adapt to their environment. The detection is:
1. **Notebook**: Check if `IPython.get_ipython()` returns a `ZMQInteractiveShell` instance (Jupyter kernel). If yes, use NotebookBackend.
2. **Terminal**: Check if `sys.stdout.isatty()` returns True. If yes, use RichBackend.
3. **Non-interactive**: Fallback to PlainBackend.

For Colab/VS Code detection within notebooks: check `google.colab` module presence or `VSCODE_PID` env var. These get HTML-only output (no ipywidgets).

Override via `KUBERAY_DISPLAY` env var: `rich` forces RichBackend, `notebook` forces NotebookBackend, `plain` forces PlainBackend, `auto` (default) uses detection.

**Alternatives considered**:
- Check `TERM` env var: Unreliable across platforms, especially in containers.
- Check `DISPLAY` env var: X11-specific, not relevant to terminal color support.

## R4: Backend Abstraction Pattern

**Decision**: Use a Python `Protocol` (typing.Protocol) for `DisplayBackend`, not an abstract base class.

**Rationale**: A Protocol is structural (duck typing), not nominal. This means backends don't need to inherit from a base class, making it easier to add new backends without import dependencies. The core SDK can define the Protocol without importing `rich` or `ipywidgets`. Each backend implementation lives in its own module that is only imported when the corresponding optional dependency is available.

**Alternatives considered**:
- ABC (Abstract Base Class): Requires imports at class definition time; heavier coupling.
- No abstraction (if/elif chains): Violates Open/Closed principle; becomes messy as backends grow.

## R5: Integration with Existing Progress Callback

**Decision**: The rich progress rendering wraps the existing `progress_callback` parameter on wait methods. A new `progress` parameter (bool, default `True`) controls auto-display.

**Rationale**: Feature 004 already established the `progress_callback: Callable[[ProgressStatus], None]` pattern on `wait_until_ready()` and `job.wait()`. The rich display layer provides a built-in callback that renders to a progress bar. When `progress=True` (default) and no explicit `progress_callback` is provided, the SDK auto-creates a rich progress callback using the detected backend. When the user provides their own `progress_callback`, it takes precedence. When `progress=False`, no automatic display is shown.

Parameter precedence: `progress_callback` (explicit) > `progress=True` (auto) > `progress=False` (silent).

**Alternatives considered**:
- Replace `progress_callback` with `progress` entirely: Breaking change; existing users may have custom callbacks.
- Add `progress` as a separate parameter alongside `progress_callback`: Chosen. Both can coexist cleanly.

## R6: Lazy Import Strategy for Optional Dependencies

**Decision**: Use try/except ImportError at module level in each backend module, with a module-level `HAS_RICH` / `HAS_IPYWIDGETS` flag.

**Rationale**: This is the standard Python pattern for optional dependencies. The `display/__init__.py` module uses these flags to select the appropriate backend. The core SDK never imports `rich` or `ipywidgets` — only the `display/` subpackage does, and only when its functions are called. This ensures zero import-time overhead for users who don't use display features.

```python
# display/_rich_backend.py
try:
    import rich
    from rich.progress import Progress
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
```

**Alternatives considered**:
- `importlib.util.find_spec()`: Checks availability without importing, but we need the actual imports anyway.
- Lazy module-level `__getattr__`: Overly complex for this use case.

## R7: `_repr_html_()` for Notebook Display

**Decision**: Add `_repr_html_()` to ClusterHandle, JobHandle, and ServiceHandle. When the `[notebook]` extra is installed, it renders a styled HTML card with action buttons. Otherwise, returns None (Jupyter falls back to `__repr__`).

**Rationale**: Jupyter's display system calls `_repr_html_()` on objects when rendering cell output. If the method returns `None` or is absent, Jupyter falls back to `__repr__()`. This is the standard pattern used by pandas DataFrames, plotly figures, and other data science libraries. The HTML card includes: resource name, namespace, state (color-coded), and action buttons (as `ipywidgets.Button` or plain HTML links for non-widget environments).

**Alternatives considered**:
- Override `__repr__` with ANSI colors: Doesn't work in notebooks; ANSI is not rendered as HTML.
- `_repr_mimebundle_()`: More flexible but more complex; `_repr_html_()` is sufficient.

## R8: Action Button Implementation

**Decision**: Use `ipywidgets.Button` with `on_click` callbacks for Jupyter/JupyterLab. For Colab/VS Code (HTML-only fallback), render static HTML without interactive buttons.

**Rationale**: `ipywidgets.Button` is the standard interactive widget for Jupyter. The `on_click` callback receives the button instance and can trigger SDK operations. For destructive actions (Delete), a confirmation widget (`ipywidgets.ToggleButton` or a second "Confirm" button) appears before execution. The button callbacks hold a reference to the handle's client, allowing them to call SDK methods directly.

For Colab/VS Code where ipywidgets may not render, the `_repr_html_()` returns a styled HTML summary card without action buttons — users get a nice visual display but must use code for actions.

**Alternatives considered**:
- JavaScript-based buttons via `IPython.display.Javascript`: Security restrictions in many notebook environments; unreliable.
- `panel.widgets.Button`: Requires additional dependency (`panel`); overkill.
