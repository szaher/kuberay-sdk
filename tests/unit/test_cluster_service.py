"""Unit tests for ClusterService (T016, T017).

Tests verify that ClusterService correctly:
- Generates CRD dicts and calls CustomObjectsApi for CRUD operations
- Handles simple and advanced (multi-group) cluster creation
- Implements idempotent create semantics
- Polls for readiness
- Scales and deletes clusters

All Kubernetes API calls are mocked via ``mock_custom_objects_api`` from
conftest.py.

TDD: these tests are written BEFORE ``kuberay_sdk.services.cluster_service``
and ``kuberay_sdk.models.cluster`` are implemented.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from kuberay_sdk.config import SDKConfig
from kuberay_sdk.errors import (
    ClusterNotFoundError,
    ResourceConflictError,
    TimeoutError,
    ValidationError,
)

# ── Imports that will fail until implementation exists ──
from kuberay_sdk.models.cluster import (
    ClusterStatus,
    HeadNodeConfig,
    WorkerGroup,
)
from kuberay_sdk.services.cluster_service import ClusterService

# conftest helpers
from tests.conftest import make_raycluster_cr

# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture()
def sdk_config() -> SDKConfig:
    """Default SDK config for tests."""
    return SDKConfig(namespace="default")


@pytest.fixture()
def cluster_service(
    mock_custom_objects_api: MagicMock,
    sdk_config: SDKConfig,
) -> ClusterService:
    """ClusterService with mocked CustomObjectsApi."""
    return ClusterService(mock_custom_objects_api, sdk_config)


# ──────────────────────────────────────────────
# create_cluster — simple params
# ──────────────────────────────────────────────


class TestCreateClusterSimple:
    """Test create_cluster with simple (flat) parameters."""

    def test_create_calls_k8s_api(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        cluster_service.create(
            name="test-cluster",
            namespace="default",
            workers=2,
            cpus_per_worker=1.0,
            gpus_per_worker=0,
            memory_per_worker="2Gi",
        )
        mock_custom_objects_api.create_namespaced_custom_object.assert_called_once()

    def test_create_passes_correct_group_version(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        cluster_service.create(
            name="test-cluster",
            namespace="default",
            workers=1,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        assert call_kwargs[1]["group"] == "ray.io" or call_kwargs[0][0] == "ray.io"
        # Check version and plural
        args = call_kwargs[1] if call_kwargs[1] else {}
        positional = call_kwargs[0] if call_kwargs[0] else ()
        # The call should include version="v1" and plural="rayclusters"
        all_args = list(positional) + list(args.values())
        assert "v1" in all_args or args.get("version") == "v1"

    def test_create_generates_correct_crd_name(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        cluster_service.create(
            name="my-test-cluster",
            namespace="ml-namespace",
            workers=2,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        # Extract the body dict from the call
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        assert body["metadata"]["name"] == "my-test-cluster"
        assert body["metadata"]["namespace"] == "ml-namespace"

    def test_create_generates_correct_worker_count(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        cluster_service.create(
            name="test",
            namespace="default",
            workers=5,
            cpus_per_worker=2.0,
            memory_per_worker="4Gi",
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        group = body["spec"]["workerGroupSpecs"][0]
        assert group["replicas"] == 5

    def test_create_generates_correct_resources(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        cluster_service.create(
            name="test",
            namespace="default",
            workers=1,
            cpus_per_worker=4.0,
            memory_per_worker="8Gi",
            gpus_per_worker=2,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        container = body["spec"]["workerGroupSpecs"][0]["template"]["spec"]["containers"][0]
        assert container["resources"]["requests"]["cpu"] == "4"
        assert container["resources"]["requests"]["memory"] == "8Gi"
        assert container["resources"]["requests"]["nvidia.com/gpu"] == "2"


# ──────────────────────────────────────────────
# create_cluster — advanced params (worker_groups)
# ──────────────────────────────────────────────


class TestCreateClusterAdvanced:
    """Test create_cluster with explicit WorkerGroup objects."""

    def test_multi_group_generates_multiple_specs(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        groups = [
            WorkerGroup(name="cpu-pool", replicas=4, cpus=4.0, memory="8Gi"),
            WorkerGroup(name="gpu-pool", replicas=2, cpus=2.0, memory="16Gi", gpus=1),
        ]
        cluster_service.create(
            name="hetero-cluster",
            namespace="default",
            worker_groups=groups,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        worker_specs = body["spec"]["workerGroupSpecs"]
        assert len(worker_specs) == 2

    def test_multi_group_names_preserved(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        groups = [
            WorkerGroup(name="cpu-pool", replicas=4),
            WorkerGroup(name="gpu-pool", replicas=2, gpus=1),
        ]
        cluster_service.create(
            name="multi",
            namespace="default",
            worker_groups=groups,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        names = [g["groupName"] for g in body["spec"]["workerGroupSpecs"]]
        assert names == ["cpu-pool", "gpu-pool"]

    def test_multi_group_resources_per_group(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        groups = [
            WorkerGroup(name="small", replicas=4, cpus=1.0, memory="2Gi"),
            WorkerGroup(name="large", replicas=2, cpus=8.0, memory="32Gi", gpus=4),
        ]
        cluster_service.create(
            name="multi",
            namespace="default",
            worker_groups=groups,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        small_container = body["spec"]["workerGroupSpecs"][0]["template"]["spec"]["containers"][0]
        large_container = body["spec"]["workerGroupSpecs"][1]["template"]["spec"]["containers"][0]
        assert small_container["resources"]["requests"]["cpu"] == "1"
        assert large_container["resources"]["requests"]["cpu"] == "8"
        assert "nvidia.com/gpu" not in small_container["resources"]["requests"]
        assert large_container["resources"]["requests"]["nvidia.com/gpu"] == "4"

    def test_head_config_applied(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        head = HeadNodeConfig(cpus=2.0, memory="4Gi")
        cluster_service.create(
            name="with-head",
            namespace="default",
            workers=1,
            head=head,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        head_container = body["spec"]["headGroupSpec"]["template"]["spec"]["containers"][0]
        assert head_container["resources"]["requests"]["cpu"] == "2"
        assert head_container["resources"]["requests"]["memory"] == "4Gi"


# ──────────────────────────────────────────────
# get_cluster → ClusterStatus
# ──────────────────────────────────────────────


class TestGetCluster:
    """Test get_status returns a ClusterStatus object."""

    def test_get_returns_cluster_status(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = make_raycluster_cr(
            name="my-cluster", namespace="default", state="ready"
        )
        status = cluster_service.get_status("my-cluster", "default")
        assert isinstance(status, ClusterStatus)
        assert status.name == "my-cluster"
        assert status.namespace == "default"

    def test_get_status_head_ready(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = make_raycluster_cr(head_ready=True)
        status = cluster_service.get_status("test-cluster", "default")
        assert status.head_ready is True

    def test_get_status_head_not_ready(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = make_raycluster_cr(head_ready=False)
        status = cluster_service.get_status("test-cluster", "default")
        assert status.head_ready is False

    def test_get_status_workers_desired(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = make_raycluster_cr(workers=3)
        status = cluster_service.get_status("test-cluster", "default")
        assert status.workers_desired == 3

    def test_get_status_ray_version(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = make_raycluster_cr(ray_version="2.39.0")
        status = cluster_service.get_status("test-cluster", "default")
        assert status.ray_version == "2.39.0"

    def test_get_nonexistent_cluster_raises(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        """Getting a cluster that does not exist should raise ClusterNotFoundError."""

        api_exception = type("ApiException", (Exception,), {"status": 404, "reason": "Not Found"})()
        mock_custom_objects_api.get_namespaced_custom_object.side_effect = api_exception
        with pytest.raises(ClusterNotFoundError):
            cluster_service.get_status("nonexistent", "default")


# ──────────────────────────────────────────────
# list_clusters → list[ClusterStatus]
# ──────────────────────────────────────────────


class TestListClusters:
    """Test list returns a list of ClusterStatus objects."""

    def test_list_empty(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.list_namespaced_custom_object.return_value = {"items": []}
        result = cluster_service.list("default")
        assert result == []

    def test_list_returns_cluster_statuses(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.list_namespaced_custom_object.return_value = {
            "items": [
                make_raycluster_cr(name="cluster-1"),
                make_raycluster_cr(name="cluster-2"),
            ]
        }
        result = cluster_service.list("default")
        assert len(result) == 2
        assert all(isinstance(s, ClusterStatus) for s in result)

    def test_list_status_names(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.list_namespaced_custom_object.return_value = {
            "items": [
                make_raycluster_cr(name="alpha"),
                make_raycluster_cr(name="bravo"),
                make_raycluster_cr(name="charlie"),
            ]
        }
        result = cluster_service.list("default")
        names = [s.name for s in result]
        assert names == ["alpha", "bravo", "charlie"]

    def test_list_calls_correct_api(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        cluster_service.list("my-namespace")
        mock_custom_objects_api.list_namespaced_custom_object.assert_called_once()
        call_kwargs = mock_custom_objects_api.list_namespaced_custom_object.call_args
        # Verify namespace is passed
        args_and_kwargs = list(call_kwargs[0]) + list(call_kwargs[1].values())
        assert "my-namespace" in args_and_kwargs


# ──────────────────────────────────────────────
# scale_cluster
# ──────────────────────────────────────────────


class TestScaleCluster:
    """Test scale patches workerGroupSpecs replicas."""

    def test_scale_calls_patch_api(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        # First, set up get to return current cluster state
        mock_custom_objects_api.get_namespaced_custom_object.return_value = make_raycluster_cr(workers=2)
        cluster_service.scale("test-cluster", "default", 5)
        mock_custom_objects_api.patch_namespaced_custom_object.assert_called_once()

    def test_scale_updates_replicas(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = make_raycluster_cr(workers=2)
        cluster_service.scale("test-cluster", "default", 10)
        call_kwargs = mock_custom_objects_api.patch_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        # The patch should update workerGroupSpecs replicas
        worker_specs = body.get("spec", {}).get("workerGroupSpecs", [])
        if worker_specs:
            assert worker_specs[0]["replicas"] == 10

    def test_scale_to_zero_raises_or_allowed(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        """Scaling to zero workers may be invalid (depends on design)."""
        mock_custom_objects_api.get_namespaced_custom_object.return_value = make_raycluster_cr(workers=2)
        # Depending on implementation, this might raise or be allowed.
        # We test that it doesn't silently corrupt state.
        with pytest.raises((ValidationError, ValueError)):
            cluster_service.scale("test-cluster", "default", 0)


# ──────────────────────────────────────────────
# delete_cluster
# ──────────────────────────────────────────────


class TestDeleteCluster:
    """Test delete calls the correct K8s API."""

    def test_delete_calls_api(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        cluster_service.delete("test-cluster", "default")
        mock_custom_objects_api.delete_namespaced_custom_object.assert_called_once()

    def test_delete_passes_correct_name(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        cluster_service.delete("my-cluster", "ml-team")
        call_kwargs = mock_custom_objects_api.delete_namespaced_custom_object.call_args
        # Name and namespace should be in the call
        all_args = list(call_kwargs[0]) + list(call_kwargs[1].values())
        assert "my-cluster" in all_args
        assert "ml-team" in all_args

    def test_delete_nonexistent_cluster_raises(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        api_exception = type("ApiException", (Exception,), {"status": 404, "reason": "Not Found"})()
        mock_custom_objects_api.delete_namespaced_custom_object.side_effect = api_exception
        with pytest.raises(ClusterNotFoundError):
            cluster_service.delete("nonexistent", "default")


# ──────────────────────────────────────────────
# wait_until_ready
# ──────────────────────────────────────────────


class TestWaitUntilReady:
    """Test wait_until_ready polls until HeadPodReady condition is True."""

    def test_already_ready_returns_immediately(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = make_raycluster_cr(
            state="ready", head_ready=True
        )
        # Should not raise and should return quickly
        cluster_service.wait_until_ready("test-cluster", "default", timeout=5)

    def test_polls_until_ready(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        """Simulate cluster becoming ready after a few polls."""
        not_ready = make_raycluster_cr(state="creating", head_ready=False)
        ready = make_raycluster_cr(state="ready", head_ready=True)

        mock_custom_objects_api.get_namespaced_custom_object.side_effect = [
            not_ready,
            not_ready,
            ready,
        ]
        with patch("time.sleep"):  # Don't actually sleep in tests
            cluster_service.wait_until_ready("test-cluster", "default", timeout=60)

        # Should have polled 3 times
        assert mock_custom_objects_api.get_namespaced_custom_object.call_count == 3

    def test_timeout_raises(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        """If cluster never becomes ready, TimeoutError should be raised."""
        not_ready = make_raycluster_cr(state="creating", head_ready=False)
        mock_custom_objects_api.get_namespaced_custom_object.return_value = not_ready

        with patch("time.sleep"), pytest.raises(TimeoutError):
            cluster_service.wait_until_ready(
                "test-cluster",
                "default",
                timeout=0.01,
            )

    def test_wait_checks_head_pod_ready_condition(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        """Verify that wait specifically checks the HeadPodReady condition."""
        # Cluster has state=ready but HeadPodReady is False => not actually ready
        cr = make_raycluster_cr(state="ready", head_ready=False)
        cr_ready = make_raycluster_cr(state="ready", head_ready=True)

        mock_custom_objects_api.get_namespaced_custom_object.side_effect = [
            cr,
            cr_ready,
        ]
        with patch("time.sleep"):
            cluster_service.wait_until_ready("test-cluster", "default", timeout=60)

        assert mock_custom_objects_api.get_namespaced_custom_object.call_count == 2


# ──────────────────────────────────────────────
# Idempotent create
# ──────────────────────────────────────────────


class TestIdempotentCreate:
    """Test idempotent create semantics (T017).

    - Existing cluster with identical spec -> return handle (no error)
    - Existing cluster with different spec -> ResourceConflictError
    """

    def test_identical_spec_returns_without_error(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        """Creating a cluster that already exists with the same spec should succeed."""
        # Simulate K8s 409 Conflict on create
        api_exception = type(
            "ApiException",
            (Exception,),
            {"status": 409, "reason": "Conflict"},
        )()
        mock_custom_objects_api.create_namespaced_custom_object.side_effect = api_exception

        # When we fetch the existing cluster, it matches the requested spec
        existing_cr = make_raycluster_cr(
            name="test-cluster",
            namespace="default",
            workers=2,
            ray_version="2.41.0",
        )
        mock_custom_objects_api.get_namespaced_custom_object.return_value = existing_cr

        # Should NOT raise -- idempotent create succeeds
        cluster_service.create(
            name="test-cluster",
            namespace="default",
            workers=2,
            ray_version="2.41.0",
        )

    def test_different_spec_raises_resource_conflict(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        """Creating a cluster that already exists with a different spec should fail."""
        api_exception = type(
            "ApiException",
            (Exception,),
            {"status": 409, "reason": "Conflict"},
        )()
        mock_custom_objects_api.create_namespaced_custom_object.side_effect = api_exception

        # Existing cluster has different worker count
        existing_cr = make_raycluster_cr(
            name="test-cluster",
            namespace="default",
            workers=5,  # Different from what we request (2)
            ray_version="2.41.0",
        )
        mock_custom_objects_api.get_namespaced_custom_object.return_value = existing_cr

        with pytest.raises(ResourceConflictError):
            cluster_service.create(
                name="test-cluster",
                namespace="default",
                workers=2,  # Conflicts with existing (5)
                ray_version="2.41.0",
            )

    def test_different_ray_version_raises_conflict(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        """Different ray_version should trigger ResourceConflictError."""
        api_exception = type(
            "ApiException",
            (Exception,),
            {"status": 409, "reason": "Conflict"},
        )()
        mock_custom_objects_api.create_namespaced_custom_object.side_effect = api_exception

        existing_cr = make_raycluster_cr(
            name="test-cluster",
            namespace="default",
            workers=2,
            ray_version="2.39.0",  # Different version
        )
        mock_custom_objects_api.get_namespaced_custom_object.return_value = existing_cr

        with pytest.raises(ResourceConflictError):
            cluster_service.create(
                name="test-cluster",
                namespace="default",
                workers=2,
                ray_version="2.41.0",  # Conflicts with existing (2.39.0)
            )


# ──────────────────────────────────────────────
# create_cluster with labels and annotations
# ──────────────────────────────────────────────


class TestCreateClusterMetadata:
    """Test that labels and annotations are propagated to the CRD."""

    def test_labels_in_crd(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        cluster_service.create(
            name="labeled",
            namespace="default",
            workers=1,
            labels={"team": "ml", "project": "llm"},
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        assert body["metadata"]["labels"]["team"] == "ml"
        assert body["metadata"]["labels"]["project"] == "llm"

    def test_annotations_in_crd(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        cluster_service.create(
            name="annotated",
            namespace="default",
            workers=1,
            annotations={"description": "Test cluster"},
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        assert body["metadata"]["annotations"]["description"] == "Test cluster"


# ──────────────────────────────────────────────
# create_cluster with ray_version and image
# ──────────────────────────────────────────────


class TestCreateClusterImage:
    """Test ray_version and image handling."""

    def test_ray_version_sets_image(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        cluster_service.create(
            name="versioned",
            namespace="default",
            workers=1,
            ray_version="2.39.0",
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        head_image = body["spec"]["headGroupSpec"]["template"]["spec"]["containers"][0]["image"]
        worker_image = body["spec"]["workerGroupSpecs"][0]["template"]["spec"]["containers"][0]["image"]
        assert "2.39.0" in head_image
        assert "2.39.0" in worker_image

    def test_custom_image_overrides_version(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        cluster_service.create(
            name="custom-img",
            namespace="default",
            workers=1,
            image="my-registry.io/ray:custom",
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        head_image = body["spec"]["headGroupSpec"]["template"]["spec"]["containers"][0]["image"]
        assert head_image == "my-registry.io/ray:custom"
