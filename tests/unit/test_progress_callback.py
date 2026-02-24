"""Unit tests for progress callback in wait operations (US2 - T010)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from kuberay_sdk.models.progress import ProgressStatus


class TestClusterWaitProgress:
    @patch("kuberay_sdk.services.cluster_service.time.sleep")
    @patch("kuberay_sdk.services.cluster_service.time.monotonic")
    def test_callback_invoked_during_wait(self, mock_mono: MagicMock, mock_sleep: MagicMock) -> None:
        """Progress callback should be called each poll cycle."""
        from kuberay_sdk.services.cluster_service import ClusterService

        mock_api = MagicMock()
        mock_config = MagicMock()
        svc = ClusterService(mock_api, mock_config)

        # First call: start time, second: elapsed check, third: after get_status,
        # fourth: elapsed check for second poll, fifth: after second get_status
        mock_mono.side_effect = [0.0, 5.0, 10.0]

        status_creating = MagicMock()
        status_creating.state = "CREATING"
        status_creating.head_ready = False

        status_ready = MagicMock()
        status_ready.state = "RUNNING"
        status_ready.head_ready = True

        with patch.object(svc, "get_status", side_effect=[status_creating, status_ready]):
            callback = MagicMock()
            svc.wait_until_ready("test", "default", timeout=300, progress_callback=callback)
            assert callback.call_count >= 1
            # Check callback was called with ProgressStatus
            first_call_arg = callback.call_args_list[0][0][0]
            assert isinstance(first_call_arg, ProgressStatus)

    @patch("kuberay_sdk.services.cluster_service.time.sleep")
    @patch("kuberay_sdk.services.cluster_service.time.monotonic")
    def test_callback_receives_correct_state(self, mock_mono: MagicMock, mock_sleep: MagicMock) -> None:
        """Progress callback should receive the current cluster state."""
        from kuberay_sdk.services.cluster_service import ClusterService

        mock_api = MagicMock()
        mock_config = MagicMock()
        svc = ClusterService(mock_api, mock_config)

        mock_mono.side_effect = [0.0, 2.0, 5.0]

        status_creating = MagicMock()
        status_creating.state = "CREATING"
        status_creating.head_ready = False

        status_ready = MagicMock()
        status_ready.state = "RUNNING"
        status_ready.head_ready = True

        with patch.object(svc, "get_status", side_effect=[status_creating, status_ready]):
            callback = MagicMock()
            svc.wait_until_ready("test", "default", timeout=300, progress_callback=callback)

            # First call should have CREATING state
            first_progress = callback.call_args_list[0][0][0]
            assert first_progress.state == "CREATING"

            # Second call should have RUNNING state
            second_progress = callback.call_args_list[1][0][0]
            assert second_progress.state == "RUNNING"

    @patch("kuberay_sdk.services.cluster_service.time.sleep")
    @patch("kuberay_sdk.services.cluster_service.time.monotonic")
    def test_no_callback_silent(self, mock_mono: MagicMock, mock_sleep: MagicMock) -> None:
        """Without callback, wait works as before."""
        from kuberay_sdk.services.cluster_service import ClusterService

        mock_api = MagicMock()
        mock_config = MagicMock()
        svc = ClusterService(mock_api, mock_config)
        mock_mono.side_effect = [0.0, 5.0]

        status_ready = MagicMock()
        status_ready.state = "RUNNING"
        status_ready.head_ready = True

        with patch.object(svc, "get_status", return_value=status_ready):
            # no callback, no error
            svc.wait_until_ready("test", "default", timeout=300)

    @patch("kuberay_sdk.services.cluster_service.time.sleep")
    @patch("kuberay_sdk.services.cluster_service.time.monotonic")
    def test_callback_exception_caught(self, mock_mono: MagicMock, mock_sleep: MagicMock) -> None:
        """Callback exception should be caught and not propagate."""
        from kuberay_sdk.services.cluster_service import ClusterService

        mock_api = MagicMock()
        mock_config = MagicMock()
        svc = ClusterService(mock_api, mock_config)
        mock_mono.side_effect = [0.0, 5.0, 10.0]

        status_creating = MagicMock()
        status_creating.state = "CREATING"
        status_creating.head_ready = False

        status_ready = MagicMock()
        status_ready.state = "RUNNING"
        status_ready.head_ready = True

        def bad_callback(status: ProgressStatus) -> None:
            raise RuntimeError("callback error")

        with patch.object(svc, "get_status", side_effect=[status_creating, status_ready]):
            # Should NOT raise even though callback throws
            svc.wait_until_ready("test", "default", timeout=300, progress_callback=bad_callback)


class TestJobWaitProgress:
    @patch("kuberay_sdk.services.job_service.time.sleep")
    @patch("kuberay_sdk.services.job_service.time.monotonic")
    def test_callback_invoked_during_job_wait(self, mock_mono: MagicMock, mock_sleep: MagicMock) -> None:
        """Progress callback should be called each poll cycle for job wait."""
        from kuberay_sdk.services.job_service import JobService

        mock_api = MagicMock()
        mock_config = MagicMock()
        svc = JobService(mock_api, mock_config)

        mock_mono.side_effect = [0.0, 5.0, 10.0]

        status_running = MagicMock()
        status_running.state = MagicMock()
        status_running.state.value = "RUNNING"

        status_done = MagicMock()
        status_done.state = MagicMock()
        status_done.state.value = "SUCCEEDED"

        with patch.object(svc, "get_status", side_effect=[status_running, status_done]):
            callback = MagicMock()
            svc.wait("test-job", "default", timeout=3600, progress_callback=callback)
            assert callback.call_count >= 1
            first_call_arg = callback.call_args_list[0][0][0]
            assert isinstance(first_call_arg, ProgressStatus)

    @patch("kuberay_sdk.services.job_service.time.sleep")
    @patch("kuberay_sdk.services.job_service.time.monotonic")
    def test_job_wait_no_callback_silent(self, mock_mono: MagicMock, mock_sleep: MagicMock) -> None:
        """Without callback, job wait works as before."""
        from kuberay_sdk.services.job_service import JobService

        mock_api = MagicMock()
        mock_config = MagicMock()
        svc = JobService(mock_api, mock_config)
        mock_mono.side_effect = [0.0, 5.0]

        status_done = MagicMock()
        status_done.state = MagicMock()
        status_done.state.value = "SUCCEEDED"

        with patch.object(svc, "get_status", return_value=status_done):
            svc.wait("test-job", "default", timeout=3600)

    @patch("kuberay_sdk.services.job_service.time.sleep")
    @patch("kuberay_sdk.services.job_service.time.monotonic")
    def test_job_callback_exception_caught(self, mock_mono: MagicMock, mock_sleep: MagicMock) -> None:
        """Callback exception should be caught and not propagate in job wait."""
        from kuberay_sdk.services.job_service import JobService

        mock_api = MagicMock()
        mock_config = MagicMock()
        svc = JobService(mock_api, mock_config)
        mock_mono.side_effect = [0.0, 5.0, 10.0]

        status_running = MagicMock()
        status_running.state = MagicMock()
        status_running.state.value = "RUNNING"

        status_done = MagicMock()
        status_done.state = MagicMock()
        status_done.state.value = "SUCCEEDED"

        def bad_callback(status: ProgressStatus) -> None:
            raise RuntimeError("callback error")

        with patch.object(svc, "get_status", side_effect=[status_running, status_done]):
            svc.wait(
                "test-job",
                "default",
                timeout=3600,
                progress_callback=bad_callback,
            )


class TestDashboardJobWaitProgress:
    @patch("kuberay_sdk.services.job_service.time.sleep")
    @patch("kuberay_sdk.services.job_service.time.monotonic")
    def test_callback_invoked_during_dashboard_wait(self, mock_mono: MagicMock, mock_sleep: MagicMock) -> None:
        """Progress callback should be called for dashboard job wait."""
        from kuberay_sdk.services.job_service import JobService

        mock_api = MagicMock()
        mock_config = MagicMock()
        svc = JobService(mock_api, mock_config)

        mock_mono.side_effect = [0.0, 5.0, 10.0]

        mock_dc = MagicMock()
        mock_dc.get_job_status.side_effect = [
            {"status": "RUNNING", "message": "running"},
            {"status": "SUCCEEDED", "message": "done"},
        ]

        callback = MagicMock()
        svc.wait_dashboard_job(
            mock_dc,
            "raysubmit_abc",
            timeout=3600,
            progress_callback=callback,
        )
        assert callback.call_count >= 1
        first_call_arg = callback.call_args_list[0][0][0]
        assert isinstance(first_call_arg, ProgressStatus)

    @patch("kuberay_sdk.services.job_service.time.sleep")
    @patch("kuberay_sdk.services.job_service.time.monotonic")
    def test_dashboard_callback_exception_caught(self, mock_mono: MagicMock, mock_sleep: MagicMock) -> None:
        """Callback exception should be caught in dashboard job wait."""
        from kuberay_sdk.services.job_service import JobService

        mock_api = MagicMock()
        mock_config = MagicMock()
        svc = JobService(mock_api, mock_config)

        mock_mono.side_effect = [0.0, 5.0, 10.0]

        mock_dc = MagicMock()
        mock_dc.get_job_status.side_effect = [
            {"status": "RUNNING", "message": "running"},
            {"status": "SUCCEEDED", "message": "done"},
        ]

        def bad_callback(status: ProgressStatus) -> None:
            raise RuntimeError("callback error")

        svc.wait_dashboard_job(
            mock_dc,
            "raysubmit_abc",
            timeout=3600,
            progress_callback=bad_callback,
        )


class TestTimeoutErrorLastStatus:
    def test_timeout_error_has_last_status(self) -> None:
        """TimeoutError should accept and store last_status."""
        from kuberay_sdk.errors import TimeoutError

        progress = ProgressStatus(state="CREATING", elapsed_seconds=300.0)
        err = TimeoutError("wait_until_ready(test)", 300, last_status=progress)
        assert err.last_status is progress
        assert err.last_status.state == "CREATING"

    def test_timeout_error_default_last_status_none(self) -> None:
        """TimeoutError should default last_status to None."""
        from kuberay_sdk.errors import TimeoutError

        err = TimeoutError("op", 60)
        assert err.last_status is None

    def test_timeout_error_preserves_remediation(self) -> None:
        """TimeoutError should still have remediation from US1."""
        from kuberay_sdk.errors import TimeoutError

        err = TimeoutError("op", 60, last_status=None)
        assert err.remediation != ""

    @patch("kuberay_sdk.services.cluster_service.time.sleep")
    @patch("kuberay_sdk.services.cluster_service.time.monotonic")
    def test_timeout_error_includes_last_status_on_timeout(self, mock_mono: MagicMock, mock_sleep: MagicMock) -> None:
        """When a wait times out, the TimeoutError should include last_status."""
        from kuberay_sdk.errors import TimeoutError
        from kuberay_sdk.services.cluster_service import ClusterService

        mock_api = MagicMock()
        mock_config = MagicMock()
        svc = ClusterService(mock_api, mock_config)

        # Start at 0, then exceed timeout
        mock_mono.side_effect = [0.0, 5.0, 301.0]

        status_creating = MagicMock()
        status_creating.state = "CREATING"
        status_creating.head_ready = False

        with patch.object(svc, "get_status", return_value=status_creating):
            with pytest.raises(TimeoutError) as exc_info:
                svc.wait_until_ready("test", "default", timeout=300)
            assert exc_info.value.last_status is not None
            assert isinstance(exc_info.value.last_status, ProgressStatus)


class TestHandleProgressCallback:
    """Test that handle classes pass progress_callback through to services."""

    def test_cluster_handle_passes_callback(self) -> None:
        """ClusterHandle.wait_until_ready should accept and pass progress_callback."""
        from kuberay_sdk.client import ClusterHandle

        mock_client = MagicMock()
        handle = ClusterHandle("test", "default", mock_client)

        callback = MagicMock()
        with patch("kuberay_sdk.services.cluster_service.ClusterService.wait_until_ready") as mock_wait:
            handle.wait_until_ready(timeout=300, progress_callback=callback)
            mock_wait.assert_called_once()
            call_kwargs = mock_wait.call_args
            assert call_kwargs.kwargs.get("timeout") == 300
            assert call_kwargs.kwargs.get("progress_callback") is callback

    def test_job_handle_passes_callback_crd(self) -> None:
        """JobHandle.wait should accept and pass progress_callback for CRD mode."""
        from kuberay_sdk.client import JobHandle

        mock_client = MagicMock()
        handle = JobHandle("test-job", "default", mock_client, mode="CRD")

        callback = MagicMock()
        with patch("kuberay_sdk.services.job_service.JobService.wait") as mock_wait:
            handle.wait(timeout=3600, progress_callback=callback)
            mock_wait.assert_called_once()
            call_kwargs = mock_wait.call_args
            assert call_kwargs.kwargs.get("timeout") == 3600
            assert call_kwargs.kwargs.get("progress_callback") is callback

    def test_job_handle_passes_callback_dashboard(self) -> None:
        """JobHandle.wait should pass progress_callback for Dashboard mode."""
        from kuberay_sdk.client import JobHandle

        mock_client = MagicMock()
        handle = JobHandle(
            "job-id",
            "default",
            mock_client,
            mode="DASHBOARD",
            dashboard_url="http://localhost:8265",
        )

        callback = MagicMock()
        with patch("kuberay_sdk.services.job_service.JobService.wait_dashboard_job") as mock_wait:
            handle.wait(timeout=3600, progress_callback=callback)
            mock_wait.assert_called_once()
            call_kwargs = mock_wait.call_args
            assert call_kwargs.kwargs.get("timeout") == 3600
            assert call_kwargs.kwargs.get("progress_callback") is callback
