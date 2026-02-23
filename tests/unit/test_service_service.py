"""Unit tests for ServiceService (T042).

Tests verify that ServiceService correctly:
- Generates CRD dicts and calls CustomObjectsApi for CRUD operations
- Handles create with import_path and serve_config_v2
- Gets service status
- Lists services
- Updates service configuration (num_replicas, import_path)
- Deletes services

All Kubernetes API calls are mocked via ``mock_custom_objects_api`` from
conftest.py.

TDD: these tests are written BEFORE ``kuberay_sdk.services.service_service``
and ``kuberay_sdk.models.service`` are implemented.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import yaml

from kuberay_sdk.config import SDKConfig
from kuberay_sdk.errors import (
    ResourceConflictError,
    ServiceNotFoundError,
)

# ── Imports that will fail until implementation exists ──
from kuberay_sdk.models.service import ServiceConfig, ServiceStatus
from kuberay_sdk.services.service_service import ServiceService

# conftest helpers
from tests.conftest import make_rayservice_cr

# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture()
def sdk_config() -> SDKConfig:
    """Default SDK config for tests."""
    return SDKConfig(namespace="default")


@pytest.fixture()
def service_service(
    mock_custom_objects_api: MagicMock,
    sdk_config: SDKConfig,
) -> ServiceService:
    """ServiceService with mocked CustomObjectsApi."""
    return ServiceService(mock_custom_objects_api, sdk_config)


# ──────────────────────────────────────────────
# create — with import_path
# ──────────────────────────────────────────────


class TestCreateService:
    """Test create_service with import_path."""

    def test_create_calls_k8s_api(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        service_service.create(
            name="test-service",
            namespace="default",
            import_path="serve_app:deployment",
        )
        mock_custom_objects_api.create_namespaced_custom_object.assert_called_once()

    def test_create_passes_correct_group_version(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        service_service.create(
            name="test-service",
            namespace="default",
            import_path="serve_app:deployment",
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        # Check group, version, and plural are correct
        args = call_kwargs[1] if call_kwargs[1] else {}
        positional = call_kwargs[0] if call_kwargs[0] else ()
        all_args = list(positional) + list(args.values())
        assert "ray.io" in all_args or args.get("group") == "ray.io"
        assert "v1" in all_args or args.get("version") == "v1"

    def test_create_generates_correct_crd_kind(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        service_service.create(
            name="my-llm",
            namespace="ml-namespace",
            import_path="serve_app:deployment",
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        assert body["kind"] == "RayService"
        assert body["apiVersion"] == "ray.io/v1"

    def test_create_generates_correct_metadata(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        service_service.create(
            name="my-llm",
            namespace="ml-namespace",
            import_path="serve_app:deployment",
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        assert body["metadata"]["name"] == "my-llm"
        assert body["metadata"]["namespace"] == "ml-namespace"

    def test_create_has_serve_config_v2(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        service_service.create(
            name="test-service",
            namespace="default",
            import_path="serve_app:deployment",
            num_replicas=2,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        assert "serveConfigV2" in body["spec"]
        serve_config = yaml.safe_load(body["spec"]["serveConfigV2"])
        assert serve_config["applications"][0]["import_path"] == "serve_app:deployment"

    def test_create_has_ray_cluster_config(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        service_service.create(
            name="test-service",
            namespace="default",
            import_path="serve_app:deployment",
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        assert "rayClusterConfig" in body["spec"]
        rcc = body["spec"]["rayClusterConfig"]
        assert "headGroupSpec" in rcc
        assert "workerGroupSpecs" in rcc

    def test_create_with_num_replicas(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        service_service.create(
            name="test-service",
            namespace="default",
            import_path="serve_app:deployment",
            num_replicas=4,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        serve_config = yaml.safe_load(body["spec"]["serveConfigV2"])
        deployments = serve_config["applications"][0]["deployments"]
        assert deployments[0]["num_replicas"] == 4

    def test_create_with_raw_serve_config_v2(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        raw_yaml = "applications:\n  - name: custom\n    import_path: custom:app\n"
        service_service.create(
            name="test-service",
            namespace="default",
            serve_config_v2=raw_yaml,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        assert body["spec"]["serveConfigV2"] == raw_yaml

    def test_create_with_gpu_workers(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        service_service.create(
            name="gpu-service",
            namespace="default",
            import_path="serve_app:deployment",
            gpus_per_worker=1,
            workers=2,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        rcc = body["spec"]["rayClusterConfig"]
        worker_container = rcc["workerGroupSpecs"][0]["template"]["spec"]["containers"][0]
        assert worker_container["resources"]["requests"]["nvidia.com/gpu"] == "1"


# ──────────────────────────────────────────────
# get_status
# ──────────────────────────────────────────────


class TestGetServiceStatus:
    """Test get_status returns a ServiceStatus object."""

    def test_get_returns_service_status(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = (
            make_rayservice_cr(name="my-llm", namespace="default", state="Running")
        )
        status = service_service.get_status("my-llm", "default")
        assert isinstance(status, ServiceStatus)
        assert status.name == "my-llm"
        assert status.namespace == "default"

    def test_get_status_state(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = (
            make_rayservice_cr(state="Running")
        )
        status = service_service.get_status("test-service", "default")
        assert status.state == "RUNNING"

    def test_get_status_deploying(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = (
            make_rayservice_cr(state="Deploying")
        )
        status = service_service.get_status("test-service", "default")
        assert status.state == "DEPLOYING"

    def test_get_nonexistent_service_raises(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        api_exception = type("ApiException", (Exception,), {"status": 404, "reason": "Not Found"})()
        mock_custom_objects_api.get_namespaced_custom_object.side_effect = api_exception
        with pytest.raises(ServiceNotFoundError):
            service_service.get_status("nonexistent", "default")

    def test_get_status_calls_correct_api(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = (
            make_rayservice_cr()
        )
        service_service.get_status("test-service", "default")
        call_kwargs = mock_custom_objects_api.get_namespaced_custom_object.call_args
        assert call_kwargs[1].get("plural") == "rayservices"
        assert call_kwargs[1].get("group") == "ray.io"
        assert call_kwargs[1].get("version") == "v1"


# ──────────────────────────────────────────────
# list
# ──────────────────────────────────────────────


class TestListServices:
    """Test list returns a list of ServiceStatus objects."""

    def test_list_empty(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.list_namespaced_custom_object.return_value = {"items": []}
        result = service_service.list("default")
        assert result == []

    def test_list_returns_service_statuses(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.list_namespaced_custom_object.return_value = {
            "items": [
                make_rayservice_cr(name="svc-1"),
                make_rayservice_cr(name="svc-2"),
            ]
        }
        result = service_service.list("default")
        assert len(result) == 2
        assert all(isinstance(s, ServiceStatus) for s in result)

    def test_list_status_names(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.list_namespaced_custom_object.return_value = {
            "items": [
                make_rayservice_cr(name="alpha"),
                make_rayservice_cr(name="bravo"),
                make_rayservice_cr(name="charlie"),
            ]
        }
        result = service_service.list("default")
        names = [s.name for s in result]
        assert names == ["alpha", "bravo", "charlie"]

    def test_list_calls_correct_api(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        service_service.list("my-namespace")
        mock_custom_objects_api.list_namespaced_custom_object.assert_called_once()
        call_kwargs = mock_custom_objects_api.list_namespaced_custom_object.call_args
        assert call_kwargs[1].get("plural") == "rayservices"
        assert call_kwargs[1].get("namespace") == "my-namespace"


# ──────────────────────────────────────────────
# update
# ──────────────────────────────────────────────


class TestUpdateService:
    """Test update patches serveConfigV2."""

    def test_update_num_replicas_calls_patch(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = (
            make_rayservice_cr(name="test-service")
        )
        service_service.update("test-service", "default", num_replicas=4)
        mock_custom_objects_api.patch_namespaced_custom_object.assert_called_once()

    def test_update_num_replicas_in_patch(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = (
            make_rayservice_cr(name="test-service")
        )
        service_service.update("test-service", "default", num_replicas=5)
        call_kwargs = mock_custom_objects_api.patch_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        serve_config = yaml.safe_load(body["spec"]["serveConfigV2"])
        app = serve_config["applications"][0]
        deployments = app.get("deployments", [])
        assert len(deployments) >= 1
        assert deployments[0]["num_replicas"] == 5

    def test_update_import_path(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = (
            make_rayservice_cr(name="test-service")
        )
        service_service.update("test-service", "default", import_path="new_module:app")
        call_kwargs = mock_custom_objects_api.patch_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        serve_config = yaml.safe_load(body["spec"]["serveConfigV2"])
        app = serve_config["applications"][0]
        assert app["import_path"] == "new_module:app"

    def test_update_both_replicas_and_import_path(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = (
            make_rayservice_cr(name="test-service")
        )
        service_service.update(
            "test-service", "default",
            num_replicas=3,
            import_path="updated:app",
        )
        call_kwargs = mock_custom_objects_api.patch_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        serve_config = yaml.safe_load(body["spec"]["serveConfigV2"])
        app = serve_config["applications"][0]
        assert app["import_path"] == "updated:app"
        assert app["deployments"][0]["num_replicas"] == 3

    def test_update_nonexistent_service_raises(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        api_exception = type("ApiException", (Exception,), {"status": 404, "reason": "Not Found"})()
        mock_custom_objects_api.get_namespaced_custom_object.side_effect = api_exception
        with pytest.raises(ServiceNotFoundError):
            service_service.update("nonexistent", "default", num_replicas=3)

    def test_update_passes_correct_api_params(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = (
            make_rayservice_cr(name="test-service")
        )
        service_service.update("test-service", "ml-team", num_replicas=2)
        call_kwargs = mock_custom_objects_api.patch_namespaced_custom_object.call_args
        assert call_kwargs[1].get("plural") == "rayservices"
        assert call_kwargs[1].get("name") == "test-service"
        assert call_kwargs[1].get("namespace") == "ml-team"


# ──────────────────────────────────────────────
# delete
# ──────────────────────────────────────────────


class TestDeleteService:
    """Test delete calls the correct K8s API."""

    def test_delete_calls_api(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        service_service.delete("test-service", "default")
        mock_custom_objects_api.delete_namespaced_custom_object.assert_called_once()

    def test_delete_passes_correct_params(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        service_service.delete("my-llm", "ml-team")
        call_kwargs = mock_custom_objects_api.delete_namespaced_custom_object.call_args
        assert call_kwargs[1].get("group") == "ray.io"
        assert call_kwargs[1].get("version") == "v1"
        assert call_kwargs[1].get("plural") == "rayservices"
        assert call_kwargs[1].get("name") == "my-llm"
        assert call_kwargs[1].get("namespace") == "ml-team"

    def test_delete_nonexistent_service_raises(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        api_exception = type("ApiException", (Exception,), {"status": 404, "reason": "Not Found"})()
        mock_custom_objects_api.delete_namespaced_custom_object.side_effect = api_exception
        with pytest.raises(ServiceNotFoundError):
            service_service.delete("nonexistent", "default")


# ──────────────────────────────────────────────
# Idempotent create
# ──────────────────────────────────────────────


class TestIdempotentCreateService:
    """Test idempotent create semantics for services."""

    def test_identical_spec_returns_without_error(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        """Creating a service that already exists with the same spec should succeed."""
        api_exception = type(
            "ApiException", (Exception,), {"status": 409, "reason": "Conflict"},
        )()
        mock_custom_objects_api.create_namespaced_custom_object.side_effect = api_exception

        # Build the expected CRD to match what idempotent_create will compare
        svc_config = ServiceConfig(
            name="test-service",
            namespace="default",
            import_path="serve_app:deployment",
            num_replicas=1,
        )
        expected_crd = svc_config.to_crd_dict()
        mock_custom_objects_api.get_namespaced_custom_object.return_value = expected_crd

        # Should NOT raise -- idempotent create succeeds
        service_service.create(
            name="test-service",
            namespace="default",
            import_path="serve_app:deployment",
            num_replicas=1,
        )

    def test_different_spec_raises_resource_conflict(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        """Creating a service that already exists with a different spec should fail."""
        api_exception = type(
            "ApiException", (Exception,), {"status": 409, "reason": "Conflict"},
        )()
        mock_custom_objects_api.create_namespaced_custom_object.side_effect = api_exception

        # Existing service has a different serveConfigV2
        existing_cr = make_rayservice_cr(
            name="test-service",
            namespace="default",
        )
        mock_custom_objects_api.get_namespaced_custom_object.return_value = existing_cr

        with pytest.raises(ResourceConflictError):
            service_service.create(
                name="test-service",
                namespace="default",
                import_path="completely_different:app",
                num_replicas=10,
            )


# ──────────────────────────────────────────────
# US9: Heterogeneous worker groups (T070)
# ──────────────────────────────────────────────


class TestHeterogeneousWorkerGroups:
    """Test RayService with heterogeneous worker groups (GPU + CPU) for agentic workloads (T070/US9)."""

    def test_create_with_gpu_and_cpu_worker_groups(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        """Verify RayService CRD has multiple workerGroupSpecs with correct resources."""
        from kuberay_sdk.models.cluster import WorkerGroup

        mock_custom_objects_api.create_namespaced_custom_object.return_value = {}

        service_service.create(
            name="agent-app",
            namespace="default",
            import_path="agent_app:app",
            worker_groups=[
                WorkerGroup(name="llm", replicas=1, gpus=1, memory="16Gi"),
                WorkerGroup(name="tools", replicas=4, cpus=4.0, memory="4Gi"),
            ],
        )

        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        ray_cluster_config = body["spec"]["rayClusterConfig"]
        worker_specs = ray_cluster_config["workerGroupSpecs"]

        assert len(worker_specs) == 2

    def test_heterogeneous_group_names_preserved(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        """Verify worker group names are preserved in the CRD."""
        from kuberay_sdk.models.cluster import WorkerGroup

        mock_custom_objects_api.create_namespaced_custom_object.return_value = {}

        service_service.create(
            name="agent-app",
            namespace="default",
            import_path="agent_app:app",
            worker_groups=[
                WorkerGroup(name="llm", replicas=1, gpus=1, memory="16Gi"),
                WorkerGroup(name="tools", replicas=4, cpus=4.0, memory="4Gi"),
            ],
        )

        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        worker_specs = body["spec"]["rayClusterConfig"]["workerGroupSpecs"]
        names = [g["groupName"] for g in worker_specs]
        assert "llm" in names
        assert "tools" in names

    def test_gpu_group_has_gpu_resources(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        """Verify GPU worker group has nvidia.com/gpu in resource requests."""
        from kuberay_sdk.models.cluster import WorkerGroup

        mock_custom_objects_api.create_namespaced_custom_object.return_value = {}

        service_service.create(
            name="agent-app",
            namespace="default",
            import_path="agent_app:app",
            worker_groups=[
                WorkerGroup(name="llm", replicas=1, gpus=1, memory="16Gi"),
                WorkerGroup(name="tools", replicas=4, cpus=4.0, memory="4Gi"),
            ],
        )

        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        worker_specs = body["spec"]["rayClusterConfig"]["workerGroupSpecs"]

        # Find the GPU group
        llm_group = next(g for g in worker_specs if g["groupName"] == "llm")
        llm_container = llm_group["template"]["spec"]["containers"][0]
        assert "nvidia.com/gpu" in llm_container["resources"]["requests"]
        assert llm_container["resources"]["requests"]["nvidia.com/gpu"] == "1"

    def test_cpu_group_has_no_gpu_resources(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        """Verify CPU-only worker group does NOT have GPU resources."""
        from kuberay_sdk.models.cluster import WorkerGroup

        mock_custom_objects_api.create_namespaced_custom_object.return_value = {}

        service_service.create(
            name="agent-app",
            namespace="default",
            import_path="agent_app:app",
            worker_groups=[
                WorkerGroup(name="llm", replicas=1, gpus=1, memory="16Gi"),
                WorkerGroup(name="tools", replicas=4, cpus=4.0, memory="4Gi"),
            ],
        )

        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        worker_specs = body["spec"]["rayClusterConfig"]["workerGroupSpecs"]

        # Find the CPU group
        tools_group = next(g for g in worker_specs if g["groupName"] == "tools")
        tools_container = tools_group["template"]["spec"]["containers"][0]
        assert "nvidia.com/gpu" not in tools_container["resources"]["requests"]

    def test_heterogeneous_replicas_correct(
        self,
        service_service: ServiceService,
        mock_custom_objects_api: MagicMock,
    ):
        """Verify each worker group has the correct replica count."""
        from kuberay_sdk.models.cluster import WorkerGroup

        mock_custom_objects_api.create_namespaced_custom_object.return_value = {}

        service_service.create(
            name="agent-app",
            namespace="default",
            import_path="agent_app:app",
            worker_groups=[
                WorkerGroup(name="llm", replicas=1, gpus=1, memory="16Gi"),
                WorkerGroup(name="tools", replicas=4, cpus=4.0, memory="4Gi"),
            ],
        )

        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body") or call_kwargs[0][-1]
        worker_specs = body["spec"]["rayClusterConfig"]["workerGroupSpecs"]

        llm_group = next(g for g in worker_specs if g["groupName"] == "llm")
        tools_group = next(g for g in worker_specs if g["groupName"] == "tools")
        assert llm_group["replicas"] == 1
        assert tools_group["replicas"] == 4
