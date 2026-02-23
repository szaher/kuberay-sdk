"""Contract tests: SDK-generated RayJob CRD matches RAYJOB_SCHEMA (T024).

These tests verify that the job model's ``to_crd_dict()`` output conforms to
the RayJob CRD contract defined in ``specs/.../contracts/crd_schemas.py``.

TDD: these tests are written BEFORE the ``kuberay_sdk.models.job`` module
exists.  They will fail on import until the implementation is created.
"""

from __future__ import annotations

import pytest
import yaml

from kuberay_sdk.models.cluster import HeadNodeConfig, WorkerGroup
from kuberay_sdk.models.common import JobMode, JobState

# ── Imports that will fail until implementation exists ──
from kuberay_sdk.models.job import JobConfig, JobStatus
from kuberay_sdk.models.runtime_env import ExperimentTracking, RuntimeEnv

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _build_default_job(**overrides) -> JobConfig:
    """Build a JobConfig with sensible defaults, merging *overrides*."""
    defaults = {
        "name": "test-job",
        "namespace": "default",
        "entrypoint": "python train.py",
        "workers": 2,
        "ray_version": "2.41.0",
    }
    defaults.update(overrides)
    return JobConfig(**defaults)


def _head_container(crd: dict) -> dict:
    """Extract the first container from headGroupSpec inside rayClusterSpec."""
    return crd["spec"]["rayClusterSpec"]["headGroupSpec"]["template"]["spec"]["containers"][0]


def _worker_container(crd: dict, group_idx: int = 0) -> dict:
    """Extract the first container from a workerGroupSpec inside rayClusterSpec."""
    return crd["spec"]["rayClusterSpec"]["workerGroupSpecs"][group_idx]["template"]["spec"]["containers"][0]


# ──────────────────────────────────────────────
# apiVersion and kind
# ──────────────────────────────────────────────


class TestJobCRDTopLevel:
    """Verify top-level CRD fields: apiVersion, kind."""

    def test_api_version(self):
        job = _build_default_job()
        crd = job.to_crd_dict()
        assert crd["apiVersion"] == "ray.io/v1"

    def test_kind(self):
        job = _build_default_job()
        crd = job.to_crd_dict()
        assert crd["kind"] == "RayJob"


# ──────────────────────────────────────────────
# metadata
# ──────────────────────────────────────────────


class TestJobCRDMetadata:
    """Verify metadata structure: name, namespace, labels, annotations."""

    def test_metadata_name(self):
        job = _build_default_job(name="my-job")
        crd = job.to_crd_dict()
        assert crd["metadata"]["name"] == "my-job"

    def test_metadata_namespace(self):
        job = _build_default_job(namespace="ml-team")
        crd = job.to_crd_dict()
        assert crd["metadata"]["namespace"] == "ml-team"

    def test_metadata_has_labels_dict(self):
        job = _build_default_job()
        crd = job.to_crd_dict()
        assert isinstance(crd["metadata"]["labels"], dict)

    def test_metadata_has_annotations_dict(self):
        job = _build_default_job()
        crd = job.to_crd_dict()
        assert isinstance(crd["metadata"]["annotations"], dict)

    def test_custom_labels_propagated(self):
        job = _build_default_job(labels={"team": "ml", "env": "dev"})
        crd = job.to_crd_dict()
        assert crd["metadata"]["labels"]["team"] == "ml"
        assert crd["metadata"]["labels"]["env"] == "dev"

    def test_custom_annotations_propagated(self):
        job = _build_default_job(annotations={"note": "test-job"})
        crd = job.to_crd_dict()
        assert crd["metadata"]["annotations"]["note"] == "test-job"


# ──────────────────────────────────────────────
# spec.entrypoint
# ──────────────────────────────────────────────


