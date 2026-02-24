"""Unit tests for compound operations (US8: T034)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestCreateClusterAndSubmitJob:
    """Test the create_cluster_and_submit_job compound operation."""

    def test_returns_job_handle(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import JobHandle, KubeRayClient

            client = KubeRayClient()

            # Mock the create_cluster, wait_until_ready, and submit_job chain
            with (
                patch.object(client, "create_cluster") as mock_create,
            ):
                mock_cluster = MagicMock()
                mock_create.return_value = mock_cluster
                mock_cluster.wait_until_ready.return_value = None
                mock_job = MagicMock(spec=JobHandle)
                mock_cluster.submit_job.return_value = mock_job

                result = client.create_cluster_and_submit_job(
                    "my-cluster",
                    entrypoint="python train.py",
                    workers=4,
                )

                assert result is mock_job

    def test_calls_in_correct_order(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient

            client = KubeRayClient()
            call_order: list[str] = []

            mock_cluster = MagicMock()

            def track_create(*args, **kwargs):
                call_order.append("create_cluster")
                return mock_cluster

            def track_wait(*args, **kwargs):
                call_order.append("wait_until_ready")

            def track_submit(*args, **kwargs):
                call_order.append("submit_job")
                return MagicMock()

            with patch.object(client, "create_cluster", side_effect=track_create):
                mock_cluster.wait_until_ready.side_effect = track_wait
                mock_cluster.submit_job.side_effect = track_submit

                client.create_cluster_and_submit_job(
                    "my-cluster",
                    entrypoint="python train.py",
                )

            assert call_order == ["create_cluster", "wait_until_ready", "submit_job"]

    def test_timeout_raises_but_does_not_delete_cluster(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient

            client = KubeRayClient()

            mock_cluster = MagicMock()
            mock_cluster.wait_until_ready.side_effect = TimeoutError("Cluster not ready")

            with patch.object(client, "create_cluster", return_value=mock_cluster):
                with pytest.raises(TimeoutError) as exc_info:
                    client.create_cluster_and_submit_job(
                        "my-cluster",
                        entrypoint="python train.py",
                        wait_timeout=10,
                    )

                # Cluster should NOT be deleted
                mock_cluster.delete.assert_not_called()
                # Error should have cluster handle attached
                assert hasattr(exc_info.value, "cluster")
                assert exc_info.value.cluster is mock_cluster

    def test_error_includes_cluster_handle(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient

            client = KubeRayClient()

            mock_cluster = MagicMock()
            mock_cluster.wait_until_ready.side_effect = RuntimeError("Something broke")

            with patch.object(client, "create_cluster", return_value=mock_cluster):
                with pytest.raises(RuntimeError) as exc_info:
                    client.create_cluster_and_submit_job(
                        "my-cluster",
                        entrypoint="python train.py",
                    )

                assert exc_info.value.cluster is mock_cluster

    def test_passes_preset_to_create_cluster(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient

            client = KubeRayClient()

            mock_cluster = MagicMock()
            mock_cluster.submit_job.return_value = MagicMock()

            with patch.object(client, "create_cluster", return_value=mock_cluster) as mock_create:
                client.create_cluster_and_submit_job(
                    "my-cluster",
                    entrypoint="python train.py",
                    preset="dev",
                )

                # Verify preset was passed through
                _, kwargs = mock_create.call_args
                assert kwargs["preset"] == "dev"

    def test_passes_runtime_env_to_submit_job(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient

            client = KubeRayClient()

            mock_cluster = MagicMock()
            mock_cluster.submit_job.return_value = MagicMock()
            runtime = {"pip": ["torch"]}

            with patch.object(client, "create_cluster", return_value=mock_cluster):
                client.create_cluster_and_submit_job(
                    "my-cluster",
                    entrypoint="python train.py",
                    runtime_env=runtime,
                )

                mock_cluster.submit_job.assert_called_once_with(
                    entrypoint="python train.py",
                    runtime_env=runtime,
                )
