"""Contract tests: SDK-generated RayCluster CRD matches RAYCLUSTER_SCHEMA (T014).

These tests verify that the cluster model's ``to_crd()`` output conforms to
the RayCluster CRD contract defined in ``specs/.../contracts/crd_schemas.py``.

TDD: these tests are written BEFORE the ``kuberay_sdk.models.cluster`` module
exists.  They will fail on import until the implementation is created.
"""

from __future__ import annotations

# ── Imports that will fail until implementation exists ──
from kuberay_sdk.models.cluster import (
    ClusterConfig,
    HeadNodeConfig,
    WorkerGroup,
)

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _build_default_cluster(**overrides) -> ClusterConfig:
    """Build a ClusterConfig with sensible defaults, merging *overrides*."""
    defaults = {
        "name": "test-cluster",
        "namespace": "default",
        "workers": 2,
        "ray_version": "2.41.0",
    }
    defaults.update(overrides)
    return ClusterConfig(**defaults)


def _head_container(crd: dict) -> dict:
    """Extract the first container from headGroupSpec."""
    return crd["spec"]["headGroupSpec"]["template"]["spec"]["containers"][0]


def _worker_container(crd: dict, group_idx: int = 0) -> dict:
    """Extract the first container from a workerGroupSpec."""
    return crd["spec"]["workerGroupSpecs"][group_idx]["template"]["spec"]["containers"][0]


# ──────────────────────────────────────────────
# apiVersion and kind
# ──────────────────────────────────────────────