class TestJobCRDEntrypoint:
    """Verify spec.entrypoint is set correctly."""

    def test_entrypoint_set(self):
        job = _build_default_job(entrypoint="python train.py --epochs 10")
        crd = job.to_crd_dict()
        assert crd["spec"]["entrypoint"] == "python train.py --epochs 10"

    def test_entrypoint_required(self):
        """Entrypoint must not be empty."""
        with pytest.raises(Exception):
            _build_default_job(entrypoint="")

    def test_entrypoint_whitespace_only_rejected(self):
        """Entrypoint that is only whitespace must be rejected."""
        with pytest.raises(Exception):
            _build_default_job(entrypoint="   ")


# ──────────────────────────────────────────────
# spec.runtimeEnvYAML
# ──────────────────────────────────────────────


class TestJobCRDRuntimeEnvYAML:
    """Verify runtimeEnvYAML is a YAML string."""

    def test_runtime_env_yaml_present_when_set(self):
        runtime_env = RuntimeEnv(pip=["torch", "transformers"])
        job = _build_default_job(runtime_env=runtime_env)
        crd = job.to_crd_dict()
        assert "runtimeEnvYAML" in crd["spec"]
        assert isinstance(crd["spec"]["runtimeEnvYAML"], str)

    def test_runtime_env_yaml_is_valid_yaml(self):
        runtime_env = RuntimeEnv(pip=["torch"], env_vars={"KEY": "val"})
        job = _build_default_job(runtime_env=runtime_env)
        crd = job.to_crd_dict()
        parsed = yaml.safe_load(crd["spec"]["runtimeEnvYAML"])
        assert isinstance(parsed, dict)
        assert "pip" in parsed
        assert "torch" in parsed["pip"]

    def test_runtime_env_yaml_absent_when_not_set(self):
        job = _build_default_job()
        crd = job.to_crd_dict()
        # runtimeEnvYAML should be absent or empty when no runtime_env
        runtime_yaml = crd["spec"].get("runtimeEnvYAML")
        assert runtime_yaml is None or runtime_yaml == ""

    def test_runtime_env_dict_converted(self):
        """When runtime_env is a dict, it should be converted to YAML."""
        job = _build_default_job(runtime_env={"pip": ["numpy"]})
        crd = job.to_crd_dict()
        assert "runtimeEnvYAML" in crd["spec"]
        parsed = yaml.safe_load(crd["spec"]["runtimeEnvYAML"])
        assert "numpy" in parsed["pip"]

    def test_experiment_tracking_env_vars_merged(self):
        """ExperimentTracking env vars should be merged into runtimeEnvYAML."""
        runtime_env = RuntimeEnv(pip=["torch"])
        et = ExperimentTracking(
            provider="mlflow",
            tracking_uri="http://mlflow:5000",
            experiment_name="test-exp",
        )
        job = _build_default_job(runtime_env=runtime_env, experiment_tracking=et)
        crd = job.to_crd_dict()
        parsed = yaml.safe_load(crd["spec"]["runtimeEnvYAML"])
        assert parsed["env_vars"]["MLFLOW_TRACKING_URI"] == "http://mlflow:5000"
        assert parsed["env_vars"]["MLFLOW_EXPERIMENT_NAME"] == "test-exp"


# ──────────────────────────────────────────────
# spec.shutdownAfterJobFinishes
# ──────────────────────────────────────────────


class TestJobCRDShutdownAfterFinish:
    """Verify shutdownAfterJobFinishes field."""

    def test_shutdown_default_true(self):
        job = _build_default_job()
        crd = job.to_crd_dict()
        assert crd["spec"]["shutdownAfterJobFinishes"] is True

    def test_shutdown_explicit_true(self):
        job = _build_default_job(shutdown_after_finish=True)
        crd = job.to_crd_dict()
        assert crd["spec"]["shutdownAfterJobFinishes"] is True

    def test_shutdown_explicit_false(self):
        job = _build_default_job(shutdown_after_finish=False)
        crd = job.to_crd_dict()
        assert crd["spec"]["shutdownAfterJobFinishes"] is False

    def test_queue_requires_shutdown_true(self):
        """When queue is set, shutdown_after_finish must be True (Kueue constraint)."""
        with pytest.raises(Exception):
            _build_default_job(queue="my-queue", shutdown_after_finish=False)

    def test_queue_with_shutdown_true_ok(self):
        """Queue + shutdown=True should work fine."""
        job = _build_default_job(queue="my-queue", shutdown_after_finish=True)
        crd = job.to_crd_dict()
        assert crd["spec"]["shutdownAfterJobFinishes"] is True


