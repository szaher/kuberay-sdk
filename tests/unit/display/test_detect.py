"""Unit tests for environment detection (T006)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from kuberay_sdk.display._detect import detect_environment


class TestDetectEnvironment:
    """Tests for detect_environment()."""

    def test_tty_terminal_returns_terminal(self) -> None:
        """TTY stdout should detect as terminal."""
        with (
            patch("kuberay_sdk.display._detect._is_notebook", return_value=False),
            patch("kuberay_sdk.display._detect._is_terminal", return_value=True),
            patch.dict("os.environ", {}, clear=True),
        ):
            assert detect_environment() == "terminal"

    def test_jupyter_zmq_returns_notebook(self) -> None:
        """Jupyter ZMQInteractiveShell should detect as notebook."""
        mock_shell = MagicMock()
        type(mock_shell).__name__ = "ZMQInteractiveShell"

        with (
            patch("kuberay_sdk.display._detect.get_ipython", return_value=mock_shell, create=True),
            patch.dict("os.environ", {}, clear=True),
            patch("kuberay_sdk.display._detect._is_notebook", return_value=True),
        ):
            assert detect_environment() == "notebook"

    def test_non_tty_returns_plain(self) -> None:
        """Non-TTY stdout without notebook should detect as plain."""
        with (
            patch("kuberay_sdk.display._detect._is_notebook", return_value=False),
            patch("kuberay_sdk.display._detect._is_terminal", return_value=False),
            patch.dict("os.environ", {}, clear=True),
        ):
            assert detect_environment() == "plain"

    def test_env_var_plain_override(self) -> None:
        """KUBERAY_DISPLAY=plain should override detection."""
        with patch.dict("os.environ", {"KUBERAY_DISPLAY": "plain"}):
            assert detect_environment() == "plain"

    def test_env_var_rich_override(self) -> None:
        """KUBERAY_DISPLAY=rich should return terminal."""
        with patch.dict("os.environ", {"KUBERAY_DISPLAY": "rich"}):
            assert detect_environment() == "terminal"

    def test_env_var_notebook_override(self) -> None:
        """KUBERAY_DISPLAY=notebook should return notebook."""
        with patch.dict("os.environ", {"KUBERAY_DISPLAY": "notebook"}):
            assert detect_environment() == "notebook"

    def test_env_var_auto_uses_detection(self) -> None:
        """KUBERAY_DISPLAY=auto should fall through to detection."""
        with (
            patch.dict("os.environ", {"KUBERAY_DISPLAY": "auto"}),
            patch("kuberay_sdk.display._detect._is_notebook", return_value=False),
            patch("kuberay_sdk.display._detect._is_terminal", return_value=True),
        ):
            assert detect_environment() == "terminal"

    def test_colab_detection(self) -> None:
        """Google Colab shell should detect as notebook."""
        mock_shell = MagicMock()
        type(mock_shell).__name__ = "Shell"

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("kuberay_sdk.display._detect._is_terminal", return_value=False),
            patch("kuberay_sdk.display._detect._is_notebook", return_value=True),
        ):
            assert detect_environment() == "notebook"

    def test_vscode_detection(self) -> None:
        """VS Code notebook (VSCODE_PID set) should be detectable."""
        from kuberay_sdk.display._detect import _is_vscode_notebook

        with patch.dict("os.environ", {"VSCODE_PID": "12345"}):
            assert _is_vscode_notebook() is True

        with patch.dict("os.environ", {}, clear=True):
            assert _is_vscode_notebook() is False
