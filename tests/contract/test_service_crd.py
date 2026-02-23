"""Contract tests: SDK-generated RayService CRD matches RAYSERVICE_SCHEMA (T040).

These tests verify that the service model's ``to_crd()`` output conforms to
the RayService CRD contract defined in ``specs/.../contracts/crd_schemas.py``.

TDD: these tests are written BEFORE the ``kuberay_sdk.models.service`` module
exists.  They will fail on import until the implementation is created.
"""

from __future__ import annotations

import pytest
import yaml

from kuberay_sdk.models.cluster import HeadNodeConfig, WorkerGroup
from kuberay_sdk.models.runtime_env import RuntimeEnv

# ── Imports that will fail until implementation exists ──
from kuberay_sdk.models.service import ServiceConfig

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _build_default_service(**overrides) -> ServiceConfig:
    """Build a ServiceConfig with sensible defaults, merging *overrides*."""
    defaults = {
        "name": "test-service",
        "namespace": "default",
        "import_path": "serve_app:deployment",
        "num_replicas": 1,
        "ray_version": "2.41.0",
    }
    defaults.update(overrides)
    return ServiceConfig(**defaults)


def _head_container(crd: dict) -> dict:
    """Extract the first container from rayClusterConfig headGroupSpec."""
    return crd["spec"]["rayClusterConfig"]["headGroupSpec"]["template"]["spec"]["containers"][0]


def _worker_container(crd: dict, group_idx: int = 0) -> dict:
    """Extract the first container from a rayClusterConfig workerGroupSpec."""
    return crd["spec"]["rayClusterConfig"]["workerGroupSpecs"][group_idx]["template"]["spec"]["containers"][0]


# ──────────────────────────────────────────────
# apiVersion and kind
# ──────────────────────────────────────────────


