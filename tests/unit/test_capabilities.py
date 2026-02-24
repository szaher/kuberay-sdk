"""Unit tests for capability discovery (US11).

T046: ClusterCapabilities model tests
T047: Capability detection logic tests
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from kuberay_sdk.models.capabilities import ClusterCapabilities

# ──────────────────────────────────────────────
# T046: ClusterCapabilities model
# ──────────────────────────────────────────────


class TestClusterCapabilitiesModel:
    """Tests for ClusterCapabilities pydantic model defaults and construction."""

    def test_default_values(self) -> None:
        caps = ClusterCapabilities()
        assert caps.kuberay_installed is False
        assert caps.kuberay_version is None
        assert caps.gpu_available is None
        assert caps.gpu_types == []
        assert caps.kueue_available is None
        assert caps.openshift is None

    def test_all_available(self) -> None:
        caps = ClusterCapabilities(
            kuberay_installed=True,
            kuberay_version="v1.2.0",
            gpu_available=True,
            gpu_types=["nvidia.com/gpu"],
            kueue_available=True,
            openshift=True,
        )
        assert caps.kuberay_installed is True
        assert caps.kuberay_version == "v1.2.0"
        assert caps.gpu_available is True
        assert caps.gpu_types == ["nvidia.com/gpu"]
        assert caps.kueue_available is True
        assert caps.openshift is True

    def test_nothing_available(self) -> None:
        caps = ClusterCapabilities(
            kuberay_installed=False,
            kuberay_version=None,
            gpu_available=False,
            gpu_types=[],
            kueue_available=False,
            openshift=False,
        )
        assert caps.kuberay_installed is False
        assert caps.kuberay_version is None
        assert caps.gpu_available is False
        assert caps.gpu_types == []
        assert caps.kueue_available is False
        assert caps.openshift is False

    def test_multiple_gpu_types(self) -> None:
        caps = ClusterCapabilities(
            gpu_available=True,
            gpu_types=["nvidia.com/gpu", "amd.com/gpu"],
        )
        assert len(caps.gpu_types) == 2
        assert "nvidia.com/gpu" in caps.gpu_types
        assert "amd.com/gpu" in caps.gpu_types

    def test_none_means_unknown(self) -> None:
        """None fields indicate 'unknown' (e.g. RBAC prevented detection)."""
        caps = ClusterCapabilities(
            kuberay_installed=True,
            gpu_available=None,
            kueue_available=None,
            openshift=None,
        )
        assert caps.gpu_available is None
        assert caps.kueue_available is None
        assert caps.openshift is None

    def test_serialization_round_trip(self) -> None:
        """Model should survive dict serialization and deserialization."""
        caps = ClusterCapabilities(
            kuberay_installed=True,
            kuberay_version="v1.2.0",
            gpu_available=True,
            gpu_types=["nvidia.com/gpu"],
            kueue_available=False,
            openshift=True,
        )
        data = caps.model_dump()
        restored = ClusterCapabilities(**data)
        assert restored == caps


# ──────────────────────────────────────────────
# T047: Capability detection logic
# ──────────────────────────────────────────────


def _make_crd(name: str, labels: dict[str, str] | None = None, annotations: dict[str, str] | None = None) -> MagicMock:
    """Create a mock CRD object."""
    crd = MagicMock()
    crd.metadata.name = name
    crd.metadata.labels = labels
    crd.metadata.annotations = annotations
    return crd


def _make_node(allocatable: dict[str, str] | None = None) -> MagicMock:
    """Create a mock K8s node object."""
    node = MagicMock()
    node.status.allocatable = allocatable or {}
    return node


def _make_api_exception(status: int) -> Exception:
    """Create a mock K8s API exception with a status code."""
    exc = Exception(f"Forbidden: {status}")
    exc.status = status  # type: ignore[attr-defined]
    return exc


class TestDetectCapabilities:
    """Tests for the detect_capabilities() function."""

    def test_full_capability_cluster(self) -> None:
        """All CRDs present, GPU nodes available."""
        from kuberay_sdk.capabilities import detect_capabilities

        api_client = MagicMock()

        # Mock ApiextensionsV1Api.list_custom_resource_definition
        crds = MagicMock()
        crds.items = [
            _make_crd(
                "rayclusters.ray.io",
                labels={"app.kubernetes.io/version": "v1.2.0"},
            ),
            _make_crd("workloads.kueue.x-k8s.io"),
            _make_crd("routes.route.openshift.io"),
        ]

        # Mock CoreV1Api.list_node
        nodes = MagicMock()
        nodes.items = [
            _make_node({"cpu": "8", "memory": "32Gi", "nvidia.com/gpu": "4"}),
        ]

        with (
            patch("kuberay_sdk.capabilities.ApiextensionsV1Api") as mock_ext_cls,
            patch("kuberay_sdk.capabilities.CoreV1Api") as mock_core_cls,
        ):
            mock_ext_cls.return_value.list_custom_resource_definition.return_value = crds
            mock_core_cls.return_value.list_node.return_value = nodes

            caps = detect_capabilities(api_client)

        assert caps.kuberay_installed is True
        assert caps.kuberay_version == "v1.2.0"
        assert caps.gpu_available is True
        assert "nvidia.com/gpu" in caps.gpu_types
        assert caps.kueue_available is True
        assert caps.openshift is True

    def test_minimal_cluster(self) -> None:
        """Only KubeRay CRD present, no GPU nodes."""
        from kuberay_sdk.capabilities import detect_capabilities

        api_client = MagicMock()

        crds = MagicMock()
        crds.items = [
            _make_crd("rayclusters.ray.io"),
        ]

        nodes = MagicMock()
        nodes.items = [
            _make_node({"cpu": "4", "memory": "16Gi"}),
        ]

        with (
            patch("kuberay_sdk.capabilities.ApiextensionsV1Api") as mock_ext_cls,
            patch("kuberay_sdk.capabilities.CoreV1Api") as mock_core_cls,
        ):
            mock_ext_cls.return_value.list_custom_resource_definition.return_value = crds
            mock_core_cls.return_value.list_node.return_value = nodes

            caps = detect_capabilities(api_client)

        assert caps.kuberay_installed is True
        assert caps.kuberay_version is None
        assert caps.gpu_available is False
        assert caps.gpu_types == []
        assert caps.kueue_available is False
        assert caps.openshift is False

    def test_no_kuberay_crd(self) -> None:
        """No KubeRay CRDs installed."""
        from kuberay_sdk.capabilities import detect_capabilities

        api_client = MagicMock()

        crds = MagicMock()
        crds.items = []

        nodes = MagicMock()
        nodes.items = [_make_node({"cpu": "4"})]

        with (
            patch("kuberay_sdk.capabilities.ApiextensionsV1Api") as mock_ext_cls,
            patch("kuberay_sdk.capabilities.CoreV1Api") as mock_core_cls,
        ):
            mock_ext_cls.return_value.list_custom_resource_definition.return_value = crds
            mock_core_cls.return_value.list_node.return_value = nodes

            caps = detect_capabilities(api_client)

        assert caps.kuberay_installed is False
        assert caps.kuberay_version is None

    def test_rbac_error_gpu_detection(self) -> None:
        """403 on node listing results in gpu_available=None."""
        from kuberay_sdk.capabilities import detect_capabilities

        api_client = MagicMock()

        crds = MagicMock()
        crds.items = [_make_crd("rayclusters.ray.io")]

        with (
            patch("kuberay_sdk.capabilities.ApiextensionsV1Api") as mock_ext_cls,
            patch("kuberay_sdk.capabilities.CoreV1Api") as mock_core_cls,
        ):
            mock_ext_cls.return_value.list_custom_resource_definition.return_value = crds
            mock_core_cls.return_value.list_node.side_effect = _make_api_exception(403)

            caps = detect_capabilities(api_client)

        assert caps.kuberay_installed is True
        assert caps.gpu_available is None
        assert caps.gpu_types == []

    def test_rbac_error_crd_listing(self) -> None:
        """403 on CRD listing results in kueue/openshift=None."""
        from kuberay_sdk.capabilities import detect_capabilities

        api_client = MagicMock()

        with (
            patch("kuberay_sdk.capabilities.ApiextensionsV1Api") as mock_ext_cls,
            patch("kuberay_sdk.capabilities.CoreV1Api") as mock_core_cls,
        ):
            mock_ext_cls.return_value.list_custom_resource_definition.side_effect = _make_api_exception(403)
            mock_core_cls.return_value.list_node.return_value = MagicMock(items=[])

            caps = detect_capabilities(api_client)

        assert caps.kueue_available is None
        assert caps.openshift is None

    def test_network_error_raises_kuberay_error(self) -> None:
        """Non-RBAC errors on CRD listing raise KubeRayError."""
        from kuberay_sdk.capabilities import detect_capabilities
        from kuberay_sdk.errors import KubeRayError

        api_client = MagicMock()

        with (
            patch("kuberay_sdk.capabilities.ApiextensionsV1Api") as mock_ext_cls,
            patch("kuberay_sdk.capabilities.CoreV1Api"),
        ):
            exc = Exception("Connection refused")
            mock_ext_cls.return_value.list_custom_resource_definition.side_effect = exc

            with pytest.raises(KubeRayError, match="Failed to discover cluster capabilities"):
                detect_capabilities(api_client)

    def test_kuberay_version_from_annotations(self) -> None:
        """Version extracted from CRD annotations when labels don't have it."""
        from kuberay_sdk.capabilities import detect_capabilities

        api_client = MagicMock()

        crds = MagicMock()
        crds.items = [
            _make_crd(
                "rayclusters.ray.io",
                labels=None,
                annotations={"controller-gen.kubebuilder.io/version": "v0.15.0"},
            ),
        ]

        nodes = MagicMock()
        nodes.items = []

        with (
            patch("kuberay_sdk.capabilities.ApiextensionsV1Api") as mock_ext_cls,
            patch("kuberay_sdk.capabilities.CoreV1Api") as mock_core_cls,
        ):
            mock_ext_cls.return_value.list_custom_resource_definition.return_value = crds
            mock_core_cls.return_value.list_node.return_value = nodes

            caps = detect_capabilities(api_client)

        assert caps.kuberay_installed is True
        assert caps.kuberay_version == "v0.15.0"

    def test_gpu_with_zero_quantity_not_counted(self) -> None:
        """GPU resources with quantity '0' should not count."""
        from kuberay_sdk.capabilities import detect_capabilities

        api_client = MagicMock()

        crds = MagicMock()
        crds.items = [_make_crd("rayclusters.ray.io")]

        nodes = MagicMock()
        nodes.items = [
            _make_node({"cpu": "4", "nvidia.com/gpu": "0"}),
        ]

        with (
            patch("kuberay_sdk.capabilities.ApiextensionsV1Api") as mock_ext_cls,
            patch("kuberay_sdk.capabilities.CoreV1Api") as mock_core_cls,
        ):
            mock_ext_cls.return_value.list_custom_resource_definition.return_value = crds
            mock_core_cls.return_value.list_node.return_value = nodes

            caps = detect_capabilities(api_client)

        assert caps.gpu_available is False
        assert caps.gpu_types == []

    def test_multiple_gpu_types_across_nodes(self) -> None:
        """Multiple GPU types across different nodes should all be detected."""
        from kuberay_sdk.capabilities import detect_capabilities

        api_client = MagicMock()

        crds = MagicMock()
        crds.items = [_make_crd("rayclusters.ray.io")]

        nodes = MagicMock()
        nodes.items = [
            _make_node({"cpu": "4", "nvidia.com/gpu": "2"}),
            _make_node({"cpu": "4", "amd.com/gpu": "1"}),
        ]

        with (
            patch("kuberay_sdk.capabilities.ApiextensionsV1Api") as mock_ext_cls,
            patch("kuberay_sdk.capabilities.CoreV1Api") as mock_core_cls,
        ):
            mock_ext_cls.return_value.list_custom_resource_definition.return_value = crds
            mock_core_cls.return_value.list_node.return_value = nodes

            caps = detect_capabilities(api_client)

        assert caps.gpu_available is True
        assert sorted(caps.gpu_types) == ["amd.com/gpu", "nvidia.com/gpu"]

    def test_non_rbac_gpu_error_sets_none(self) -> None:
        """Non-RBAC errors during GPU detection set gpu_available=None (warning logged)."""
        from kuberay_sdk.capabilities import detect_capabilities

        api_client = MagicMock()

        crds = MagicMock()
        crds.items = [_make_crd("rayclusters.ray.io")]

        with (
            patch("kuberay_sdk.capabilities.ApiextensionsV1Api") as mock_ext_cls,
            patch("kuberay_sdk.capabilities.CoreV1Api") as mock_core_cls,
        ):
            mock_ext_cls.return_value.list_custom_resource_definition.return_value = crds
            mock_core_cls.return_value.list_node.side_effect = Exception("node list failed")

            caps = detect_capabilities(api_client)

        assert caps.gpu_available is None
        assert caps.gpu_types == []


