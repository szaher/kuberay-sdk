"""Unit tests for cluster models (T015), StorageVolume (T047),
RuntimeEnv (T048), and ExperimentTracking (T067).

Tests for WorkerGroup, HeadNodeConfig, ClusterConfig, ClusterStatus,
StorageVolume, RuntimeEnv, and ExperimentTracking.
These cover validation rules, defaults, and edge cases defined in the
data model specification.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
import yaml

from kuberay_sdk.errors import ValidationError

# ── Imports that will fail until implementation exists ──
from kuberay_sdk.models.cluster import (
    ClusterConfig,
    ClusterStatus,
    HeadNodeConfig,
    WorkerGroup,
)
from kuberay_sdk.models.runtime_env import ExperimentTracking, RuntimeEnv
from kuberay_sdk.models.storage import StorageVolume

# ──────────────────────────────────────────────
# WorkerGroup
# ──────────────────────────────────────────────


class TestWorkerGroupCreation:
    """Test WorkerGroup construction and defaults."""

    def test_create_with_required_params(self):
        wg = WorkerGroup(name="cpu-workers", replicas=4)
        assert wg.name == "cpu-workers"
        assert wg.replicas == 4

    def test_default_cpus(self):
        wg = WorkerGroup(name="default", replicas=1)
        assert wg.cpus == 1.0

    def test_default_memory(self):
        wg = WorkerGroup(name="default", replicas=1)
        assert wg.memory == "2Gi"

    def test_default_gpus(self):
        wg = WorkerGroup(name="default", replicas=1)
        assert wg.gpus == 0

    def test_custom_resources(self):
        wg = WorkerGroup(name="gpu-pool", replicas=2, cpus=8.0, gpus=4, memory="32Gi")
        assert wg.cpus == 8.0
        assert wg.gpus == 4
        assert wg.memory == "32Gi"

    def test_custom_gpu_type(self):
        wg = WorkerGroup(name="amd", replicas=1, gpus=1, gpu_type="amd.com/gpu")
        assert wg.gpu_type == "amd.com/gpu"

    def test_default_gpu_type_is_none(self):
        wg = WorkerGroup(name="cpu", replicas=1)
        assert wg.gpu_type is None

    def test_ray_start_params(self):
        wg = WorkerGroup(
            name="custom", replicas=2,
            ray_start_params={"num-cpus": "4"},
        )
        assert wg.ray_start_params == {"num-cpus": "4"}

    def test_default_ray_start_params_is_none(self):
        wg = WorkerGroup(name="default", replicas=1)
        assert wg.ray_start_params is None


class TestWorkerGroupReplicaValidation:
    """Test min_replicas <= replicas <= max_replicas constraint."""

    def test_min_replicas_defaults_to_replicas(self):
        wg = WorkerGroup(name="pool", replicas=3)
        # When min_replicas is not set, it should default to replicas
        assert wg.min_replicas is None or wg.min_replicas == 3

    def test_max_replicas_defaults_to_replicas(self):
        wg = WorkerGroup(name="pool", replicas=3)
        # When max_replicas is not set, it should default to replicas
        assert wg.max_replicas is None or wg.max_replicas == 3

    def test_explicit_min_max_replicas(self):
        wg = WorkerGroup(name="pool", replicas=3, min_replicas=1, max_replicas=10)
        assert wg.min_replicas == 1
        assert wg.max_replicas == 10

    def test_min_replicas_greater_than_replicas_raises(self):
        with pytest.raises((ValidationError, ValueError)):
            WorkerGroup(name="bad", replicas=3, min_replicas=5)

    def test_max_replicas_less_than_replicas_raises(self):
        with pytest.raises((ValidationError, ValueError)):
            WorkerGroup(name="bad", replicas=5, max_replicas=2)

    def test_min_replicas_greater_than_max_replicas_raises(self):
        with pytest.raises((ValidationError, ValueError)):
            WorkerGroup(name="bad", replicas=5, min_replicas=8, max_replicas=3)

    def test_replicas_must_be_positive(self):
        with pytest.raises((ValidationError, ValueError)):
            WorkerGroup(name="bad", replicas=0)

    def test_replicas_negative_raises(self):
        with pytest.raises((ValidationError, ValueError)):
            WorkerGroup(name="bad", replicas=-1)


# ──────────────────────────────────────────────
# HeadNodeConfig
# ──────────────────────────────────────────────


class TestHeadNodeConfig:
    """Test HeadNodeConfig defaults and overrides."""

    def test_default_cpus(self):
        head = HeadNodeConfig()
        assert head.cpus == 1.0

    def test_default_memory(self):
        head = HeadNodeConfig()
        assert head.memory == "2Gi"

    def test_default_gpus(self):
        head = HeadNodeConfig()
        assert head.gpus == 0

    def test_override_cpus(self):
        head = HeadNodeConfig(cpus=4.0)
        assert head.cpus == 4.0

    def test_override_memory(self):
        head = HeadNodeConfig(memory="16Gi")
        assert head.memory == "16Gi"

    def test_override_gpus(self):
        head = HeadNodeConfig(gpus=1)
        assert head.gpus == 1

    def test_ray_start_params_default(self):
        head = HeadNodeConfig()
        assert head.ray_start_params is None

    def test_ray_start_params_override(self):
        head = HeadNodeConfig(ray_start_params={"num-cpus": "0"})
        assert head.ray_start_params == {"num-cpus": "0"}


# ──────────────────────────────────────────────
# ClusterConfig — K8s name validation
# ──────────────────────────────────────────────


class TestClusterConfigNameValidation:
    """K8s resource names: lowercase, alphanumeric + hyphens, max 63 chars."""

    def test_valid_simple_name(self):
        cluster = ClusterConfig(name="my-cluster", workers=1)
        assert cluster.name == "my-cluster"

    def test_valid_name_with_numbers(self):
        cluster = ClusterConfig(name="cluster-123", workers=1)
        assert cluster.name == "cluster-123"

    def test_valid_single_char_name(self):
        cluster = ClusterConfig(name="a", workers=1)
        assert cluster.name == "a"

    def test_max_length_63_chars(self):
        name = "a" * 63
        cluster = ClusterConfig(name=name, workers=1)
        assert cluster.name == name

    def test_name_too_long_64_chars_raises(self):
        name = "a" * 64
        with pytest.raises((ValidationError, ValueError)):
            ClusterConfig(name=name, workers=1)

    def test_uppercase_name_raises(self):
        with pytest.raises((ValidationError, ValueError)):
            ClusterConfig(name="MyCluster", workers=1)

    def test_underscore_name_raises(self):
        with pytest.raises((ValidationError, ValueError)):
            ClusterConfig(name="my_cluster", workers=1)

    def test_dot_name_raises(self):
        with pytest.raises((ValidationError, ValueError)):
            ClusterConfig(name="my.cluster", workers=1)

    def test_space_name_raises(self):
        with pytest.raises((ValidationError, ValueError)):
            ClusterConfig(name="my cluster", workers=1)

    def test_empty_name_raises(self):
        with pytest.raises((ValidationError, ValueError)):
            ClusterConfig(name="", workers=1)

    def test_name_starting_with_hyphen_raises(self):
        with pytest.raises((ValidationError, ValueError)):
            ClusterConfig(name="-invalid", workers=1)

    def test_name_ending_with_hyphen_raises(self):
        with pytest.raises((ValidationError, ValueError)):
            ClusterConfig(name="invalid-", workers=1)


# ──────────────────────────────────────────────
# ClusterConfig — mutual exclusivity
# ──────────────────────────────────────────────


class TestClusterConfigMutualExclusivity:
    """workers vs worker_groups: using both must raise ValidationError."""

    def test_workers_only_is_valid(self):
        cluster = ClusterConfig(name="test", workers=4)
        assert cluster.workers == 4

    def test_worker_groups_only_is_valid(self):
        groups = [WorkerGroup(name="pool", replicas=2)]
        cluster = ClusterConfig(name="test", worker_groups=groups)
        assert cluster.worker_groups is not None
        assert len(cluster.worker_groups) == 1

    def test_both_workers_and_worker_groups_raises(self):
        groups = [WorkerGroup(name="pool", replicas=2)]
        with pytest.raises((ValidationError, ValueError)):
            ClusterConfig(name="test", workers=4, worker_groups=groups)

    def test_neither_workers_nor_groups_uses_defaults(self):
        # When neither is explicitly provided, defaults should apply
        # (workers defaults to 1)
        cluster = ClusterConfig(name="test")
        assert cluster.workers == 1 or cluster.worker_groups is not None


# ──────────────────────────────────────────────
# ClusterConfig — defaults
# ──────────────────────────────────────────────


class TestClusterConfigDefaults:
    """Verify default values for cluster configuration."""

    def test_default_workers(self):
        cluster = ClusterConfig(name="test")
        assert cluster.workers == 1

    def test_default_cpus_per_worker(self):
        cluster = ClusterConfig(name="test")
        assert cluster.cpus_per_worker == 1.0

    def test_default_memory_per_worker(self):
        cluster = ClusterConfig(name="test")
        assert cluster.memory_per_worker == "2Gi"

    def test_default_gpus_per_worker(self):
        cluster = ClusterConfig(name="test")
        assert cluster.gpus_per_worker == 0

    def test_default_namespace_is_none(self):
        cluster = ClusterConfig(name="test")
        assert cluster.namespace is None

    def test_default_labels_empty(self):
        cluster = ClusterConfig(name="test")
        assert cluster.labels is None or cluster.labels == {}

    def test_default_annotations_empty(self):
        cluster = ClusterConfig(name="test")
        assert cluster.annotations is None or cluster.annotations == {}

    def test_default_enable_autoscaling_false(self):
        cluster = ClusterConfig(name="test")
        assert cluster.enable_autoscaling is False


# ──────────────────────────────────────────────
# ClusterStatus — read-only
# ──────────────────────────────────────────────


class TestClusterStatus:
    """ClusterStatus is a read-only object parsed from K8s CR status."""

    def test_status_has_required_fields(self):
        status = ClusterStatus(
            name="my-cluster",
            namespace="default",
            state="RUNNING",
            head_ready=True,
            workers_ready=4,
            workers_desired=4,
            ray_version="2.41.0",
            dashboard_url=None,
            age=timedelta(hours=1),
            conditions=[],
        )
        assert status.name == "my-cluster"
        assert status.namespace == "default"
        assert status.state == "RUNNING"
        assert status.head_ready is True
        assert status.workers_ready == 4
        assert status.workers_desired == 4
        assert status.ray_version == "2.41.0"

    def test_status_dashboard_url_optional(self):
        status = ClusterStatus(
            name="test",
            namespace="default",
            state="CREATING",
            head_ready=False,
            workers_ready=0,
            workers_desired=2,
            ray_version="2.41.0",
            dashboard_url=None,
            age=timedelta(seconds=30),
            conditions=[],
        )
        assert status.dashboard_url is None

    def test_status_with_dashboard_url(self):
        status = ClusterStatus(
            name="test",
            namespace="default",
            state="RUNNING",
            head_ready=True,
            workers_ready=2,
            workers_desired=2,
            ray_version="2.41.0",
            dashboard_url="http://10.0.0.1:8265",
            age=timedelta(minutes=5),
            conditions=[],
        )
        assert status.dashboard_url == "http://10.0.0.1:8265"

    def test_status_age_is_timedelta(self):
        status = ClusterStatus(
            name="test",
            namespace="default",
            state="RUNNING",
            head_ready=True,
            workers_ready=1,
            workers_desired=1,
            ray_version="2.41.0",
            dashboard_url=None,
            age=timedelta(hours=2, minutes=30),
            conditions=[],
        )
        assert isinstance(status.age, timedelta)
        assert status.age == timedelta(hours=2, minutes=30)

    def test_status_conditions_list(self):
        conditions = [
            {"type": "HeadPodReady", "status": "True"},
            {"type": "RayClusterProvisioned", "status": "True"},
        ]
        status = ClusterStatus(
            name="test",
            namespace="default",
            state="RUNNING",
            head_ready=True,
            workers_ready=1,
            workers_desired=1,
            ray_version="2.41.0",
            dashboard_url=None,
            age=timedelta(minutes=1),
            conditions=conditions,
        )
        assert len(status.conditions) == 2

    def test_status_is_read_only(self):
        """ClusterStatus fields should not be freely mutable."""
        status = ClusterStatus(
            name="test",
            namespace="default",
            state="RUNNING",
            head_ready=True,
            workers_ready=1,
            workers_desired=1,
            ray_version="2.41.0",
            dashboard_url=None,
            age=timedelta(minutes=1),
            conditions=[],
        )
        # Attempting to change state should raise (frozen model or property)
        with pytest.raises((AttributeError, TypeError, Exception)):
            status.state = "FAILED"  # type: ignore[misc]


# ──────────────────────────────────────────────
# ClusterConfig — additional validation
# ──────────────────────────────────────────────


class TestClusterConfigResourceValidation:
    """Resource parameter validation."""

    def test_cpus_per_worker_must_be_positive(self):
        with pytest.raises((ValidationError, ValueError)):
            ClusterConfig(name="test", cpus_per_worker=0.0)

    def test_cpus_per_worker_negative_raises(self):
        with pytest.raises((ValidationError, ValueError)):
            ClusterConfig(name="test", cpus_per_worker=-1.0)

    def test_gpus_per_worker_negative_raises(self):
        with pytest.raises((ValidationError, ValueError)):
            ClusterConfig(name="test", gpus_per_worker=-1)

    def test_workers_must_be_at_least_one(self):
        with pytest.raises((ValidationError, ValueError)):
            ClusterConfig(name="test", workers=0)

    def test_fractional_cpus_allowed(self):
        cluster = ClusterConfig(name="test", cpus_per_worker=0.5)
        assert cluster.cpus_per_worker == 0.5


# ──────────────────────────────────────────────
# StorageVolume (T047)
# ──────────────────────────────────────────────


class TestStorageVolume:
    """Tests for StorageVolume model: PVC creation, validation, and output dicts."""

    def test_create_with_new_pvc(self):
        """A new PVC is created when size and mount_path are given."""
        vol = StorageVolume(name="data-vol", size="10Gi", mount_path="/data")
        assert vol.size == "10Gi"
        assert vol.mount_path == "/data"
        assert vol.existing_claim is None

    def test_create_with_existing_claim(self):
        """An existing PVC can be referenced by claim name."""
        vol = StorageVolume(name="data-vol", existing_claim="my-pvc", mount_path="/data")
        assert vol.existing_claim == "my-pvc"
        assert vol.size is None

    def test_size_and_existing_claim_mutually_exclusive(self):
        """Setting both size and existing_claim must raise ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            StorageVolume(
                name="bad-vol",
                size="10Gi",
                existing_claim="my-pvc",
                mount_path="/data",
            )

    def test_neither_size_nor_existing_claim_raises(self):
        """Omitting both size and existing_claim must raise ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            StorageVolume(name="bad-vol", mount_path="/data")

    def test_mount_path_must_be_absolute(self):
        """A relative mount_path must be rejected."""
        with pytest.raises((ValidationError, ValueError)):
            StorageVolume(name="bad-vol", size="10Gi", mount_path="relative/path")

    @pytest.mark.parametrize(
        "mode", ["ReadWriteOnce", "ReadOnlyMany", "ReadWriteMany"]
    )
    def test_valid_access_modes(self, mode: str):
        """All three standard PVC access modes must be accepted."""
        vol = StorageVolume(
            name="vol", size="5Gi", mount_path="/mnt", access_mode=mode
        )
        assert vol.access_mode == mode

    def test_to_volume_spec_returns_dict(self):
        """to_volume_spec must return a K8s volume spec dict."""
        vol = StorageVolume(name="data", size="10Gi", mount_path="/data")
        spec = vol.to_volume_spec()
        assert isinstance(spec, dict)
        assert spec["name"] == "data"
        assert "persistentVolumeClaim" in spec
        assert spec["persistentVolumeClaim"]["claimName"] == "data"

    def test_to_volume_spec_existing_claim(self):
        """to_volume_spec for existing claim uses the claim name."""
        vol = StorageVolume(
            name="models", existing_claim="shared-models", mount_path="/models"
        )
        spec = vol.to_volume_spec()
        assert spec["persistentVolumeClaim"]["claimName"] == "shared-models"

    def test_to_volume_mount_returns_dict(self):
        """to_volume_mount must return a dict with name and mountPath."""
        vol = StorageVolume(name="data", size="10Gi", mount_path="/data")
        mount = vol.to_volume_mount()
        assert isinstance(mount, dict)
        assert mount["name"] == "data"
        assert mount["mountPath"] == "/data"

    def test_to_pvc_manifest_returns_dict(self):
        """to_pvc_manifest for a new PVC must return a valid PVC manifest dict."""
        vol = StorageVolume(name="data", size="10Gi", mount_path="/data")
        manifest = vol.to_pvc_manifest(namespace="default")
        assert isinstance(manifest, dict)
        assert manifest["apiVersion"] == "v1"
        assert manifest["kind"] == "PersistentVolumeClaim"
        assert manifest["metadata"]["name"] == "data"
        assert manifest["metadata"]["namespace"] == "default"
        assert manifest["spec"]["accessModes"] == ["ReadWriteOnce"]
        assert manifest["spec"]["resources"]["requests"]["storage"] == "10Gi"

    def test_to_pvc_manifest_existing_claim_returns_none(self):
        """to_pvc_manifest for an existing claim must return None."""
        vol = StorageVolume(
            name="ext", existing_claim="my-pvc", mount_path="/ext"
        )
        assert vol.to_pvc_manifest(namespace="default") is None

    def test_default_access_mode_is_readwriteonce(self):
        """The default access_mode must be ReadWriteOnce."""
        vol = StorageVolume(name="vol", size="1Gi", mount_path="/vol")
        assert vol.access_mode == "ReadWriteOnce"

    def test_invalid_access_mode_raises(self):
        """An invalid access_mode must raise ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            StorageVolume(
                name="vol",
                size="1Gi",
                mount_path="/vol",
                access_mode="InvalidMode",
            )

    def test_to_pvc_manifest_with_storage_class(self):
        """to_pvc_manifest must include storageClassName when set."""
        vol = StorageVolume(
            name="fast", size="50Gi", mount_path="/fast", storage_class="ssd"
        )
        manifest = vol.to_pvc_manifest(namespace="prod")
        assert manifest["spec"]["storageClassName"] == "ssd"