# ──────────────────────────────────────────────
# spec.rayClusterSpec
# ──────────────────────────────────────────────


class TestJobCRDRayClusterSpec:
    """Verify rayClusterSpec is embedded with proper structure."""

    def test_ray_cluster_spec_present(self):
        job = _build_default_job()
        crd = job.to_crd_dict()
        assert "rayClusterSpec" in crd["spec"]
        assert isinstance(crd["spec"]["rayClusterSpec"], dict)

    def test_ray_cluster_spec_has_ray_version(self):
        job = _build_default_job(ray_version="2.41.0")
        crd = job.to_crd_dict()
        cluster_spec = crd["spec"]["rayClusterSpec"]
        assert cluster_spec["rayVersion"] == "2.41.0"

    def test_ray_cluster_spec_has_head_group(self):
        job = _build_default_job()
        crd = job.to_crd_dict()
        cluster_spec = crd["spec"]["rayClusterSpec"]
        assert "headGroupSpec" in cluster_spec

    def test_ray_cluster_spec_has_worker_groups(self):
        job = _build_default_job(workers=3)
        crd = job.to_crd_dict()
        cluster_spec = crd["spec"]["rayClusterSpec"]
        assert "workerGroupSpecs" in cluster_spec
        assert len(cluster_spec["workerGroupSpecs"]) >= 1
        assert cluster_spec["workerGroupSpecs"][0]["replicas"] == 3

    def test_ray_cluster_spec_head_container(self):
        job = _build_default_job()
        crd = job.to_crd_dict()
        container = _head_container(crd)
        assert container["name"] == "ray-head"

    def test_ray_cluster_spec_worker_container(self):
        job = _build_default_job()
        crd = job.to_crd_dict()
        container = _worker_container(crd)
        assert container["name"] == "ray-worker"

    def test_ray_cluster_spec_custom_resources(self):
        job = _build_default_job(
            cpus_per_worker=4.0,
            memory_per_worker="8Gi",
            gpus_per_worker=2,
        )
        crd = job.to_crd_dict()
        container = _worker_container(crd)
        assert container["resources"]["requests"]["cpu"] == "4"
        assert container["resources"]["requests"]["memory"] == "8Gi"
        assert container["resources"]["requests"]["nvidia.com/gpu"] == "2"

    def test_ray_cluster_spec_with_worker_groups(self):
        groups = [
            WorkerGroup(name="cpu-pool", replicas=4, cpus=4.0, memory="8Gi"),
            WorkerGroup(name="gpu-pool", replicas=2, gpus=1, memory="16Gi"),
        ]
        job = _build_default_job(worker_groups=groups)
        crd = job.to_crd_dict()
        cluster_spec = crd["spec"]["rayClusterSpec"]
        assert len(cluster_spec["workerGroupSpecs"]) == 2
        names = [g["groupName"] for g in cluster_spec["workerGroupSpecs"]]
        assert names == ["cpu-pool", "gpu-pool"]

    def test_ray_cluster_spec_with_head_config(self):
        head = HeadNodeConfig(cpus=4.0, memory="8Gi")
        job = _build_default_job(head=head)
        crd = job.to_crd_dict()
        container = _head_container(crd)
        assert container["resources"]["requests"]["cpu"] == "4"
        assert container["resources"]["requests"]["memory"] == "8Gi"


# ──────────────────────────────────────────────
# Kueue queue label
# ──────────────────────────────────────────────


