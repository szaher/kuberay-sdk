"""Unit tests for KubeRayClient and AsyncKubeRayClient (T073)."""

from __future__ import annotations

import asyncio
import inspect
from unittest.mock import MagicMock, patch


class TestKubeRayClientInit:
    """Test KubeRayClient initialization."""

    def test_creates_with_default_config(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient

            client = KubeRayClient()
            assert client._config is not None

    def test_creates_with_custom_config(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient
            from kuberay_sdk.config import SDKConfig

            config = SDKConfig(namespace="custom-ns")
            client = KubeRayClient(config=config)
            assert client._config.namespace == "custom-ns"

    def test_checks_kuberay_crds_on_init(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds") as mock_check:
            from kuberay_sdk.client import KubeRayClient

            KubeRayClient()
            mock_check.assert_called_once()


class TestAsyncClientMethodSignatures:
    """Verify AsyncKubeRayClient has identical method signatures to KubeRayClient (FR-041)."""

    def test_create_cluster_params_match(self) -> None:
        from kuberay_sdk.async_client import AsyncKubeRayClient
        from kuberay_sdk.client import KubeRayClient

        sync_sig = inspect.signature(KubeRayClient.create_cluster)
        async_sig = inspect.signature(AsyncKubeRayClient.create_cluster)

        sync_params = {k: v for k, v in sync_sig.parameters.items() if k != "self"}
        async_params = {k: v for k, v in async_sig.parameters.items() if k != "self"}

        assert set(sync_params.keys()) == set(async_params.keys()), (
            f"Parameter names differ: sync={set(sync_params.keys())}, async={set(async_params.keys())}"
        )

    def test_create_job_params_match(self) -> None:
        from kuberay_sdk.async_client import AsyncKubeRayClient
        from kuberay_sdk.client import KubeRayClient

        sync_sig = inspect.signature(KubeRayClient.create_job)
        async_sig = inspect.signature(AsyncKubeRayClient.create_job)

        sync_params = set(sync_sig.parameters.keys()) - {"self"}
        async_params = set(async_sig.parameters.keys()) - {"self"}

        assert sync_params == async_params

    def test_create_service_params_match(self) -> None:
        from kuberay_sdk.async_client import AsyncKubeRayClient
        from kuberay_sdk.client import KubeRayClient

        sync_sig = inspect.signature(KubeRayClient.create_service)
        async_sig = inspect.signature(AsyncKubeRayClient.create_service)

        sync_params = set(sync_sig.parameters.keys()) - {"self"}
        async_params = set(async_sig.parameters.keys()) - {"self"}

        assert sync_params == async_params

    def test_get_cluster_params_match(self) -> None:
        from kuberay_sdk.async_client import AsyncKubeRayClient
        from kuberay_sdk.client import KubeRayClient

        sync_params = set(inspect.signature(KubeRayClient.get_cluster).parameters.keys()) - {"self"}
        async_params = set(inspect.signature(AsyncKubeRayClient.get_cluster).parameters.keys()) - {"self"}
        assert sync_params == async_params

    def test_list_clusters_params_match(self) -> None:
        from kuberay_sdk.async_client import AsyncKubeRayClient
        from kuberay_sdk.client import KubeRayClient

        sync_params = set(inspect.signature(KubeRayClient.list_clusters).parameters.keys()) - {"self"}
        async_params = set(inspect.signature(AsyncKubeRayClient.list_clusters).parameters.keys()) - {"self"}
        assert sync_params == async_params

    def test_get_job_params_match(self) -> None:
        from kuberay_sdk.async_client import AsyncKubeRayClient
        from kuberay_sdk.client import KubeRayClient

        sync_params = set(inspect.signature(KubeRayClient.get_job).parameters.keys()) - {"self"}
        async_params = set(inspect.signature(AsyncKubeRayClient.get_job).parameters.keys()) - {"self"}
        assert sync_params == async_params

    def test_list_jobs_params_match(self) -> None:
        from kuberay_sdk.async_client import AsyncKubeRayClient
        from kuberay_sdk.client import KubeRayClient

        sync_params = set(inspect.signature(KubeRayClient.list_jobs).parameters.keys()) - {"self"}
        async_params = set(inspect.signature(AsyncKubeRayClient.list_jobs).parameters.keys()) - {"self"}
        assert sync_params == async_params

    def test_get_service_params_match(self) -> None:
        from kuberay_sdk.async_client import AsyncKubeRayClient
        from kuberay_sdk.client import KubeRayClient

        sync_params = set(inspect.signature(KubeRayClient.get_service).parameters.keys()) - {"self"}
        async_params = set(inspect.signature(AsyncKubeRayClient.get_service).parameters.keys()) - {"self"}
        assert sync_params == async_params

    def test_list_services_params_match(self) -> None:
        from kuberay_sdk.async_client import AsyncKubeRayClient
        from kuberay_sdk.client import KubeRayClient

        sync_params = set(inspect.signature(KubeRayClient.list_services).parameters.keys()) - {"self"}
        async_params = set(inspect.signature(AsyncKubeRayClient.list_services).parameters.keys()) - {"self"}
        assert sync_params == async_params

    def test_all_async_methods_are_coroutines(self) -> None:
        from kuberay_sdk.async_client import AsyncKubeRayClient

        public_methods = [
            "create_cluster",
            "get_cluster",
            "list_clusters",
            "create_job",
            "get_job",
            "list_jobs",
            "create_service",
            "get_service",
            "list_services",
        ]
        for method_name in public_methods:
            method = getattr(AsyncKubeRayClient, method_name)
            assert asyncio.iscoroutinefunction(method), f"{method_name} is not a coroutine"
