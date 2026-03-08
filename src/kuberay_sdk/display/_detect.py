"""Environment detection for display backend selection.

Detects whether the SDK is running in a Jupyter notebook, an interactive
terminal, or a non-interactive (plain) environment.
"""

from __future__ import annotations

import os
import sys


def detect_environment() -> str:
    """Detect the current runtime environment for display rendering.

    Checks ``KUBERAY_DISPLAY`` env var first, then auto-detects.

    Returns:
        One of ``"notebook"``, ``"terminal"``, or ``"plain"``.
    """
    env_override = os.environ.get("KUBERAY_DISPLAY", "auto").lower().strip()

    if env_override == "plain":
        return "plain"
    if env_override == "rich":
        return "terminal"
    if env_override == "notebook":
        return "notebook"
    # "auto" or unrecognized → proceed with detection

    if _is_notebook():
        return "notebook"
    if _is_terminal():
        return "terminal"
    return "plain"


def _is_notebook() -> bool:
    """Check if running inside a Jupyter/IPython notebook kernel."""
    try:
        from IPython import get_ipython

        shell = get_ipython()
        if shell is None:
            return False
        shell_class = type(shell).__name__
        # ZMQInteractiveShell = Jupyter notebook/lab
        if shell_class == "ZMQInteractiveShell":
            return True
        # Google Colab
        if shell_class == "Shell" and _is_colab():
            return True
    except ImportError:
        pass
    return False


def _is_colab() -> bool:
    """Check if running in Google Colab."""
    try:
        import google.colab  # noqa: F401

        return True
    except ImportError:
        return False


def _is_vscode_notebook() -> bool:
    """Check if running in a VS Code notebook."""
    return "VSCODE_PID" in os.environ


def _is_terminal() -> bool:
    """Check if stdout is an interactive terminal (TTY)."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