class TestCRDTopLevel:
    """Verify top-level CRD fields: apiVersion, kind."""

    def test_api_version(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        assert crd["apiVersion"] == "ray.io/v1"

    def test_kind(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        assert crd["kind"] == "RayCluster"


# ──────────────────────────────────────────────
# metadata
# ──────────────────────────────────────────────


class TestCRDMetadata:
    """Verify metadata structure: name, namespace, labels, annotations."""

    def test_metadata_name(self):
        cluster = _build_default_cluster(name="my-cluster")
        crd = cluster.to_crd()
        assert crd["metadata"]["name"] == "my-cluster"

    def test_metadata_namespace(self):
        cluster = _build_default_cluster(namespace="ml-team")
        crd = cluster.to_crd()
        assert crd["metadata"]["namespace"] == "ml-team"

    def test_metadata_has_labels_dict(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        assert isinstance(crd["metadata"]["labels"], dict)

    def test_metadata_has_annotations_dict(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        assert isinstance(crd["metadata"]["annotations"], dict)

    def test_custom_labels_propagated(self):
        cluster = _build_default_cluster(labels={"team": "ml", "env": "dev"})
        crd = cluster.to_crd()
        assert crd["metadata"]["labels"]["team"] == "ml"
        assert crd["metadata"]["labels"]["env"] == "dev"

    def test_custom_annotations_propagated(self):
        cluster = _build_default_cluster(
            annotations={"note": "test-cluster"},
        )
        crd = cluster.to_crd()
        assert crd["metadata"]["annotations"]["note"] == "test-cluster"


# ──────────────────────────────────────────────
# rayVersion
# ──────────────────────────────────────────────


class TestCRDRayVersion:
    """Verify spec.rayVersion is set correctly."""

    def test_ray_version_set(self):
        cluster = _build_default_cluster(ray_version="2.41.0")
        crd = cluster.to_crd()
        assert crd["spec"]["rayVersion"] == "2.41.0"

    def test_ray_version_custom(self):
        cluster = _build_default_cluster(ray_version="2.39.0")
        crd = cluster.to_crd()
        assert crd["spec"]["rayVersion"] == "2.39.0"


# ──────────────────────────────────────────────
# headGroupSpec
# ──────────────────────────────────────────────


class TestCRDHeadGroupSpec:
    """Verify headGroupSpec structure matches contract."""

    def test_dashboard_host_param(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        head = crd["spec"]["headGroupSpec"]
        assert head["rayStartParams"]["dashboard-host"] == "0.0.0.0"

    def test_head_container_name(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        container = _head_container(crd)
        assert container["name"] == "ray-head"

    def test_head_container_image(self):
        cluster = _build_default_cluster(ray_version="2.41.0")
        crd = cluster.to_crd()
        container = _head_container(crd)
        assert container["image"] == "rayproject/ray:2.41.0"

    def test_head_container_image_custom(self):
        cluster = _build_default_cluster(image="custom-registry/ray:latest")
        crd = cluster.to_crd()
        container = _head_container(crd)
        assert container["image"] == "custom-registry/ray:latest"

    def test_head_resources_present(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        container = _head_container(crd)
        assert "requests" in container["resources"]
        assert "limits" in container["resources"]

    def test_head_default_resources(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        container = _head_container(crd)
        assert container["resources"]["requests"]["cpu"] == "1"
        assert container["resources"]["requests"]["memory"] == "2Gi"

    def test_head_custom_resources(self):
        head = HeadNodeConfig(cpus=4.0, memory="8Gi")
        cluster = _build_default_cluster(head=head)
        crd = cluster.to_crd()
        container = _head_container(crd)
        assert container["resources"]["requests"]["cpu"] == "4"
        assert container["resources"]["requests"]["memory"] == "8Gi"

    def test_head_ray_start_params_merged(self):
        head = HeadNodeConfig(ray_start_params={"num-cpus": "0"})
        cluster = _build_default_cluster(head=head)
        crd = cluster.to_crd()
        params = crd["spec"]["headGroupSpec"]["rayStartParams"]
        # dashboard-host must always be present
        assert params["dashboard-host"] == "0.0.0.0"
        # custom param is also included
        assert params["num-cpus"] == "0"


# ──────────────────────────────────────────────
# workerGroupSpecs
# ──────────────────────────────────────────────


class TestCRDWorkerGroupSpecs:
    """Verify workerGroupSpecs structure matches contract."""

    def test_default_worker_group_name(self):
        cluster = _build_default_cluster(workers=3)
        crd = cluster.to_crd()
        groups = crd["spec"]["workerGroupSpecs"]
        assert len(groups) == 1
        assert groups[0]["groupName"] == "default-workers"

    def test_worker_replicas(self):
        cluster = _build_default_cluster(workers=5)
        crd = cluster.to_crd()
        group = crd["spec"]["workerGroupSpecs"][0]
        assert group["replicas"] == 5

    def test_worker_min_max_replicas_equal_replicas_by_default(self):
        cluster = _build_default_cluster(workers=3)
        crd = cluster.to_crd()
        group = crd["spec"]["workerGroupSpecs"][0]
        assert group["minReplicas"] == 3
        assert group["maxReplicas"] == 3

    def test_worker_container_name(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        container = _worker_container(crd)
        assert container["name"] == "ray-worker"

    def test_worker_container_image(self):
        cluster = _build_default_cluster(ray_version="2.41.0")
        crd = cluster.to_crd()
        container = _worker_container(crd)
        assert container["image"] == "rayproject/ray:2.41.0"

    def test_worker_resources(self):
        cluster = _build_default_cluster(
            cpus_per_worker=2.0, memory_per_worker="4Gi",
        )
        crd = cluster.to_crd()
        container = _worker_container(crd)
        assert container["resources"]["requests"]["cpu"] == "2"
        assert container["resources"]["requests"]["memory"] == "4Gi"
        assert container["resources"]["limits"]["cpu"] == "2"
        assert container["resources"]["limits"]["memory"] == "4Gi"

    def test_worker_ray_start_params_is_dict(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        group = crd["spec"]["workerGroupSpecs"][0]
        assert isinstance(group["rayStartParams"], dict)


# ──────────────────────────────────────────────
# Advanced: multiple worker groups
# ──────────────────────────────────────────────


class TestCRDMultipleWorkerGroups:
    """Verify multi-group CRD generation."""

    def test_multiple_groups_count(self):
        groups = [
            WorkerGroup(name="cpu-pool", replicas=4, cpus=4.0, memory="8Gi"),
            WorkerGroup(name="gpu-pool", replicas=2, gpus=1, memory="16Gi"),
        ]
        cluster = _build_default_cluster(worker_groups=groups)
        crd = cluster.to_crd()
        assert len(crd["spec"]["workerGroupSpecs"]) == 2

    def test_group_names_preserved(self):
        groups = [
            WorkerGroup(name="cpu-pool", replicas=4),
            WorkerGroup(name="gpu-pool", replicas=2, gpus=1),
        ]
        cluster = _build_default_cluster(worker_groups=groups)
        crd = cluster.to_crd()
        names = [g["groupName"] for g in crd["spec"]["workerGroupSpecs"]]
        assert names == ["cpu-pool", "gpu-pool"]

    def test_each_group_has_correct_replicas(self):
        groups = [
            WorkerGroup(name="small", replicas=10),
            WorkerGroup(name="large", replicas=2, cpus=8.0, memory="32Gi"),
        ]
        cluster = _build_default_cluster(worker_groups=groups)
        crd = cluster.to_crd()
        assert crd["spec"]["workerGroupSpecs"][0]["replicas"] == 10
        assert crd["spec"]["workerGroupSpecs"][1]["replicas"] == 2

    def test_each_group_has_own_resources(self):
        groups = [
            WorkerGroup(name="cpu-pool", replicas=4, cpus=4.0, memory="8Gi"),
            WorkerGroup(name="gpu-pool", replicas=2, cpus=2.0, memory="16Gi", gpus=1),
        ]
        cluster = _build_default_cluster(worker_groups=groups)
        crd = cluster.to_crd()
        cpu_container = _worker_container(crd, group_idx=0)
        gpu_container = _worker_container(crd, group_idx=1)
        assert cpu_container["resources"]["requests"]["cpu"] == "4"
        assert cpu_container["resources"]["requests"]["memory"] == "8Gi"
        assert gpu_container["resources"]["requests"]["cpu"] == "2"
        assert gpu_container["resources"]["requests"]["memory"] == "16Gi"


# ──────────────────────────────────────────────
# Resource format
# ──────────────────────────────────────────────


class TestCRDResourceFormat:
    """Verify resource requests/limits use correct K8s format (string values)."""

    def test_cpu_is_string(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        container = _head_container(crd)
        assert isinstance(container["resources"]["requests"]["cpu"], str)
        assert isinstance(container["resources"]["limits"]["cpu"], str)

    def test_memory_is_string(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        container = _head_container(crd)
        assert isinstance(container["resources"]["requests"]["memory"], str)
        assert isinstance(container["resources"]["limits"]["memory"], str)

    def test_worker_cpu_is_string(self):
        cluster = _build_default_cluster(cpus_per_worker=2.5)
        crd = cluster.to_crd()
        container = _worker_container(crd)
        # cpu should be a string like "2.5" or "2500m"
        assert isinstance(container["resources"]["requests"]["cpu"], str)

    def test_requests_and_limits_match(self):
        cluster = _build_default_cluster(cpus_per_worker=2.0, memory_per_worker="4Gi")
        crd = cluster.to_crd()
        container = _worker_container(crd)
        assert container["resources"]["requests"] == container["resources"]["limits"]


# ──────────────────────────────────────────────
# GPU handling
# ──────────────────────────────────────────────


class TestCRDGPUResources:
    """Verify GPU resources are only included when gpus > 0."""

    def test_no_gpu_key_when_gpus_zero(self):
        cluster = _build_default_cluster(gpus_per_worker=0)
        crd = cluster.to_crd()
        container = _worker_container(crd)
        assert "nvidia.com/gpu" not in container["resources"]["requests"]
        assert "nvidia.com/gpu" not in container["resources"]["limits"]

    def test_no_gpu_key_in_head_when_gpus_zero(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        container = _head_container(crd)
        assert "nvidia.com/gpu" not in container["resources"]["requests"]
        assert "nvidia.com/gpu" not in container["resources"]["limits"]

    def test_gpu_key_present_when_gpus_positive(self):
        cluster = _build_default_cluster(gpus_per_worker=2)
        crd = cluster.to_crd()
        container = _worker_container(crd)
        assert container["resources"]["requests"]["nvidia.com/gpu"] == "2"
        assert container["resources"]["limits"]["nvidia.com/gpu"] == "2"

    def test_gpu_key_is_string(self):
        cluster = _build_default_cluster(gpus_per_worker=1)
        crd = cluster.to_crd()
        container = _worker_container(crd)
        assert isinstance(container["resources"]["requests"]["nvidia.com/gpu"], str)

    def test_head_gpu_when_configured(self):
        head = HeadNodeConfig(gpus=1)
        cluster = _build_default_cluster(head=head)
        crd = cluster.to_crd()
        container = _head_container(crd)
        assert container["resources"]["requests"]["nvidia.com/gpu"] == "1"

    def test_worker_group_gpu_type_custom(self):
        groups = [
            WorkerGroup(
                name="amd-pool",
                replicas=2,
                gpus=1,
                gpu_type="amd.com/gpu",
            ),
        ]
        cluster = _build_default_cluster(worker_groups=groups)
        crd = cluster.to_crd()
        container = _worker_container(crd, group_idx=0)
        assert "amd.com/gpu" in container["resources"]["requests"]
        assert container["resources"]["requests"]["amd.com/gpu"] == "1"
        # Default nvidia key should NOT be present
        assert "nvidia.com/gpu" not in container["resources"]["requests"]

    def test_worker_group_no_gpu_when_zero(self):
        groups = [WorkerGroup(name="cpu-only", replicas=4, gpus=0)]
        cluster = _build_default_cluster(worker_groups=groups)
        crd = cluster.to_crd()
        container = _worker_container(crd, group_idx=0)
        assert "nvidia.com/gpu" not in container["resources"]["requests"]


# ──────────────────────────────────────────────
# Overall schema shape
# ──────────────────────────────────────────────


class TestCRDSchemaShape:
    """Verify the overall CRD dict has the expected top-level keys."""

    def test_top_level_keys(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        assert set(crd.keys()) >= {"apiVersion", "kind", "metadata", "spec"}

    def test_spec_contains_head_and_workers(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        spec = crd["spec"]
        assert "headGroupSpec" in spec
        assert "workerGroupSpecs" in spec
        assert "rayVersion" in spec

    def test_worker_group_spec_structure(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        group = crd["spec"]["workerGroupSpecs"][0]
        required_keys = {"groupName", "replicas", "minReplicas", "maxReplicas",
                         "rayStartParams", "template"}
        assert required_keys.issubset(set(group.keys()))

    def test_head_group_spec_structure(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        head = crd["spec"]["headGroupSpec"]
        assert "rayStartParams" in head
        assert "template" in head
        assert "spec" in head["template"]
        assert "containers" in head["template"]["spec"]


# ──────────────────────────────────────────────
# Storage volumes in CRD (T049 / US5)
# ──────────────────────────────────────────────


class TestCRDStorageVolumes:
    """Verify cluster CRD with storage has correct volumes/volumeMounts (T049)."""

    def test_cluster_with_storage_has_volumes_in_head(self):
        from kuberay_sdk.models.storage import StorageVolume

        vol = StorageVolume(name="data", size="100Gi", mount_path="/data")
        cluster = _build_default_cluster(storage=[vol])
        crd = cluster.to_crd()
        head_spec = crd["spec"]["headGroupSpec"]["template"]["spec"]
        assert "volumes" in head_spec
        vol_names = [v["name"] for v in head_spec["volumes"]]
        assert "data" in vol_names

    def test_cluster_with_storage_has_volume_mounts_in_head_container(self):
        from kuberay_sdk.models.storage import StorageVolume

        vol = StorageVolume(name="data", size="100Gi", mount_path="/data")
        cluster = _build_default_cluster(storage=[vol])
        crd = cluster.to_crd()
        container = _head_container(crd)
        assert "volumeMounts" in container
        mount_paths = [m["mountPath"] for m in container["volumeMounts"]]
        assert "/data" in mount_paths

    def test_cluster_with_storage_has_volume_mounts_in_worker_container(self):
        from kuberay_sdk.models.storage import StorageVolume

        vol = StorageVolume(name="models", existing_claim="shared-models", mount_path="/models")
        cluster = _build_default_cluster(storage=[vol])
        crd = cluster.to_crd()
        container = _worker_container(crd)
        assert "volumeMounts" in container
        mount_paths = [m["mountPath"] for m in container["volumeMounts"]]
        assert "/models" in mount_paths

    def test_existing_claim_uses_claim_name_in_volume_spec(self):
        from kuberay_sdk.models.storage import StorageVolume

        vol = StorageVolume(name="data", existing_claim="my-pvc", mount_path="/data")
        cluster = _build_default_cluster(storage=[vol])
        crd = cluster.to_crd()
        head_spec = crd["spec"]["headGroupSpec"]["template"]["spec"]
        pvc_vol = next(v for v in head_spec["volumes"] if v["name"] == "data")
        assert pvc_vol["persistentVolumeClaim"]["claimName"] == "my-pvc"

    def test_multiple_storage_volumes_all_present(self):
        from kuberay_sdk.models.storage import StorageVolume

        vols = [
            StorageVolume(name="data", size="100Gi", mount_path="/data"),
            StorageVolume(name="logs", size="10Gi", mount_path="/logs"),
        ]
        cluster = _build_default_cluster(storage=vols)
        crd = cluster.to_crd()
        head_spec = crd["spec"]["headGroupSpec"]["template"]["spec"]
        vol_names = [v["name"] for v in head_spec["volumes"]]
        assert "data" in vol_names
        assert "logs" in vol_names
        container = _head_container(crd)
        mount_paths = [m["mountPath"] for m in container["volumeMounts"]]
        assert "/data" in mount_paths
        assert "/logs" in mount_paths

    def test_no_storage_no_volumes_key(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        head_spec = crd["spec"]["headGroupSpec"]["template"]["spec"]
        assert "volumes" not in head_spec

    def test_no_storage_no_volume_mounts_key(self):
        cluster = _build_default_cluster()
        crd = cluster.to_crd()
        container = _head_container(crd)
        assert "volumeMounts" not in container