class TestServiceCRDTopLevel:
    """Verify top-level CRD fields: apiVersion, kind."""

    def test_api_version(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        assert crd["apiVersion"] == "ray.io/v1"

    def test_kind(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        assert crd["kind"] == "RayService"


# ──────────────────────────────────────────────
# metadata
# ──────────────────────────────────────────────


class TestServiceCRDMetadata:
    """Verify metadata structure: name, namespace, labels, annotations."""

    def test_metadata_name(self):
        svc = _build_default_service(name="my-llm")
        crd = svc.to_crd()
        assert crd["metadata"]["name"] == "my-llm"

    def test_metadata_namespace(self):
        svc = _build_default_service(namespace="ml-team")
        crd = svc.to_crd()
        assert crd["metadata"]["namespace"] == "ml-team"

    def test_metadata_has_labels_dict(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        assert isinstance(crd["metadata"]["labels"], dict)

    def test_metadata_has_annotations_dict(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        assert isinstance(crd["metadata"]["annotations"], dict)

    def test_custom_labels_propagated(self):
        svc = _build_default_service(labels={"team": "ml", "env": "prod"})
        crd = svc.to_crd()
        assert crd["metadata"]["labels"]["team"] == "ml"
        assert crd["metadata"]["labels"]["env"] == "prod"

    def test_custom_annotations_propagated(self):
        svc = _build_default_service(annotations={"note": "test-service"})
        crd = svc.to_crd()
        assert crd["metadata"]["annotations"]["note"] == "test-service"


# ──────────────────────────────────────────────
# spec.serveConfigV2
# ──────────────────────────────────────────────


class TestServiceCRDServeConfigV2:
    """Verify spec.serveConfigV2 is a YAML string with correct structure."""

    def test_serve_config_v2_is_string(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        assert isinstance(crd["spec"]["serveConfigV2"], str)

    def test_serve_config_v2_is_valid_yaml(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        parsed = yaml.safe_load(crd["spec"]["serveConfigV2"])
        assert isinstance(parsed, dict)

    def test_serve_config_v2_has_applications(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        parsed = yaml.safe_load(crd["spec"]["serveConfigV2"])
        assert "applications" in parsed
        assert isinstance(parsed["applications"], list)
        assert len(parsed["applications"]) >= 1

    def test_serve_config_v2_import_path(self):
        svc = _build_default_service(import_path="my_module:app")
        crd = svc.to_crd()
        parsed = yaml.safe_load(crd["spec"]["serveConfigV2"])
        app = parsed["applications"][0]
        assert app["import_path"] == "my_module:app"

    def test_serve_config_v2_num_replicas(self):
        svc = _build_default_service(num_replicas=3)
        crd = svc.to_crd()
        parsed = yaml.safe_load(crd["spec"]["serveConfigV2"])
        app = parsed["applications"][0]
        deployments = app.get("deployments", [])
        assert len(deployments) >= 1
        assert deployments[0]["num_replicas"] == 3

    def test_serve_config_v2_default_replicas(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        parsed = yaml.safe_load(crd["spec"]["serveConfigV2"])
        app = parsed["applications"][0]
        deployments = app.get("deployments", [])
        assert len(deployments) >= 1
        assert deployments[0]["num_replicas"] == 1

    def test_serve_config_v2_with_runtime_env(self):
        env = RuntimeEnv(pip=["torch", "transformers"], env_vars={"KEY": "val"})
        svc = _build_default_service(runtime_env=env)
        crd = svc.to_crd()
        parsed = yaml.safe_load(crd["spec"]["serveConfigV2"])
        app = parsed["applications"][0]
        assert "runtime_env" in app
        assert "pip" in app["runtime_env"]
        assert "torch" in app["runtime_env"]["pip"]

    def test_raw_serve_config_v2_passthrough(self):
        """When serve_config_v2 is provided directly, it should pass through unchanged."""
        raw_yaml = "applications:\n  - name: custom\n    import_path: custom:app\n"
        svc = ServiceConfig(
            name="test-service",
            namespace="default",
            serve_config_v2=raw_yaml,
        )
        crd = svc.to_crd()
        assert crd["spec"]["serveConfigV2"] == raw_yaml


# ──────────────────────────────────────────────
# spec.rayClusterConfig
# ──────────────────────────────────────────────


class TestServiceCRDRayClusterConfig:
    """Verify spec.rayClusterConfig contains embedded cluster spec."""

    def test_ray_cluster_config_is_dict(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        assert isinstance(crd["spec"]["rayClusterConfig"], dict)

    def test_ray_cluster_config_has_head_group(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        rcc = crd["spec"]["rayClusterConfig"]
        assert "headGroupSpec" in rcc

    def test_ray_cluster_config_has_worker_groups(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        rcc = crd["spec"]["rayClusterConfig"]
        assert "workerGroupSpecs" in rcc
        assert isinstance(rcc["workerGroupSpecs"], list)

    def test_ray_cluster_config_has_ray_version(self):
        svc = _build_default_service(ray_version="2.41.0")
        crd = svc.to_crd()
        rcc = crd["spec"]["rayClusterConfig"]
        assert rcc["rayVersion"] == "2.41.0"

    def test_head_container_image(self):
        svc = _build_default_service(ray_version="2.41.0")
        crd = svc.to_crd()
        container = _head_container(crd)
        assert container["image"] == "rayproject/ray:2.41.0"

    def test_head_container_name(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        container = _head_container(crd)
        assert container["name"] == "ray-head"

    def test_worker_container_name(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        container = _worker_container(crd)
        assert container["name"] == "ray-worker"

    def test_worker_container_image(self):
        svc = _build_default_service(ray_version="2.41.0")
        crd = svc.to_crd()
        container = _worker_container(crd)
        assert container["image"] == "rayproject/ray:2.41.0"

    def test_custom_image_propagated(self):
        svc = _build_default_service(image="custom-registry/ray:latest")
        crd = svc.to_crd()
        container = _head_container(crd)
        assert container["image"] == "custom-registry/ray:latest"
        worker = _worker_container(crd)
        assert worker["image"] == "custom-registry/ray:latest"

    def test_worker_resources(self):
        svc = _build_default_service(
            cpus_per_worker=2.0, memory_per_worker="4Gi", gpus_per_worker=1,
        )
        crd = svc.to_crd()
        container = _worker_container(crd)
        assert container["resources"]["requests"]["cpu"] == "2"
        assert container["resources"]["requests"]["memory"] == "4Gi"
        assert container["resources"]["requests"]["nvidia.com/gpu"] == "1"

    def test_head_custom_resources(self):
        head = HeadNodeConfig(cpus=4.0, memory="8Gi")
        svc = _build_default_service(head=head)
        crd = svc.to_crd()
        container = _head_container(crd)
        assert container["resources"]["requests"]["cpu"] == "4"
        assert container["resources"]["requests"]["memory"] == "8Gi"


# ──────────────────────────────────────────────
# Multiple worker groups
# ──────────────────────────────────────────────


class TestServiceCRDMultipleWorkerGroups:
    """Verify multi-group worker spec in rayClusterConfig."""

    def test_multiple_groups_count(self):
        groups = [
            WorkerGroup(name="cpu-pool", replicas=4, cpus=4.0, memory="8Gi"),
            WorkerGroup(name="gpu-pool", replicas=2, gpus=1, memory="16Gi"),
        ]
        svc = _build_default_service(worker_groups=groups)
        crd = svc.to_crd()
        rcc = crd["spec"]["rayClusterConfig"]
        assert len(rcc["workerGroupSpecs"]) == 2

    def test_group_names_preserved(self):
        groups = [
            WorkerGroup(name="cpu-pool", replicas=4),
            WorkerGroup(name="gpu-pool", replicas=2, gpus=1),
        ]
        svc = _build_default_service(worker_groups=groups)
        crd = svc.to_crd()
        rcc = crd["spec"]["rayClusterConfig"]
        names = [g["groupName"] for g in rcc["workerGroupSpecs"]]
        assert names == ["cpu-pool", "gpu-pool"]


# ──────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────


class TestServiceConfigValidation:
    """Verify ServiceConfig validation rules."""

    def test_import_path_and_serve_config_v2_mutually_exclusive(self):
        with pytest.raises(Exception):
            ServiceConfig(
                name="test-service",
                import_path="serve_app:deployment",
                serve_config_v2="applications:\n  - name: custom\n",
            )

    def test_import_path_required_without_serve_config_v2(self):
        with pytest.raises(Exception):
            ServiceConfig(
                name="test-service",
                namespace="default",
            )

    def test_invalid_name_raises(self):
        with pytest.raises(Exception):
            ServiceConfig(
                name="INVALID_NAME",
                import_path="serve_app:deployment",
            )

    def test_num_replicas_must_be_positive(self):
        with pytest.raises(Exception):
            ServiceConfig(
                name="test-service",
                import_path="serve_app:deployment",
                num_replicas=0,
            )

    def test_serve_config_v2_without_import_path_is_valid(self):
        """Using serve_config_v2 alone should be valid."""
        svc = ServiceConfig(
            name="test-service",
            namespace="default",
            serve_config_v2="applications:\n  - name: custom\n    import_path: custom:app\n",
        )
        assert svc.serve_config_v2 is not None
        assert svc.import_path is None


# ──────────────────────────────────────────────
# Overall schema shape
# ──────────────────────────────────────────────


class TestServiceCRDSchemaShape:
    """Verify the overall CRD dict has the expected top-level keys."""

    def test_top_level_keys(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        assert set(crd.keys()) >= {"apiVersion", "kind", "metadata", "spec"}

    def test_spec_contains_serve_config_and_cluster_config(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        spec = crd["spec"]
        assert "serveConfigV2" in spec
        assert "rayClusterConfig" in spec

    def test_ray_cluster_config_structure(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        rcc = crd["spec"]["rayClusterConfig"]
        required_keys = {"rayVersion", "headGroupSpec", "workerGroupSpecs"}
        assert required_keys.issubset(set(rcc.keys()))

    def test_head_dashboard_host_param(self):
        svc = _build_default_service()
        crd = svc.to_crd()
        head = crd["spec"]["rayClusterConfig"]["headGroupSpec"]
        assert head["rayStartParams"]["dashboard-host"] == "0.0.0.0"


# ──────────────────────────────────────────────
# raw_overrides
# ──────────────────────────────────────────────


class TestServiceCRDRawOverrides:
    """Verify raw_overrides are deep-merged into the CRD."""

    def test_raw_overrides_applied(self):
        svc = _build_default_service(
            raw_overrides={
                "spec": {
                    "serviceUnhealthySecondThreshold": 600,
                    "deploymentUnhealthySecondThreshold": 120,
                }
            },
        )
        crd = svc.to_crd()
        assert crd["spec"]["serviceUnhealthySecondThreshold"] == 600
        assert crd["spec"]["deploymentUnhealthySecondThreshold"] == 120

    def test_raw_overrides_do_not_clobber_existing_keys(self):
        svc = _build_default_service(
            raw_overrides={"spec": {"serviceUnhealthySecondThreshold": 900}},
        )
        crd = svc.to_crd()
        # serveConfigV2 and rayClusterConfig should still be present
        assert "serveConfigV2" in crd["spec"]
        assert "rayClusterConfig" in crd["spec"]