# ──────────────────────────────────────────────
# T047: Client integration tests for get_capabilities
# ──────────────────────────────────────────────


class TestKubeRayClientGetCapabilities:
    """Test get_capabilities() on KubeRayClient."""

    def test_sync_client_get_capabilities(self) -> None:
        """KubeRayClient.get_capabilities() delegates to detect_capabilities."""
        with (
            patch("kuberay_sdk.client.get_k8s_client"),
            patch("kuberay_sdk.client.check_kuberay_crds"),
            patch("kubernetes.client.CustomObjectsApi"),
            patch("kuberay_sdk.capabilities.detect_capabilities") as mock_detect,
        ):
            from kuberay_sdk.client import KubeRayClient

            expected = ClusterCapabilities(kuberay_installed=True, kuberay_version="v1.0.0")
            mock_detect.return_value = expected

            client = KubeRayClient()
            result = client.get_capabilities()

            assert result == expected
            mock_detect.assert_called_once_with(client._api_client)


class TestAsyncKubeRayClientGetCapabilities:
    """Test get_capabilities() on AsyncKubeRayClient."""

    @pytest.mark.asyncio
    async def test_async_client_get_capabilities(self) -> None:
        """AsyncKubeRayClient.get_capabilities() delegates to detect_capabilities via _run_sync."""
        with (
            patch("kuberay_sdk.async_client.get_k8s_client"),
            patch("kuberay_sdk.async_client.check_kuberay_crds"),
            patch("kubernetes.client.CustomObjectsApi"),
            patch("kuberay_sdk.capabilities.detect_capabilities") as mock_detect,
        ):
            from kuberay_sdk.async_client import AsyncKubeRayClient

            expected = ClusterCapabilities(kuberay_installed=True, kuberay_version="v1.0.0")
            mock_detect.return_value = expected

            client = AsyncKubeRayClient()
            result = await client.get_capabilities()

            assert result == expected
