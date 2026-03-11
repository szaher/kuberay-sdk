"""Unit tests for handle _repr_html_() (T025)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestClusterHandleReprHtml:
    """Tests for ClusterHandle._repr_html_()."""

    def test_repr_html_returns_html_with_notebook_extra(self) -> None:
        from kuberay_sdk.client import ClusterHandle

        handle = ClusterHandle("my-cluster", "default", MagicMock())

        with patch("kuberay_sdk.display.get_backend") as mock_get_backend:
            mock_backend = MagicMock()
            mock_backend.render_html_card.return_value = "<div>HTML card</div>"
            mock_get_backend.return_value = mock_backend

            html = handle._repr_html_()
            assert html is not None
            assert "HTML card" in html

    def test_repr_html_returns_none_without_extra(self) -> None:
        from kuberay_sdk.client import ClusterHandle

        handle = ClusterHandle("my-cluster", "default", MagicMock())

        with patch("kuberay_sdk.display.get_backend") as mock_get_backend:
            mock_backend = MagicMock()
            mock_backend.render_html_card.return_value = None
            mock_get_backend.return_value = mock_backend

            html = handle._repr_html_()
            assert html is None

    def test_repr_html_returns_none_on_import_error(self) -> None:
        from kuberay_sdk.client import ClusterHandle

        handle = ClusterHandle("my-cluster", "default", MagicMock())

        with patch("kuberay_sdk.display.get_backend", side_effect=ImportError):
            html = handle._repr_html_()
            assert html is None


class TestJobHandleReprHtml:
    """Tests for JobHandle._repr_html_()."""

    def test_repr_html_includes_mode(self) -> None:
        from kuberay_sdk.client import JobHandle

        handle = JobHandle("my-job", "default", MagicMock(), mode="DASHBOARD")

        with patch("kuberay_sdk.display.get_backend") as mock_get_backend:
            mock_backend = MagicMock()

            def capture_card(data, *, actions=None):
                assert "Mode" in data
                assert data["Mode"] == "DASHBOARD"
                return "<div>job card</div>"

            mock_backend.render_html_card.side_effect = capture_card
            mock_get_backend.return_value = mock_backend

            html = handle._repr_html_()
            assert html is not None


class TestServiceHandleReprHtml:
    """Tests for ServiceHandle._repr_html_()."""

    def test_repr_html_includes_state(self) -> None:
        from kuberay_sdk.client import ServiceHandle

        handle = ServiceHandle("my-svc", "default", MagicMock())

        with patch("kuberay_sdk.display.get_backend") as mock_get_backend:
            mock_backend = MagicMock()

            def capture_card(data, *, actions=None):
                assert "Name" in data
                assert data["Name"] == "my-svc"
                return "<div>service card</div>"

            mock_backend.render_html_card.side_effect = capture_card
            mock_get_backend.return_value = mock_backend

            html = handle._repr_html_()
            assert html is not None
