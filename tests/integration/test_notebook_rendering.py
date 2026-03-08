"""Integration tests for notebook rendering (T046)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestNotebookIntegration:
    """Integration tests for notebook display features."""

    def test_import_kuberay_sdk_with_display(self) -> None:
        """Importing kuberay_sdk should not fail with display extras installed."""
        import kuberay_sdk

        assert hasattr(kuberay_sdk, "display")

    def test_display_function_accessible_from_top_level(self) -> None:
        """display() should be importable from kuberay_sdk.display."""
        from kuberay_sdk.display import display

        assert callable(display)

    def test_cluster_handle_has_repr_html(self) -> None:
        """ClusterHandle should have _repr_html_() method."""
        from kuberay_sdk.client import ClusterHandle

        handle = ClusterHandle("test", "default", MagicMock())
        assert hasattr(handle, "_repr_html_")

    def test_job_handle_has_repr_html(self) -> None:
        """JobHandle should have _repr_html_() method."""
        from kuberay_sdk.client import JobHandle

        handle = JobHandle("test", "default", MagicMock())
        assert hasattr(handle, "_repr_html_")

    def test_service_handle_has_repr_html(self) -> None:
        """ServiceHandle should have _repr_html_() method."""
        from kuberay_sdk.client import ServiceHandle

        handle = ServiceHandle("test", "default", MagicMock())
        assert hasattr(handle, "_repr_html_")

    def test_repr_html_returns_valid_html_with_notebook_backend(self) -> None:
        """_repr_html_() should return valid HTML when notebook backend active."""
        from kuberay_sdk.client import ClusterHandle
        from kuberay_sdk.display._notebook_backend import NotebookBackend

        handle = ClusterHandle("test-cluster", "default", MagicMock())

        with patch("kuberay_sdk.display.get_backend", return_value=NotebookBackend()):
            import kuberay_sdk.display as display_mod

            display_mod._cached_backend = None
            html = handle._repr_html_()

        assert html is not None
        assert "<div" in html
        assert "test-cluster" in html
        assert "border" in html

    def test_display_renders_html_table_in_notebook_env(self) -> None:
        """display() should render HTML table when notebook backend is active."""
        from kuberay_sdk.display._notebook_backend import NotebookBackend

        data = [{"name": "c1", "state": "RUNNING"}]

        with (
            patch("kuberay_sdk.display.get_backend", return_value=NotebookBackend()),
            patch("kuberay_sdk.display._notebook_backend._ipython_display") as mock_display,
        ):
            import kuberay_sdk.display as display_mod

            display_mod._cached_backend = None
            from kuberay_sdk.display import display

            display(data)

            mock_display.assert_called_once()
            html = mock_display.call_args[0][0].data
            assert "<table" in html
            assert "c1" in html
