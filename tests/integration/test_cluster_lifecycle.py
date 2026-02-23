"""Integration tests for full RayCluster lifecycle (T079).

Tests the complete cluster lifecycle: create -> wait_until_ready -> scale ->
status -> delete using mocked K8s API. Validates that all service operations
compose correctly in a realistic sequence.

All Kubernetes API calls are mocked via ``mock_custom_objects_api`` from
conftest.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from kuberay_sdk.config import SDKConfig
from kuberay_sdk.errors import ResourceConflictError
from kuberay_sdk.models.cluster import ClusterStatus, WorkerGroup
from kuberay_sdk.services.cluster_service import ClusterService
from tests.conftest import make_raycluster_cr

# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture()
def sdk_config() -> SDKConfig:
    """Default SDK config for integration tests."""
    return SDKConfig(namespace="default")


@pytest.fixture()
def cluster_service(
    mock_custom_objects_api: MagicMock,
    sdk_config: SDKConfig,
) -> ClusterService:
    """ClusterService with mocked CustomObjectsApi."""
    return ClusterService(mock_custom_objects_api, sdk_config)


# ──────────────────────────────────────────────
# T079: Full cluster lifecycle
# ──────────────────────────────────────────────


@pytest.mark.integration
class TestFullClusterLifecycle:
    """Full cluster lifecycle: create -> wait_until_ready -> scale -> status -> delete."""

    def test_full_cluster_lifecycle(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        """End-to-end cluster lifecycle through all CRUD operations.

        Steps:
            1. Create a cluster with 2 workers
            2. Wait until the cluster is ready (polls until RUNNING + head ready)
            3. Scale the cluster to 4 workers
            4. Get cluster status and verify the scaled state
            5. Delete the cluster
        """
        cluster_name = "lifecycle-cluster"
        namespace = "ml-team"

        # ── Step 1: Create ──
        created_cr = make_raycluster_cr(
            name=cluster_name, namespace=namespace, workers=2
        )
        mock_custom_objects_api.create_namespaced_custom_object.return_value = created_cr

        result = cluster_service.create(
            name=cluster_name,
            namespace=namespace,
            workers=2,
            cpus_per_worker=2.0,
            memory_per_worker="4Gi",
        )

        mock_custom_objects_api.create_namespaced_custom_object.assert_called_once()
        assert result["metadata"]["name"] == cluster_name
        assert result["metadata"]["namespace"] == namespace

        # ── Step 2: Wait until ready ──
        # Simulate: first poll returns "creating", second returns "ready" with head ready
        creating_cr = make_raycluster_cr(
            name=cluster_name, namespace=namespace,
            workers=2, state="creating", head_ready=False,
        )
        ready_cr = make_raycluster_cr(
            name=cluster_name, namespace=namespace,
            workers=2, state="ready", head_ready=True,
        )

        mock_custom_objects_api.get_namespaced_custom_object.side_effect = [
            creating_cr,
            ready_cr,
        ]

        with patch("time.sleep"):
            cluster_service.wait_until_ready(cluster_name, namespace, timeout=60)

        assert mock_custom_objects_api.get_namespaced_custom_object.call_count == 2

        # ── Step 3: Scale to 4 workers ──
        # get_namespaced_custom_object is called by scale() to read current spec.
        # Clear the exhausted side_effect before setting a new return_value.
        mock_custom_objects_api.get_namespaced_custom_object.reset_mock()
        mock_custom_objects_api.get_namespaced_custom_object.side_effect = None
        mock_custom_objects_api.get_namespaced_custom_object.return_value = ready_cr

        cluster_service.scale(cluster_name, namespace, workers=4)

        mock_custom_objects_api.patch_namespaced_custom_object.assert_called_once()
        patch_call = mock_custom_objects_api.patch_namespaced_custom_object.call_args
        patch_body = patch_call[1].get("body") or patch_call[0][-1]
        patched_workers = patch_body["spec"]["workerGroupSpecs"][0]
        assert patched_workers["replicas"] == 4
        assert patched_workers["minReplicas"] == 4
        assert patched_workers["maxReplicas"] == 4

        # ── Step 4: Get status after scaling ──
        scaled_cr = make_raycluster_cr(
            name=cluster_name, namespace=namespace,
            workers=4, state="ready", head_ready=True,
        )
        mock_custom_objects_api.get_namespaced_custom_object.return_value = scaled_cr

        status = cluster_service.get_status(cluster_name, namespace)

        assert isinstance(status, ClusterStatus)
        assert status.name == cluster_name
        assert status.namespace == namespace
        assert status.state == "RUNNING"
        assert status.head_ready is True
        assert status.workers_desired == 4
        assert status.workers_ready == 4

        # ── Step 5: Delete ──
        # Set up list call for running jobs check (best-effort)
        mock_custom_objects_api.list_namespaced_custom_object.return_value = {"items": []}

        cluster_service.delete(cluster_name, namespace)

        mock_custom_objects_api.delete_namespaced_custom_object.assert_called_once()
        delete_call = mock_custom_objects_api.delete_namespaced_custom_object.call_args
        delete_kwargs = delete_call[1]
        assert delete_kwargs["name"] == cluster_name
        assert delete_kwargs["namespace"] == namespace

    def test_cluster_create_idempotent(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        """Creating the same cluster twice should succeed if the spec is identical.

        Simulates the case where a K8s 409 Conflict is returned on the second
        create call, and the existing CR has an identical spec. The idempotent
        create should return the existing resource without error.
        """
        cluster_name = "idempotent-cluster"
        namespace = "default"

        # ── First create: succeeds normally ──
        first_cr = make_raycluster_cr(
            name=cluster_name, namespace=namespace, workers=2,
        )
        mock_custom_objects_api.create_namespaced_custom_object.return_value = first_cr

        result1 = cluster_service.create(
            name=cluster_name,
            namespace=namespace,
            workers=2,
        )

        assert result1["metadata"]["name"] == cluster_name
        mock_custom_objects_api.create_namespaced_custom_object.assert_called_once()

        # ── Second create: 409 Conflict, but spec matches ──
        api_conflict = type(
            "ApiException", (Exception,), {"status": 409, "reason": "Conflict"},
        )()
        mock_custom_objects_api.create_namespaced_custom_object.reset_mock()
        mock_custom_objects_api.create_namespaced_custom_object.side_effect = api_conflict

        # The get call returns an existing CR whose spec matches
        # what we are trying to create. Build a matching CR from the same params.
        # We need to ensure the spec matches exactly, so we use the body that
        # ClusterService would have generated.
        # The simplest approach: the compare_fn in ClusterService checks
        # existing["spec"] == desired["spec"], so we make get return the same
        # body that create would have sent.
        from kuberay_sdk.models.cluster import ClusterConfig

        desired_config = ClusterConfig(
            name=cluster_name, namespace=namespace, workers=2,
        )
        desired_body = desired_config.to_crd_dict()
        mock_custom_objects_api.get_namespaced_custom_object.return_value = desired_body

        result2 = cluster_service.create(
            name=cluster_name,
            namespace=namespace,
            workers=2,
        )

        # Should succeed (idempotent) -- returns the existing CR
        assert result2["metadata"]["name"] == cluster_name
        assert result2["spec"] == desired_body["spec"]

    def test_cluster_create_idempotent_conflict_on_different_spec(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        """Creating a cluster with different spec than existing should raise ResourceConflictError."""
        cluster_name = "conflict-cluster"
        namespace = "default"

        # Create returns 409 Conflict
        api_conflict = type(
            "ApiException", (Exception,), {"status": 409, "reason": "Conflict"},
        )()
        mock_custom_objects_api.create_namespaced_custom_object.side_effect = api_conflict

        # The existing CR has a different worker count (5 vs requested 2)
        existing_cr = make_raycluster_cr(
            name=cluster_name, namespace=namespace, workers=5,
        )
        mock_custom_objects_api.get_namespaced_custom_object.return_value = existing_cr

        with pytest.raises(ResourceConflictError):
            cluster_service.create(
                name=cluster_name,
                namespace=namespace,
                workers=2,  # Different from existing (5)
            )

    def test_lifecycle_with_heterogeneous_workers(
        self,
        cluster_service: ClusterService,
        mock_custom_objects_api: MagicMock,
    ):
        """Full lifecycle with multiple heterogeneous worker groups (CPU + GPU)."""
        cluster_name = "hetero-lifecycle"
        namespace = "default"

        # ── Create with heterogeneous worker groups ──
        worker_groups = [
            WorkerGroup(name="cpu-pool", replicas=4, cpus=4.0, memory="8Gi"),
            WorkerGroup(name="gpu-pool", replicas=2, cpus=2.0, memory="16Gi", gpus=1),
        ]

        created_cr = make_raycluster_cr(
            name=cluster_name, namespace=namespace, workers=4,
        )
        mock_custom_objects_api.create_namespaced_custom_object.return_value = created_cr

        result = cluster_service.create(
            name=cluster_name,
            namespace=namespace,
            worker_groups=worker_groups,
        )

        assert result["metadata"]["name"] == cluster_name

        # Verify the body sent to K8s has 2 worker group specs
        create_call = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = create_call[1].get("body") or create_call[0][-1]
        assert len(body["spec"]["workerGroupSpecs"]) == 2
        assert body["spec"]["workerGroupSpecs"][0]["groupName"] == "cpu-pool"
        assert body["spec"]["workerGroupSpecs"][1]["groupName"] == "gpu-pool"
        assert body["spec"]["workerGroupSpecs"][0]["replicas"] == 4
        assert body["spec"]["workerGroupSpecs"][1]["replicas"] == 2

        # Verify GPU resources on gpu-pool
        gpu_container = body["spec"]["workerGroupSpecs"][1]["template"]["spec"]["containers"][0]
        assert gpu_container["resources"]["requests"]["nvidia.com/gpu"] == "1"

        # ── Wait until ready ──
        ready_cr = make_raycluster_cr(
            name=cluster_name, namespace=namespace,
            workers=4, state="ready", head_ready=True,
        )
        mock_custom_objects_api.get_namespaced_custom_object.return_value = ready_cr

        with patch("time.sleep"):
            cluster_service.wait_until_ready(cluster_name, namespace, timeout=60)

        # ── Delete ──
        mock_custom_objects_api.list_namespaced_custom_object.return_value = {"items": []}
        cluster_service.delete(cluster_name, namespace)
        mock_custom_objects_api.delete_namespaced_custom_object.assert_called_once()