class TestJobCRDKueueLabel:
    """Verify Kueue queue label is added when queue is set."""

    def test_kueue_label_present(self):
        job = _build_default_job(queue="my-queue")
        crd = job.to_crd_dict()
        assert crd["metadata"]["labels"]["kueue.x-k8s.io/queue-name"] == "my-queue"

    def test_kueue_label_absent_when_no_queue(self):
        job = _build_default_job()
        crd = job.to_crd_dict()
        assert "kueue.x-k8s.io/queue-name" not in crd["metadata"]["labels"]


# ──────────────────────────────────────────────
# Overall schema shape
# ──────────────────────────────────────────────


class TestJobCRDSchemaShape:
    """Verify the overall CRD dict has the expected top-level keys."""

    def test_top_level_keys(self):
        job = _build_default_job()
        crd = job.to_crd_dict()
        assert set(crd.keys()) >= {"apiVersion", "kind", "metadata", "spec"}

    def test_spec_contains_required_fields(self):
        job = _build_default_job()
        crd = job.to_crd_dict()
        spec = crd["spec"]
        assert "entrypoint" in spec
        assert "shutdownAfterJobFinishes" in spec
        assert "rayClusterSpec" in spec


# ──────────────────────────────────────────────
# JobStatus.from_cr
# ──────────────────────────────────────────────


class TestJobStatusFromCR:
    """Verify JobStatus.from_cr() correctly parses CRD status."""

    def test_from_cr_basic(self):
        cr = {
            "apiVersion": "ray.io/v1",
            "kind": "RayJob",
            "metadata": {
                "name": "test-job",
                "namespace": "default",
                "creationTimestamp": "2026-01-01T00:00:00Z",
            },
            "spec": {
                "entrypoint": "python train.py",
            },
            "status": {
                "jobStatus": "Running",
                "startTime": "2026-01-01T00:00:00Z",
            },
        }
        status = JobStatus.from_cr(cr)
        assert status.name == "test-job"
        assert status.namespace == "default"
        assert status.entrypoint == "python train.py"
        assert status.mode == JobMode.CRD

    def test_from_cr_state_mapping(self):
        cr = {
            "metadata": {
                "name": "test-job",
                "namespace": "default",
                "creationTimestamp": "2026-01-01T00:00:00Z",
            },
            "spec": {"entrypoint": "python train.py"},
            "status": {"jobStatus": "Succeeded"},
        }
        status = JobStatus.from_cr(cr)
        assert status.state == JobState.SUCCEEDED

    def test_from_cr_failed_has_error_message(self):
        cr = {
            "metadata": {
                "name": "test-job",
                "namespace": "default",
                "creationTimestamp": "2026-01-01T00:00:00Z",
            },
            "spec": {"entrypoint": "python train.py"},
            "status": {
                "jobStatus": "Failed",
                "message": "OOM killed",
            },
        }
        status = JobStatus.from_cr(cr)
        assert status.state == JobState.FAILED
        assert status.error_message == "OOM killed"

    def test_from_cr_frozen_model(self):
        cr = {
            "metadata": {
                "name": "test-job",
                "namespace": "default",
                "creationTimestamp": "2026-01-01T00:00:00Z",
            },
            "spec": {"entrypoint": "python train.py"},
            "status": {"jobStatus": "Running"},
        }
        status = JobStatus.from_cr(cr)
        with pytest.raises(Exception):
            status.name = "changed"  # type: ignore[misc]


# ──────────────────────────────────────────────
# raw_overrides
# ──────────────────────────────────────────────


class TestJobCRDRawOverrides:
    """Verify raw_overrides are deep-merged into the CRD."""

    def test_raw_overrides_applied(self):
        job = _build_default_job(
            raw_overrides={
                "spec": {
                    "ttlSecondsAfterFinished": 3600,
                }
            }
        )
        crd = job.to_crd_dict()
        assert crd["spec"]["ttlSecondsAfterFinished"] == 3600

    def test_raw_overrides_do_not_remove_required_fields(self):
        job = _build_default_job(
            raw_overrides={"metadata": {"labels": {"extra": "label"}}}
        )
        crd = job.to_crd_dict()
        assert crd["metadata"]["name"] == "test-job"
        assert crd["metadata"]["labels"]["extra"] == "label"