# ──────────────────────────────────────────────
# RuntimeEnv (T048)
# ──────────────────────────────────────────────


class TestRuntimeEnv:
    """Tests for RuntimeEnv model: pip/conda packages, env vars, serialization."""

    def test_create_with_pip_packages(self):
        """RuntimeEnv can be created with pip packages."""
        env = RuntimeEnv(pip=["torch", "transformers"])
        assert env.pip == ["torch", "transformers"]
        assert env.conda is None

    def test_create_with_conda_packages(self):
        """RuntimeEnv can be created with conda packages (as dict)."""
        conda_spec = {
            "dependencies": ["numpy", "pandas", {"pip": ["torch"]}]
        }
        env = RuntimeEnv(conda=conda_spec)
        assert env.conda == conda_spec
        assert env.pip is None

    def test_pip_and_conda_mutually_exclusive(self):
        """Setting both pip and conda must raise ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            RuntimeEnv(pip=["torch"], conda={"dependencies": ["numpy"]})

    def test_to_dict_includes_pip(self):
        """to_dict must include pip packages when set."""
        env = RuntimeEnv(pip=["torch", "numpy"])
        d = env.to_dict()
        assert "pip" in d
        assert d["pip"] == ["torch", "numpy"]

    def test_to_dict_includes_conda(self):
        """to_dict must include conda config when set."""
        conda_spec = {"dependencies": ["numpy"]}
        env = RuntimeEnv(conda=conda_spec)
        d = env.to_dict()
        assert "conda" in d
        assert d["conda"] == conda_spec

    def test_to_yaml_returns_string(self):
        """to_yaml must return a valid YAML string."""
        env = RuntimeEnv(pip=["torch"], env_vars={"KEY": "val"})
        result = env.to_yaml()
        assert isinstance(result, str)
        parsed = yaml.safe_load(result)
        assert parsed["pip"] == ["torch"]
        assert parsed["env_vars"]["KEY"] == "val"

    def test_env_vars_included_in_dict(self):
        """to_dict must include env_vars when set."""
        env = RuntimeEnv(pip=["torch"], env_vars={"MY_VAR": "123"})
        d = env.to_dict()
        assert "env_vars" in d
        assert d["env_vars"] == {"MY_VAR": "123"}

    def test_working_dir_included(self):
        """to_dict must include working_dir when set."""
        env = RuntimeEnv(pip=["torch"], working_dir="/home/ray/project")
        d = env.to_dict()
        assert "working_dir" in d
        assert d["working_dir"] == "/home/ray/project"

    def test_merge_env_vars_creates_new_instance(self):
        """merge_env_vars must return a new RuntimeEnv with merged vars."""
        original = RuntimeEnv(pip=["torch"], env_vars={"A": "1"})
        merged = original.merge_env_vars({"B": "2"})
        # Must be a new instance
        assert merged is not original
        # Original unchanged
        assert original.env_vars == {"A": "1"}
        # Merged has both
        assert merged.env_vars == {"A": "1", "B": "2"}
        # pip preserved
        assert merged.pip == ["torch"]

    def test_merge_env_vars_overwrites_existing(self):
        """merge_env_vars with overlapping keys should overwrite."""
        original = RuntimeEnv(pip=["torch"], env_vars={"A": "1"})
        merged = original.merge_env_vars({"A": "new"})
        assert merged.env_vars == {"A": "new"}
        assert original.env_vars == {"A": "1"}

    def test_merge_env_vars_from_none(self):
        """merge_env_vars on RuntimeEnv with no existing env_vars works."""
        original = RuntimeEnv(pip=["torch"])
        merged = original.merge_env_vars({"B": "2"})
        assert merged.env_vars == {"B": "2"}

    def test_empty_runtime_env(self):
        """An empty RuntimeEnv should produce an empty dict."""
        env = RuntimeEnv()
        d = env.to_dict()
        assert d == {}

    def test_to_dict_excludes_none_fields(self):
        """to_dict must not include keys for None fields."""
        env = RuntimeEnv(pip=["torch"])
        d = env.to_dict()
        assert "conda" not in d
        assert "env_vars" not in d
        assert "working_dir" not in d

    def test_py_modules_included_in_dict(self):
        """to_dict must include py_modules when set."""
        env = RuntimeEnv(pip=["torch"], py_modules=["my_module"])
        d = env.to_dict()
        assert "py_modules" in d
        assert d["py_modules"] == ["my_module"]


# ──────────────────────────────────────────────
# ExperimentTracking (T067)
# ──────────────────────────────────────────────


class TestExperimentTracking:
    """Tests for ExperimentTracking model: provider validation and env var generation."""

    def test_mlflow_provider_valid(self):
        """The 'mlflow' provider must be accepted."""
        et = ExperimentTracking(
            provider="mlflow", tracking_uri="http://mlflow:5000"
        )
        assert et.provider == "mlflow"
        assert et.tracking_uri == "http://mlflow:5000"

    def test_invalid_provider_raises(self):
        """Any provider other than 'mlflow' must raise ValidationError."""
        with pytest.raises((ValidationError, ValueError)):
            ExperimentTracking(
                provider="wandb", tracking_uri="http://wandb:8080"
            )

    def test_to_env_vars_includes_tracking_uri(self):
        """to_env_vars must include MLFLOW_TRACKING_URI."""
        et = ExperimentTracking(
            provider="mlflow", tracking_uri="http://mlflow:5000"
        )
        env = et.to_env_vars()
        assert "MLFLOW_TRACKING_URI" in env
        assert env["MLFLOW_TRACKING_URI"] == "http://mlflow:5000"

    def test_to_env_vars_includes_experiment_name(self):
        """to_env_vars must include MLFLOW_EXPERIMENT_NAME when set."""
        et = ExperimentTracking(
            provider="mlflow",
            tracking_uri="http://mlflow:5000",
            experiment_name="my-experiment",
        )
        env = et.to_env_vars()
        assert "MLFLOW_EXPERIMENT_NAME" in env
        assert env["MLFLOW_EXPERIMENT_NAME"] == "my-experiment"

    def test_to_env_vars_without_experiment_name(self):
        """to_env_vars must omit MLFLOW_EXPERIMENT_NAME when not set."""
        et = ExperimentTracking(
            provider="mlflow", tracking_uri="http://mlflow:5000"
        )
        env = et.to_env_vars()
        assert "MLFLOW_EXPERIMENT_NAME" not in env

    def test_to_env_vars_with_additional_vars(self):
        """to_env_vars must include extra env_vars when provided."""
        et = ExperimentTracking(
            provider="mlflow",
            tracking_uri="http://mlflow:5000",
            env_vars={"MLFLOW_S3_ENDPOINT_URL": "http://minio:9000"},
        )
        env = et.to_env_vars()
        assert env["MLFLOW_TRACKING_URI"] == "http://mlflow:5000"
        assert env["MLFLOW_S3_ENDPOINT_URL"] == "http://minio:9000"

    def test_tracking_uri_required(self):
        """Omitting tracking_uri must raise a validation error."""
        with pytest.raises((ValidationError, ValueError, TypeError)):
            ExperimentTracking(provider="mlflow")  # type: ignore[call-arg]

    def test_provider_required(self):
        """Omitting provider must raise a validation error."""
        with pytest.raises((ValidationError, ValueError, TypeError)):
            ExperimentTracking(tracking_uri="http://mlflow:5000")  # type: ignore[call-arg]
