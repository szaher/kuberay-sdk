"""Integration tests for full RayJob lifecycle (T080).

Tests the complete job lifecycle in both CRD mode and Dashboard submission mode:
- CRD mode:  create_job -> wait -> get_status (polling through states)
- Dashboard: submit_to_dashboard -> poll status -> verify payload

All Kubernetes API calls are mocked via ``mock_custom_objects_api`` from
conftest.py. DashboardClient is also mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from kuberay_sdk.config import SDKConfig
from kuberay_sdk.models.common import JobMode, JobState
from kuberay_sdk.models.job import JobStatus
from kuberay_sdk.models.runtime_env import ExperimentTracking, RuntimeEnv
from kuberay_sdk.services.job_service import JobService
from tests.conftest import make_dashboard_job_response, make_rayjob_cr

# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture()
def sdk_config() -> SDKConfig:
    """Default SDK config for integration tests."""
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
    """Mocked DashboardClient for Dashboard submission mode."""
    dc = MagicMock()
    dc.submit_job.return_value = "raysubmit_integ_001"
    dc.get_job_status.return_value = make_dashboard_job_response(
        job_id="raysubmit_integ_001",
        status="RUNNING",
    )
    dc.get_logs.return_value = "Epoch 1/10\nEpoch 2/10\nTraining complete."
    dc.stop_job.return_value = None
    return dc


# ──────────────────────────────────────────────
# T080: CRD mode lifecycle
# ──────────────────────────────────────────────


@pytest.mark.integration
class TestJobCRDLifecycle:
    """Full job lifecycle via CRD mode: create -> poll -> status."""

    def test_job_crd_lifecycle(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        """End-to-end CRD job lifecycle.

        Steps:
            1. Create a RayJob CR with an entrypoint and worker config
            2. Verify the CR was created with correct spec
            3. Poll status through PENDING -> RUNNING -> SUCCEEDED
            4. Verify the final JobStatus reports SUCCEEDED
        """
        job_name = "training-job"
        namespace = "ml-team"
        entrypoint = "python train.py --epochs 10"

        # ── Step 1: Create ──
        created_cr = make_rayjob_cr(
            name=job_name, namespace=namespace,
            entrypoint=entrypoint, state="Pending",
        )
        mock_custom_objects_api.create_namespaced_custom_object.return_value = created_cr

        result = job_service.create(
            name=job_name,
            namespace=namespace,
            entrypoint=entrypoint,
            workers=4,
            cpus_per_worker=2.0,
            gpus_per_worker=1,
            memory_per_worker="8Gi",
        )

        mock_custom_objects_api.create_namespaced_custom_object.assert_called_once()
        assert result["metadata"]["name"] == job_name

        # ── Step 2: Verify CRD body ──
        create_call = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = create_call[1].get("body") or create_call[0][-1]
        assert body["apiVersion"] == "ray.io/v1"
        assert body["kind"] == "RayJob"
        assert body["spec"]["entrypoint"] == entrypoint
        assert body["spec"]["shutdownAfterJobFinishes"] is True
        assert "rayClusterSpec" in body["spec"]
        cluster_spec = body["spec"]["rayClusterSpec"]
        assert cluster_spec["workerGroupSpecs"][0]["replicas"] == 4

        # ── Step 3: Poll status through state transitions ──
        pending_cr = make_rayjob_cr(name=job_name, namespace=namespace, state="Pending")
        running_cr = make_rayjob_cr(name=job_name, namespace=namespace, state="Running")
        succeeded_cr = make_rayjob_cr(name=job_name, namespace=namespace, state="Succeeded")

        mock_custom_objects_api.get_namespaced_custom_object.side_effect = [
            pending_cr,
            running_cr,
            running_cr,
            succeeded_cr,
        ]

        with patch("time.sleep"):
            final_status = job_service.wait(job_name, namespace, timeout=120)

        # ── Step 4: Verify final status ──
        assert isinstance(final_status, JobStatus)
        assert final_status.name == job_name
        assert final_status.state == JobState.SUCCEEDED
        assert final_status.mode == JobMode.CRD
        assert mock_custom_objects_api.get_namespaced_custom_object.call_count == 4

    def test_job_crd_with_runtime_env_and_tracking(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        """CRD job with runtime_env and experiment tracking merged into spec."""
        job_name = "tracked-job"
        namespace = "default"

        runtime_env = RuntimeEnv(
            pip=["torch", "transformers"],
            env_vars={"CUSTOM_VAR": "value"},
        )
        experiment_tracking = ExperimentTracking(
            provider="mlflow",
            tracking_uri="http://mlflow:5000",
            experiment_name="my-experiment",
        )

        created_cr = make_rayjob_cr(name=job_name, namespace=namespace, state="Running")
        mock_custom_objects_api.create_namespaced_custom_object.return_value = created_cr

        job_service.create(
            name=job_name,
            namespace=namespace,
            entrypoint="python train.py",
            runtime_env=runtime_env,
            experiment_tracking=experiment_tracking,
        )

        create_call = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = create_call[1].get("body") or create_call[0][-1]

        # The spec should contain a runtimeEnvYAML with merged env vars
        assert "runtimeEnvYAML" in body["spec"]
        runtime_yaml = body["spec"]["runtimeEnvYAML"]
        assert "MLFLOW_TRACKING_URI" in runtime_yaml
        assert "mlflow:5000" in runtime_yaml

    def test_job_crd_with_queue_label(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        """CRD job with Kueue queue should include the queue label in metadata."""
        job_name = "queued-job"
        namespace = "default"

        created_cr = make_rayjob_cr(name=job_name, namespace=namespace, state="Pending")
        mock_custom_objects_api.create_namespaced_custom_object.return_value = created_cr

        job_service.create(
            name=job_name,
            namespace=namespace,
            entrypoint="python train.py",
            queue="gpu-queue",
        )

        create_call = mock_custom_objects_api.create_namespaced_custom_object.call_args
        body = create_call[1].get("body") or create_call[0][-1]
        assert body["metadata"]["labels"]["kueue.x-k8s.io/queue-name"] == "gpu-queue"

    def test_job_crd_failed_lifecycle(
        self,
        job_service: JobService,
        mock_custom_objects_api: MagicMock,
    ):
        """Job that transitions to FAILED should return status without raising."""
        job_name = "failing-job"
        namespace = "default"

        created_cr = make_rayjob_cr(name=job_name, namespace=namespace, state="Pending")
        mock_custom_objects_api.create_namespaced_custom_object.return_value = created_cr

        job_service.create(
            name=job_name,
            namespace=namespace,
            entrypoint="python broken.py",
        )

        # Transitions: Pending -> Running -> Failed
        pending_cr = make_rayjob_cr(name=job_name, namespace=namespace, state="Pending")
        running_cr = make_rayjob_cr(name=job_name, namespace=namespace, state="Running")
        failed_cr = make_rayjob_cr(name=job_name, namespace=namespace, state="Failed")

        mock_custom_objects_api.get_namespaced_custom_object.side_effect = [
            pending_cr,
            running_cr,
            failed_cr,
        ]

        with patch("time.sleep"):
            final_status = job_service.wait(job_name, namespace, timeout=120)

        assert final_status.state == JobState.FAILED


# ──────────────────────────────────────────────
# T080: Dashboard submission lifecycle
# ──────────────────────────────────────────────


@pytest.mark.integration
class TestJobDashboardLifecycle:
    """Job lifecycle via Dashboard submission mode."""

    def test_job_submission_via_dashboard(
        self,
        job_service: JobService,
        mock_dashboard_client: MagicMock,
    ):
        """Submit a job via DashboardClient and verify the submission payload.

        Steps:
            1. Submit a job with entrypoint and runtime_env
            2. Verify submit_job was called with correct payload
            3. Poll status until SUCCEEDED
            4. Verify final status
        """
        entrypoint = "python train.py --lr 0.001"
        runtime_env = {"pip": ["torch", "numpy"], "env_vars": {"CUDA_VISIBLE_DEVICES": "0"}}

        # ── Step 1: Submit ──
        job_id = job_service.submit_to_dashboard(
            dashboard_client=mock_dashboard_client,
            entrypoint=entrypoint,
            runtime_env=runtime_env,
            metadata={"user": "integration-test", "project": "llm-finetune"},
        )

        assert job_id == "raysubmit_integ_001"

        # ── Step 2: Verify submission payload ──
        mock_dashboard_client.submit_job.assert_called_once()
        submit_call = mock_dashboard_client.submit_job.call_args
        submit_kwargs = submit_call[1]

        assert submit_kwargs["entrypoint"] == entrypoint
        assert submit_kwargs["runtime_env"] == runtime_env
        assert submit_kwargs["metadata"]["user"] == "integration-test"
        assert submit_kwargs["metadata"]["project"] == "llm-finetune"

        # ── Step 3: Poll until SUCCEEDED ──
        mock_dashboard_client.get_job_status.side_effect = [
            make_dashboard_job_response(job_id="raysubmit_integ_001", status="RUNNING"),
            make_dashboard_job_response(job_id="raysubmit_integ_001", status="RUNNING"),
            make_dashboard_job_response(job_id="raysubmit_integ_001", status="SUCCEEDED"),
        ]

        with patch("time.sleep"):
            final_result = job_service.wait_dashboard_job(
                dashboard_client=mock_dashboard_client,
                job_id=job_id,
                timeout=120,
            )

        # ── Step 4: Verify final status ──
        assert final_result["status"] == "SUCCEEDED"
        assert final_result["job_id"] == "raysubmit_integ_001"
        assert mock_dashboard_client.get_job_status.call_count == 3

    def test_job_submission_with_experiment_tracking(
        self,
        job_service: JobService,
        mock_dashboard_client: MagicMock,
    ):
        """Dashboard submission with experiment tracking merges env vars into runtime_env."""
        entrypoint = "python train.py"
        runtime_env = {"pip": ["torch"]}
        experiment_tracking = ExperimentTracking(
            provider="mlflow",
            tracking_uri="http://mlflow.svc:5000",
            experiment_name="integration-test",
        )

        job_service.submit_to_dashboard(
            dashboard_client=mock_dashboard_client,
            entrypoint=entrypoint,
            runtime_env=runtime_env,
            experiment_tracking=experiment_tracking,
        )

        submit_call = mock_dashboard_client.submit_job.call_args
        submit_kwargs = submit_call[1]

        # Runtime env should have the original pip deps plus tracking env vars
        rt = submit_kwargs["runtime_env"]
        assert "pip" in rt
        assert rt["env_vars"]["MLFLOW_TRACKING_URI"] == "http://mlflow.svc:5000"
        assert rt["env_vars"]["MLFLOW_EXPERIMENT_NAME"] == "integration-test"

    def test_job_submission_without_runtime_env(
        self,
        job_service: JobService,
        mock_dashboard_client: MagicMock,
    ):
        """Dashboard submission with no runtime_env should pass None."""
        job_service.submit_to_dashboard(
            dashboard_client=mock_dashboard_client,
            entrypoint="echo hello",
        )

        submit_call = mock_dashboard_client.submit_job.call_args
        submit_kwargs = submit_call[1]

        assert submit_kwargs["entrypoint"] == "echo hello"
        assert submit_kwargs.get("runtime_env") is None
        assert submit_kwargs.get("metadata") is None
