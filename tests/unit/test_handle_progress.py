"""Unit tests for wait method progress integration (T014)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch


class TestClusterHandleProgress:
    """Tests for ClusterHandle.wait_until_ready() progress parameter."""

    def _make_handle(self) -> Any:
        from kuberay_sdk.client import ClusterHandle

        return ClusterHandle("test", "default", MagicMock())

    def test_progress_true_auto_creates_callback(self) -> None:
        """progress=True with no callback should auto-create a progress callback."""
        handle = self._make_handle()
        mock_svc = MagicMock()

        with (
            patch("kuberay_sdk.services.cluster_service.ClusterService", return_value=mock_svc),
            patch("kuberay_sdk.display.get_backend") as mock_get_backend,
        ):
            mock_backend = MagicMock()
            mock_progress_ctx = MagicMock()
            mock_backend.render_progress.return_value = mock_progress_ctx
            mock_get_backend.return_value = mock_backend

            handle.wait_until_ready(progress=True)
            mock_svc.wait_until_ready.assert_called_once()

    def test_progress_false_creates_no_callback(self) -> None:
        """progress=False should pass None as callback."""
        handle = self._make_handle()
        mock_svc = MagicMock()

        with patch("kuberay_sdk.services.cluster_service.ClusterService", return_value=mock_svc):
            handle.wait_until_ready(progress=False)
            mock_svc.wait_until_ready.assert_called_once()
            call_kwargs = mock_svc.wait_until_ready.call_args
            assert call_kwargs[1].get("progress_callback") is None

    def test_explicit_callback_takes_precedence(self) -> None:
        """Explicit progress_callback should override progress=True."""
        handle = self._make_handle()
        custom_callback = MagicMock()
        mock_svc = MagicMock()

        with patch("kuberay_sdk.services.cluster_service.ClusterService", return_value=mock_svc):
            handle.wait_until_ready(progress_callback=custom_callback)
            mock_svc.wait_until_ready.assert_called_once()
            call_kwargs = mock_svc.wait_until_ready.call_args
            assert call_kwargs[1].get("progress_callback") is custom_callback

    def test_progress_true_without_rich_falls_back_to_noop(self) -> None:
        """progress=True with PlainBackend should fall back to None callback."""
        from kuberay_sdk.display._backend import PlainBackend

        handle = self._make_handle()
        mock_svc = MagicMock()

        with (
            patch("kuberay_sdk.services.cluster_service.ClusterService", return_value=mock_svc),
            patch("kuberay_sdk.display.get_backend", return_value=PlainBackend()),
        ):
            handle.wait_until_ready(progress=True)
            mock_svc.wait_until_ready.assert_called_once()
            call_kwargs = mock_svc.wait_until_ready.call_args
            # PlainBackend returns None callback (no overhead)
            assert call_kwargs[1].get("progress_callback") is None


class TestJobHandleProgress:
    """Tests for JobHandle.wait() progress parameter."""

    def test_progress_false_creates_no_callback(self) -> None:
        from kuberay_sdk.client import JobHandle

        handle = JobHandle("test-job", "default", MagicMock(), mode="CRD")
        mock_svc = MagicMock()

        with patch("kuberay_sdk.services.job_service.JobService", return_value=mock_svc):
            handle.wait(progress=False)
            mock_svc.wait.assert_called_once()
            call_kwargs = mock_svc.wait.call_args
            assert call_kwargs[1].get("progress_callback") is None
