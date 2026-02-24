"""Unit tests for handle __repr__ methods (US4)."""

from __future__ import annotations

from unittest.mock import MagicMock


class TestClusterHandleRepr:
    def test_repr_shows_name_and_namespace(self) -> None:
        from kuberay_sdk.client import ClusterHandle

        handle = ClusterHandle("my-cluster", "default", MagicMock())
        assert repr(handle) == "ClusterHandle(name='my-cluster', namespace='default')"

    def test_repr_with_custom_namespace(self) -> None:
        from kuberay_sdk.client import ClusterHandle

        handle = ClusterHandle("test", "ml-team", MagicMock())
        assert "ml-team" in repr(handle)


class TestJobHandleRepr:
    def test_repr_shows_name_namespace_mode(self) -> None:
        from kuberay_sdk.client import JobHandle

        handle = JobHandle("my-job", "default", MagicMock(), mode="DASHBOARD")
        assert repr(handle) == "JobHandle(name='my-job', namespace='default', mode='DASHBOARD')"

    def test_repr_crd_mode(self) -> None:
        from kuberay_sdk.client import JobHandle

        handle = JobHandle("my-job", "default", MagicMock(), mode="CRD")
        assert "mode='CRD'" in repr(handle)


class TestServiceHandleRepr:
    def test_repr_shows_name_and_namespace(self) -> None:
        from kuberay_sdk.client import ServiceHandle

        handle = ServiceHandle("my-svc", "default", MagicMock())
        assert repr(handle) == "ServiceHandle(name='my-svc', namespace='default')"


class TestAsyncHandleRepr:
    def test_async_cluster_repr(self) -> None:
        from kuberay_sdk.async_client import AsyncClusterHandle

        handle = AsyncClusterHandle("c1", "ns1", MagicMock())
        assert repr(handle) == "AsyncClusterHandle(name='c1', namespace='ns1')"

    def test_async_job_repr(self) -> None:
        from kuberay_sdk.async_client import AsyncJobHandle

        handle = AsyncJobHandle("j1", "ns1", MagicMock(), mode="CRD")
        assert repr(handle) == "AsyncJobHandle(name='j1', namespace='ns1', mode='CRD')"

    def test_async_service_repr(self) -> None:
        from kuberay_sdk.async_client import AsyncServiceHandle

        handle = AsyncServiceHandle("s1", "ns1", MagicMock())
        assert repr(handle) == "AsyncServiceHandle(name='s1', namespace='ns1')"
