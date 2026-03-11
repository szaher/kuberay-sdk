"""Unit tests for RichBackend progress rendering (T013)."""

from __future__ import annotations

from unittest.mock import MagicMock

from kuberay_sdk.models.progress import ProgressStatus


class TestRichBackendProgress:
    """Tests for RichBackend.render_progress() and RichProgressContext."""

    def test_render_progress_returns_context_manager(self) -> None:
        from kuberay_sdk.display._rich_backend import RichBackend

        backend = RichBackend()
        ctx = backend.render_progress(timeout=60.0)
        assert hasattr(ctx, "__enter__")
        assert hasattr(ctx, "__exit__")

    def test_progress_context_update_calls_rich(self) -> None:
        from kuberay_sdk.display._rich_backend import RichProgressContext

        mock_progress = MagicMock()
        mock_task_id = MagicMock()
        ctx = RichProgressContext(mock_progress, mock_task_id, timeout=60.0)

        status = ProgressStatus(state="CREATING", elapsed_seconds=5.0, message="Waiting")
        ctx.update(status)
        mock_progress.update.assert_called_once()

    def test_progress_context_complete_shows_success(self) -> None:
        from kuberay_sdk.display._rich_backend import RichProgressContext

        mock_progress = MagicMock()
        mock_task_id = MagicMock()
        ctx = RichProgressContext(mock_progress, mock_task_id, timeout=60.0)

        ctx.complete("All done")
        mock_progress.update.assert_called_once()

    def test_progress_context_fail_shows_error(self) -> None:
        from kuberay_sdk.display._rich_backend import RichProgressContext

        mock_progress = MagicMock()
        mock_task_id = MagicMock()
        ctx = RichProgressContext(mock_progress, mock_task_id, timeout=60.0)

        ctx.fail("Timed out")
        mock_progress.update.assert_called_once()

    def test_progress_context_exit_with_keyboard_interrupt_cleans_up(self) -> None:
        from kuberay_sdk.display._rich_backend import RichProgressContext

        mock_progress = MagicMock()
        mock_task_id = MagicMock()
        ctx = RichProgressContext(mock_progress, mock_task_id, timeout=60.0)

        # __exit__ with KeyboardInterrupt should return False (re-raise)
        result = ctx.__exit__(KeyboardInterrupt, KeyboardInterrupt(), None)
        assert result is False
        mock_progress.stop.assert_called_once()

    def test_progress_context_exit_normal_returns_false(self) -> None:
        from kuberay_sdk.display._rich_backend import RichProgressContext

        mock_progress = MagicMock()
        mock_task_id = MagicMock()
        ctx = RichProgressContext(mock_progress, mock_task_id, timeout=60.0)

        result = ctx.__exit__(None, None, None)
        assert result is False

    def test_progress_enter_starts_progress(self) -> None:
        from kuberay_sdk.display._rich_backend import RichBackend

        backend = RichBackend()
        ctx = backend.render_progress(timeout=30.0)
        with ctx as p:
            assert p is ctx
