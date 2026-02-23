"""Integration tests for full RayService lifecycle (T081).

Tests the complete service lifecycle: create -> status -> update -> delete
using mocked K8s API. Includes tests for heterogeneous worker groups
(GPU + CPU) in a service context.

All Kubernetes API calls are mocked via ``mock_custom_objects_api`` from
conftest.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import yaml

from kuberay_sdk.config import SDKConfig
from kuberay_sdk.models.cluster import WorkerGroup
from kuberay_sdk.models.service import ServiceStatus
from kuberay_sdk.services.service_service import ServiceService
from tests.conftest import make_rayservice_cr

# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture()
def sdk_config() -> SDKConfig:
    """Default SDK config for integration tests."""
    return SDKConfig(namespace="default")


@pytest.fixture()
def service_service(
    mock_custom_objects_api: MagicMock,
    sdk_config: SDKConfig,
) -> ServiceService:
    """ServiceService with mocked CustomObjectsApi."""
    return ServiceService(mock_custom_objects_api, sdk_config)


# ──────────────────────────────────────────────
# T081: Full service lifecycle
# ──────────────────────────────────────────────


@pytest.mark.integration
class TestServiceLifecycle:
    """Full service lifecycle: create -> status -> update -> delete."""

    def test_service_lifecycle(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        """End-to-end service lifecycle through all CRUD operations.

        Steps:
            1. Create a RayService with import_path
            2. Get status and verify it reports RUNNING
            3. Update the number of serve replicas
            4. Delete the service
        """
        service_name = "llm-service"
        namespace = "ml-serving"

        # ── Step 1: Create ──
        created_cr = make_rayservice_cr(
            name=service_name, namespace=namespace, state="Running",
        )
        mock_custom_objects_api.create_namespaced_custom_object.return_value = created_cr

        result = service_service.create(
            name=service_name,
            namespace=namespace,
            import_path="serve_app:deployment",
            num_replicas=2,
            workers=3,
            cpus_per_worker=2.0,
            memory_per_worker="4Gi",
        )

        mock_custom_objects_api.create_namespaced_custom_object.assert_called_once()
        assert result["metadata"]["name"] == service_name
        assert result["metadata"]["namespace"] == namespace

        # Verify the CRD body
        create_call = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = create_call[1].get("body") or create_call[0][-1]
        assert body["apiVersion"] == "ray.io/v1"
        assert body["kind"] == "RayService"
        assert "serveConfigV2" in body["spec"]
        assert "rayClusterConfig" in body["spec"]

        # Verify serveConfigV2 content
        serve_config = yaml.safe_load(body["spec"]["serveConfigV2"])
        assert serve_config["applications"][0]["import_path"] == "serve_app:deployment"
        assert serve_config["applications"][0]["deployments"][0]["num_replicas"] == 2

        # Verify cluster config has 3 workers
        cluster_config = body["spec"]["rayClusterConfig"]
        assert cluster_config["workerGroupSpecs"][0]["replicas"] == 3

        # ── Step 2: Get status ──
        running_cr = make_rayservice_cr(
            name=service_name, namespace=namespace, state="Running",
        )
        mock_custom_objects_api.get_namespaced_custom_object.return_value = running_cr

        status = service_service.get_status(service_name, namespace)

        assert isinstance(status, ServiceStatus)
        assert status.name == service_name
        assert status.namespace == namespace
        assert status.state == "RUNNING"

        # ── Step 3: Update replicas ──
        # The update method fetches the current CR, parses serveConfigV2,
        # modifies the deployment config, and patches.
        current_cr = make_rayservice_cr(
            name=service_name, namespace=namespace, state="Running",
        )
        mock_custom_objects_api.get_namespaced_custom_object.return_value = current_cr

        service_service.update(
            name=service_name,
            namespace=namespace,
            num_replicas=4,
        )

        mock_custom_objects_api.patch_namespaced_custom_object.assert_called_once()
        patch_call = mock_custom_objects_api.patch_namespaced_custom_object.call_args
        patch_body = patch_call[1].get("body") or patch_call[0][-1]

        # The patched serveConfigV2 should contain num_replicas=4
        patched_serve_config = yaml.safe_load(patch_body["spec"]["serveConfigV2"])
        apps = patched_serve_config.get("applications", [])
        assert len(apps) >= 1
        deployments = apps[0].get("deployments", [])
        assert len(deployments) >= 1
        assert deployments[0]["num_replicas"] == 4

        # ── Step 4: Delete ──
        service_service.delete(service_name, namespace)

        mock_custom_objects_api.delete_namespaced_custom_object.assert_called_once()
        delete_call = mock_custom_objects_api.delete_namespaced_custom_object.call_args
        delete_kwargs = delete_call[1]
        assert delete_kwargs["name"] == service_name
        assert delete_kwargs["namespace"] == namespace
        assert delete_kwargs["group"] == "ray.io"
        assert delete_kwargs["plural"] == "rayservices"

    def test_service_with_heterogeneous_workers(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        """Create a service with GPU and CPU worker groups.

        Verifies that heterogeneous worker groups are correctly embedded
        in the rayClusterConfig of the RayService CRD.
        """
        service_name = "hetero-service"
        namespace = "default"

        worker_groups = [
            WorkerGroup(name="cpu-inference", replicas=4, cpus=2.0, memory="4Gi"),
            WorkerGroup(name="gpu-inference", replicas=2, cpus=2.0, memory="16Gi", gpus=1),
        ]

        created_cr = make_rayservice_cr(
            name=service_name, namespace=namespace, state="Running",
        )
        mock_custom_objects_api.create_namespaced_custom_object.return_value = created_cr

        result = service_service.create(
            name=service_name,
            namespace=namespace,
            import_path="model_server:app",
            num_replicas=1,
            worker_groups=worker_groups,
        )

        assert result["metadata"]["name"] == service_name

        # Verify the CRD body has heterogeneous worker groups
        create_call = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = create_call[1].get("body") or create_call[0][-1]
        cluster_config = body["spec"]["rayClusterConfig"]
        worker_specs = cluster_config["workerGroupSpecs"]

        assert len(worker_specs) == 2

        # CPU pool
        cpu_group = worker_specs[0]
        assert cpu_group["groupName"] == "cpu-inference"
        assert cpu_group["replicas"] == 4
        cpu_container = cpu_group["template"]["spec"]["containers"][0]
        assert cpu_container["resources"]["requests"]["cpu"] == "2"
        assert cpu_container["resources"]["requests"]["memory"] == "4Gi"
        assert "nvidia.com/gpu" not in cpu_container["resources"]["requests"]

        # GPU pool
        gpu_group = worker_specs[1]
        assert gpu_group["groupName"] == "gpu-inference"
        assert gpu_group["replicas"] == 2
        gpu_container = gpu_group["template"]["spec"]["containers"][0]
        assert gpu_container["resources"]["requests"]["cpu"] == "2"
        assert gpu_container["resources"]["requests"]["memory"] == "16Gi"
        assert gpu_container["resources"]["requests"]["nvidia.com/gpu"] == "1"

    def test_service_list_after_create(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        """List services after creating one, verifying list returns ServiceStatus objects."""
        service_name = "listed-service"
        namespace = "default"

        # Create
        created_cr = make_rayservice_cr(
            name=service_name, namespace=namespace, state="Running",
        )
        mock_custom_objects_api.create_namespaced_custom_object.return_value = created_cr
        service_service.create(
            name=service_name,
            namespace=namespace,
            import_path="app:deployment",
        )

        # List
        mock_custom_objects_api.list_namespaced_custom_object.return_value = {
            "items": [
                make_rayservice_cr(name="listed-service", namespace=namespace, state="Running"),
                make_rayservice_cr(name="other-service", namespace=namespace, state="Deploying"),
            ]
        }

        services = service_service.list(namespace)

        assert len(services) == 2
        assert all(isinstance(s, ServiceStatus) for s in services)
        names = [s.name for s in services]
        assert "listed-service" in names
        assert "other-service" in names

    def test_service_update_import_path(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        """Update a service's import_path and verify the patch body."""
        service_name = "update-path-service"
        namespace = "default"

        current_cr = make_rayservice_cr(
            name=service_name, namespace=namespace, state="Running",
        )
        mock_custom_objects_api.get_namespaced_custom_object.return_value = current_cr

        service_service.update(
            name=service_name,
            namespace=namespace,
            import_path="new_app:v2_deployment",
        )

        patch_call = mock_custom_objects_api.patch_namespaced_custom_object.call_args
        patch_body = patch_call[1].get("body") or patch_call[0][-1]

        patched_serve_config = yaml.safe_load(patch_body["spec"]["serveConfigV2"])
        assert patched_serve_config["applications"][0]["import_path"] == "new_app:v2_deployment"
