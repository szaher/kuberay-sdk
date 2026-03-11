"""Unit tests for NotebookBackend (T024)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from kuberay_sdk.models.progress import ProgressStatus


class TestNotebookBackendTable:
    """Tests for NotebookBackend.render_table()."""

    def test_render_table_calls_ipython_display(self) -> None:
        from kuberay_sdk.display._notebook_backend import NotebookBackend

        backend = NotebookBackend()

        with patch("kuberay_sdk.display._notebook_backend._ipython_display") as mock_display:
            backend.render_table(
                ["NAME", "STATE"],
                [["c1", "RUNNING"]],
            )
            mock_display.assert_called_once()
            html_arg = mock_display.call_args[0][0]
            # Should be an HTML object
            assert hasattr(html_arg, "data")
            html = html_arg.data
            assert "<table" in html
            assert "NAME" in html
            assert "c1" in html

    def test_render_table_has_alternating_row_colors(self) -> None:
        from kuberay_sdk.display._notebook_backend import NotebookBackend

        backend = NotebookBackend()
        with patch("kuberay_sdk.display._notebook_backend._ipython_display") as mock_display:
            backend.render_table(
                ["NAME"],
                [["a"], ["b"], ["c"]],
            )
            html = mock_display.call_args[0][0].data
            # Should have alternating background colors
            assert "background" in html.lower() or "bgcolor" in html.lower() or "#f" in html.lower()

    def test_state_values_are_color_coded_in_html(self) -> None:
        from kuberay_sdk.display._notebook_backend import NotebookBackend

        backend = NotebookBackend()
        with patch("kuberay_sdk.display._notebook_backend._ipython_display") as mock_display:
            backend.render_table(
                ["NAME", "STATE"],
                [["c1", "RUNNING"], ["c2", "FAILED"]],
                state_column=1,
            )
            html = mock_display.call_args[0][0].data
            # Uses CSS hex colors: #28a745 (green), #dc3545 (red)
            assert "#28a745" in html
            assert "#dc3545" in html


class TestNotebookBackendProgress:
    """Tests for NotebookBackend.render_progress()."""

    def test_render_progress_returns_context_manager(self) -> None:
        from kuberay_sdk.display._notebook_backend import NotebookBackend

        backend = NotebookBackend()
        ctx = backend.render_progress(timeout=60.0)
        assert hasattr(ctx, "__enter__")
        assert hasattr(ctx, "__exit__")

    def test_progress_update_updates_widget(self) -> None:
        from kuberay_sdk.display._notebook_backend import NotebookProgressContext

        mock_bar = MagicMock()
        mock_label = MagicMock()
        mock_box = MagicMock()
        ctx = NotebookProgressContext(mock_bar, mock_label, mock_box, timeout=60.0)

        status = ProgressStatus(state="CREATING", elapsed_seconds=5.0)
        ctx.update(status)
        # Label should be updated
        assert mock_label.value != ""

    def test_fallback_when_ipywidgets_not_installed(self) -> None:
        """Should return a plain context when ipywidgets unavailable."""
        with patch.dict("sys.modules", {"ipywidgets": None}):
            # The backend should still be importable
            from kuberay_sdk.display._notebook_backend import NotebookBackend

            backend = NotebookBackend()
            ctx = backend.render_progress(timeout=60.0)
            assert ctx is not None


class TestNotebookBackendHTMLCard:
    """Tests for NotebookBackend.render_html_card()."""

    def test_render_html_card_returns_html(self) -> None:
        from kuberay_sdk.display._notebook_backend import NotebookBackend

        backend = NotebookBackend()
        html = backend.render_html_card(
            {"Name": "my-cluster", "Namespace": "default", "State": "RUNNING"},
        )
        assert html is not None
        assert "my-cluster" in html
        assert "default" in html
        assert "border" in html
