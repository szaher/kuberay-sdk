"""Unit tests for JobService (T028).

Tests verify that JobService correctly:
- Generates CRD dicts and calls CustomObjectsApi for CRD mode create
- Submits jobs via DashboardClient for Dashboard mode
- Lists RayJob CRs
- Gets job status from both CRD and Dashboard
- Stops jobs
- Waits for completion (polling)

All Kubernetes API calls are mocked via ``mock_custom_objects_api`` from
conftest.py. DashboardClient is also mocked.

TDD: these tests are written BEFORE ``kuberay_sdk.services.job_service``
is implemented.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from kuberay_sdk.config import SDKConfig
from kuberay_sdk.errors import (
    JobNotFoundError,
    TimeoutError,
)
from kuberay_sdk.models.common import JobMode
from kuberay_sdk.models.job import JobStatus
from kuberay_sdk.models.runtime_env import ExperimentTracking, RuntimeEnv
from kuberay_sdk.services.job_service import JobService
from tests.conftest import make_dashboard_job_response, make_rayjob_cr

# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture()
def sdk_config() -> SDKConfig:
    """Default SDK config for tests."""
    return SDKConfig(namespace="default")


@pytest.fixture()
def job_service(
    mock_custom_objects_api: MagicMock,
    sdk_config: SDKConfig,
) -> JobService:
    """JobService with mocked CustomObjectsApi."""
    return JobService(mock_custom_objects_api, sdk_config)


@pytest.fixture()
def mock_dashboard_client() -> MagicMock:
    """Mocked DashboardClient."""
    dc = MagicMock()
    dc.submit_job.return_value = "raysubmit_test123"
    dc.get_job_status.return_value = make_dashboard_job_response(
        job_id="raysubmit_test123",
        status="RUNNING",
    )
    dc.list_jobs.return_value = [
        make_dashboard_job_response(job_id="job-1", status="RUNNING"),
        make_dashboard_job_response(job_id="job-2", status="SUCCEEDED"),
    ]
    dc.stop_job.return_value = None
    return dc


# ──────────────────────────────────────────────
# CRD mode: create
# ──────────────────────────────────────────────


class TestJobServiceCRDCreate:
    """Test create() builds a RayJob CRD and calls CustomObjectsApi."""

    def test_create_calls_k8s_api(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        job_service.create(
            name="test-job",
            namespace="default",
            entrypoint="python train.py",
            workers=2,
        )
        mock_custom_objects_api.create_namespaced_custom_object.assert_called_once()

    def test_create_passes_correct_group_version_plural(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        job_service.create(
            name="test-job",
            namespace="default",
            entrypoint="python train.py",
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        kwargs = call_kwargs[1] if call_kwargs[1] else {}
        assert kwargs.get("group") == "ray.io"
        assert kwargs.get("version") == "v1"
        assert kwargs.get("plural") == "rayjobs"

    def test_create_body_is_rayjob_crd(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        job_service.create(
            name="my-job",
            namespace="ml-team",
            entrypoint="python train.py --epochs 10",
            workers=4,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body")
        assert body["apiVersion"] == "ray.io/v1"
        assert body["kind"] == "RayJob"
        assert body["metadata"]["name"] == "my-job"
        assert body["metadata"]["namespace"] == "ml-team"
        assert body["spec"]["entrypoint"] == "python train.py --epochs 10"

    def test_create_body_has_ray_cluster_spec(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        job_service.create(
            name="test-job",
            namespace="default",
            entrypoint="python train.py",
            workers=2,
            cpus_per_worker=2.0,
            gpus_per_worker=1,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body")
        cluster_spec = body["spec"]["rayClusterSpec"]
        assert "headGroupSpec" in cluster_spec
        assert "workerGroupSpecs" in cluster_spec
        assert cluster_spec["workerGroupSpecs"][0]["replicas"] == 2

    def test_create_with_runtime_env(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        runtime_env = RuntimeEnv(pip=["torch"])
        job_service.create(
            name="test-job",
            namespace="default",
            entrypoint="python train.py",
            runtime_env=runtime_env,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body")
        assert "runtimeEnvYAML" in body["spec"]

    def test_create_with_experiment_tracking(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        et = ExperimentTracking(
            provider="mlflow",
            tracking_uri="http://mlflow:5000",
        )
        job_service.create(
            name="test-job",
            namespace="default",
            entrypoint="python train.py",
            experiment_tracking=et,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body")
        # Experiment tracking should result in runtimeEnvYAML with env vars
        assert "runtimeEnvYAML" in body["spec"]

    def test_create_with_shutdown_after_finish(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        job_service.create(
            name="test-job",
            namespace="default",
            entrypoint="python train.py",
            shutdown_after_finish=True,
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body")
        assert body["spec"]["shutdownAfterJobFinishes"] is True

    def test_create_with_labels_and_annotations(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        job_service.create(
            name="labeled-job",
            namespace="default",
            entrypoint="python train.py",
            labels={"team": "ml"},
            annotations={"description": "test"},
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body")
        assert body["metadata"]["labels"]["team"] == "ml"
        assert body["metadata"]["annotations"]["description"] == "test"

    def test_create_with_queue(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        job_service.create(
            name="queued-job",
            namespace="default",
            entrypoint="python train.py",
            queue="my-queue",
        )
        call_kwargs = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = call_kwargs[1].get("body")
        assert body["metadata"]["labels"]["kueue.x-k8s.io/queue-name"] == "my-queue"


# ──────────────────────────────────────────────
# Dashboard mode: submit
# ──────────────────────────────────────────────


class TestJobServiceDashboardSubmit:
    """Test submit_to_dashboard() calls DashboardClient.submit_job()."""

    def test_submit_calls_dashboard(
        self,
        job_service: JobService,
        mock_dashboard_client: MagicMock,
    ):
        job_id = job_service.submit_to_dashboard(
            mock_dashboard_client,
            entrypoint="python train.py",
        )
        mock_dashboard_client.submit_job.assert_called_once()
        assert job_id == "raysubmit_test123"

    def test_submit_passes_entrypoint(
        self,
        job_service: JobService,
        mock_dashboard_client: MagicMock,
    ):
        job_service.submit_to_dashboard(
            mock_dashboard_client,
            entrypoint="python train.py --lr 0.01",
        )
        call_kwargs = mock_dashboard_client.submit_job.call_args
        kwargs = call_kwargs[1] if call_kwargs[1] else {}
        assert kwargs.get("entrypoint") == "python train.py --lr 0.01"

    def test_submit_passes_runtime_env(
        self,
        job_service: JobService,
        mock_dashboard_client: MagicMock,
    ):
        runtime_env = {"pip": ["torch"]}
        job_service.submit_to_dashboard(
            mock_dashboard_client,
            entrypoint="python train.py",
            runtime_env=runtime_env,
        )
        call_kwargs = mock_dashboard_client.submit_job.call_args
        kwargs = call_kwargs[1] if call_kwargs[1] else {}
        assert "runtime_env" in kwargs
        assert isinstance(kwargs["runtime_env"], dict)

    def test_submit_passes_metadata(
        self,
        job_service: JobService,
        mock_dashboard_client: MagicMock,
    ):
        metadata = {"user": "tester"}
        job_service.submit_to_dashboard(
            mock_dashboard_client,
            entrypoint="python train.py",
            metadata=metadata,
        )
        call_kwargs = mock_dashboard_client.submit_job.call_args
        kwargs = call_kwargs[1] if call_kwargs[1] else {}
        assert kwargs.get("metadata") == {"user": "tester"}

    def test_submit_with_experiment_tracking_merges_env_vars(
        self,
        job_service: JobService,
        mock_dashboard_client: MagicMock,
    ):
        runtime_env = {"pip": ["torch"]}
        et = ExperimentTracking(
            provider="mlflow",
            tracking_uri="http://mlflow:5000",
        )
        job_service.submit_to_dashboard(
            mock_dashboard_client,
            entrypoint="python train.py",
            runtime_env=runtime_env,
            experiment_tracking=et,
        )
        call_kwargs = mock_dashboard_client.submit_job.call_args
        kwargs = call_kwargs[1] if call_kwargs[1] else {}
        rt = kwargs.get("runtime_env", {})
        assert rt.get("env_vars", {}).get("MLFLOW_TRACKING_URI") == "http://mlflow:5000"

    def test_submit_with_runtime_env_model(
        self,
        job_service: JobService,
        mock_dashboard_client: MagicMock,
    ):
        """RuntimeEnv model objects should be converted to dicts."""
        runtime_env = RuntimeEnv(pip=["torch"], env_vars={"KEY": "val"})
        job_service.submit_to_dashboard(
            mock_dashboard_client,
            entrypoint="python train.py",
            runtime_env=runtime_env,
        )
        call_kwargs = mock_dashboard_client.submit_job.call_args
        kwargs = call_kwargs[1] if call_kwargs[1] else {}
        rt = kwargs.get("runtime_env", {})
        assert isinstance(rt, dict)
        assert "pip" in rt


# ──────────────────────────────────────────────
# list_jobs (CRD)
# ──────────────────────────────────────────────


class TestJobServiceList:
    """Test list() returns JobStatus objects from CRD."""

    def test_list_empty(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.list_namespaced_custom_object.return_value = {"items": []}
        result = job_service.list("default")
        assert result == []

    def test_list_returns_job_statuses(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.list_namespaced_custom_object.return_value = {
            "items": [
                make_rayjob_cr(name="job-1", state="Running"),
                make_rayjob_cr(name="job-2", state="Succeeded"),
            ]
        }
        result = job_service.list("default")
        assert len(result) == 2
        assert all(isinstance(s, JobStatus) for s in result)

    def test_list_status_names(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.list_namespaced_custom_object.return_value = {
            "items": [
                make_rayjob_cr(name="alpha"),
                make_rayjob_cr(name="bravo"),
            ]
        }
        result = job_service.list("default")
        names = [s.name for s in result]
        assert names == ["alpha", "bravo"]

    def test_list_calls_correct_api(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        job_service.list("my-namespace")
        mock_custom_objects_api.list_namespaced_custom_object.assert_called_once()
        call_kwargs = mock_custom_objects_api.list_namespaced_custom_object.call_args
        kwargs = call_kwargs[1] if call_kwargs[1] else {}
        assert kwargs.get("group") == "ray.io"
        assert kwargs.get("plural") == "rayjobs"
        assert kwargs.get("namespace") == "my-namespace"


# ──────────────────────────────────────────────
# get_status
# ──────────────────────────────────────────────


class TestJobServiceGetStatus:
    """Test get_status returns a JobStatus object from CRD."""

    def test_get_status_returns_job_status(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = make_rayjob_cr(
            name="my-job", state="Running"
        )
        status = job_service.get_status("my-job", "default")
        assert isinstance(status, JobStatus)
        assert status.name == "my-job"
        assert status.mode == JobMode.CRD

    def test_get_status_not_found(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        api_exception = type("ApiException", (Exception,), {"status": 404, "reason": "Not Found"})()
        mock_custom_objects_api.get_namespaced_custom_object.side_effect = api_exception
        with pytest.raises(JobNotFoundError):
            job_service.get_status("nonexistent", "default")

    def test_get_dashboard_job_status(
        self,
        job_service: JobService,
        mock_dashboard_client: MagicMock,
    ):
        """get_dashboard_job_status should call DashboardClient."""
        result = job_service.get_dashboard_job_status(mock_dashboard_client, "raysubmit_test123")
        mock_dashboard_client.get_job_status.assert_called_once_with("raysubmit_test123")
        assert result is not None


# ──────────────────────────────────────────────
# stop
# ──────────────────────────────────────────────


class TestJobServiceStop:
    """Test stop() deletes the RayJob CR."""

    def test_stop_calls_delete_api(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        job_service.stop("test-job", "default")
        mock_custom_objects_api.delete_namespaced_custom_object.assert_called_once()

    def test_stop_passes_correct_name(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        job_service.stop("my-job", "ml-team")
        call_kwargs = mock_custom_objects_api.delete_namespaced_custom_object.call_args
        kwargs = call_kwargs[1] if call_kwargs[1] else {}
        assert kwargs.get("name") == "my-job"
        assert kwargs.get("namespace") == "ml-team"
        assert kwargs.get("group") == "ray.io"
        assert kwargs.get("plural") == "rayjobs"

    def test_stop_nonexistent_job_raises(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        api_exception = type("ApiException", (Exception,), {"status": 404, "reason": "Not Found"})()
        mock_custom_objects_api.delete_namespaced_custom_object.side_effect = api_exception
        with pytest.raises(JobNotFoundError):
            job_service.stop("nonexistent", "default")


# ──────────────────────────────────────────────
# wait (CRD mode)
# ──────────────────────────────────────────────


class TestJobServiceWait:
    """Test wait() polls until job completes."""

    def test_already_succeeded(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        mock_custom_objects_api.get_namespaced_custom_object.return_value = make_rayjob_cr(state="Succeeded")
        status = job_service.wait("test-job", "default", timeout=5)
        assert isinstance(status, JobStatus)

    def test_polls_until_complete(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        running = make_rayjob_cr(state="Running")
        succeeded = make_rayjob_cr(state="Succeeded")

        mock_custom_objects_api.get_namespaced_custom_object.side_effect = [
            running,
            running,
            succeeded,
        ]
        with patch("time.sleep"):
            job_service.wait("test-job", "default", timeout=60)
        assert mock_custom_objects_api.get_namespaced_custom_object.call_count == 3

    def test_timeout_raises(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        running = make_rayjob_cr(state="Running")
        mock_custom_objects_api.get_namespaced_custom_object.return_value = running

        with patch("time.sleep"), pytest.raises(TimeoutError):
            job_service.wait("test-job", "default", timeout=0.01)

    def test_failed_job_returns_status(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        """Failed job should return the final status, not raise."""
        failed = make_rayjob_cr(state="Failed")
        mock_custom_objects_api.get_namespaced_custom_object.return_value = failed
        status = job_service.wait("test-job", "default", timeout=5)
        assert isinstance(status, JobStatus)


# ──────────────────────────────────────────────
# wait_dashboard_job (Dashboard mode)
# ──────────────────────────────────────────────


class TestJobServiceWaitDashboard:
    """Test wait_dashboard_job() polls the Dashboard until complete."""

    def test_already_succeeded(
        self,
        job_service: JobService,
        mock_dashboard_client: MagicMock,
    ):
        mock_dashboard_client.get_job_status.return_value = make_dashboard_job_response(status="SUCCEEDED")
        result = job_service.wait_dashboard_job(mock_dashboard_client, "raysubmit_test123", timeout=5)
        assert result is not None

    def test_polls_until_complete(
        self,
        job_service: JobService,
        mock_dashboard_client: MagicMock,
    ):
        mock_dashboard_client.get_job_status.side_effect = [
            make_dashboard_job_response(status="RUNNING"),
            make_dashboard_job_response(status="RUNNING"),
            make_dashboard_job_response(status="SUCCEEDED"),
        ]
        with patch("time.sleep"):
            job_service.wait_dashboard_job(mock_dashboard_client, "raysubmit_test123", timeout=60)
        assert mock_dashboard_client.get_job_status.call_count == 3

    def test_timeout_raises(
        self,
        job_service: JobService,
        mock_dashboard_client: MagicMock,
    ):
        mock_dashboard_client.get_job_status.return_value = make_dashboard_job_response(status="RUNNING")
        with patch("time.sleep"), pytest.raises(TimeoutError):
            job_service.wait_dashboard_job(mock_dashboard_client, "raysubmit_test123", timeout=0.01)

    def test_failed_job_returns_status(
        self,
        job_service: JobService,
        mock_dashboard_client: MagicMock,
    ):
        mock_dashboard_client.get_job_status.return_value = make_dashboard_job_response(status="FAILED")
        result = job_service.wait_dashboard_job(mock_dashboard_client, "raysubmit_test123", timeout=5)
        assert result is not None
