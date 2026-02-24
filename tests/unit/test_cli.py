"""CLI tests (T039).

Tests the ``kuberay`` CLI using Click's CliRunner with mocked KubeRayClient.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kuberay_sdk.cli.main import cli
from kuberay_sdk.errors import ClusterNotFoundError, KubeRayError
from kuberay_sdk.models.capabilities import ClusterCapabilities
from kuberay_sdk.models.cluster import ClusterStatus
from kuberay_sdk.models.common import JobMode, JobState
from kuberay_sdk.models.job import JobStatus
from kuberay_sdk.models.service import ServiceStatus


def _make_cluster_status(
    name: str = "test-cluster",
    namespace: str = "default",
    state: str = "RUNNING",
    workers_ready: int = 2,
) -> ClusterStatus:
    """Create a mock ClusterStatus for testing."""
    return ClusterStatus(
        name=name,
        namespace=namespace,
        state=state,
        head_ready=True,
        workers_ready=workers_ready,
        workers_desired=workers_ready,
        ray_version="2.41.0",
        age=timedelta(hours=2),
    )


def _make_job_status(
    name: str = "test-job",
    namespace: str = "default",
    state: JobState = JobState.RUNNING,
    entrypoint: str = "python train.py",
) -> JobStatus:
    """Create a mock JobStatus for testing."""
    return JobStatus(
        name=name,
        namespace=namespace,
        state=state,
        mode=JobMode.CRD,
        entrypoint=entrypoint,
        submitted_at=datetime.now(timezone.utc) - timedelta(minutes=30),
    )


def _make_service_status(
    name: str = "test-service",
    namespace: str = "default",
    state: str = "RUNNING",
    replicas_ready: int = 1,
) -> ServiceStatus:
    """Create a mock ServiceStatus for testing."""
    return ServiceStatus(
        name=name,
        namespace=namespace,
        state=state,
        replicas_ready=replicas_ready,
        replicas_desired=replicas_ready,
        age=timedelta(hours=1),
    )


# ──────────────────────────────────────────────
# Help and version
# ──────────────────────────────────────────────


class TestHelpAndVersion:
    """Test --help and --version options."""

    def test_help_shows_subcommands(self) -> None:
        """``kuberay --help`` should show cluster, job, service subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "cluster" in result.output
        assert "job" in result.output
        assert "service" in result.output
        assert "capabilities" in result.output

    def test_version(self) -> None:
        """``kuberay --version`` should show SDK version."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        # Should contain version string (e.g., "0.1.0")
        assert "version" in result.output.lower() or "0." in result.output


# ──────────────────────────────────────────────
# Cluster commands
# ──────────────────────────────────────────────


class TestClusterList:
    """Test ``kuberay cluster list``."""

    @patch("kuberay_sdk.cli.cluster._get_client")
    def test_list_table_output(self, mock_get_client: MagicMock) -> None:
        """``kuberay cluster list`` should return table output by default."""
        mock_client = MagicMock()
        mock_client.list_clusters.return_value = [
            _make_cluster_status("cluster-a", workers_ready=2),
            _make_cluster_status("cluster-b", state="CREATING", workers_ready=0),
        ]
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["cluster", "list"])
        assert result.exit_code == 0
        assert "NAME" in result.output
        assert "STATE" in result.output
        assert "WORKERS" in result.output
        assert "cluster-a" in result.output
        assert "cluster-b" in result.output
        assert "RUNNING" in result.output
        assert "CREATING" in result.output

    @patch("kuberay_sdk.cli.cluster._get_client")
    def test_list_json_output(self, mock_get_client: MagicMock) -> None:
        """``kuberay cluster list --output json`` should return valid JSON."""
        mock_client = MagicMock()
        mock_client.list_clusters.return_value = [
            _make_cluster_status("cluster-a", workers_ready=2),
        ]
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["cluster", "list", "--output", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "cluster-a"
        assert data[0]["workers"] == 2

    @patch("kuberay_sdk.cli.cluster._get_client")
    def test_list_json_via_global_option(self, mock_get_client: MagicMock) -> None:
        """``kuberay -o json cluster list`` should return JSON output."""
        mock_client = MagicMock()
        mock_client.list_clusters.return_value = [
            _make_cluster_status("cluster-a"),
        ]
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["-o", "json", "cluster", "list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)

    @patch("kuberay_sdk.cli.cluster._get_client")
    def test_list_empty(self, mock_get_client: MagicMock) -> None:
        """``kuberay cluster list`` with no clusters shows headers only."""
        mock_client = MagicMock()
        mock_client.list_clusters.return_value = []
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["cluster", "list"])
        assert result.exit_code == 0
        assert "NAME" in result.output


class TestClusterCreate:
    """Test ``kuberay cluster create``."""

    @patch("kuberay_sdk.cli.cluster._get_client")
    def test_create_basic(self, mock_get_client: MagicMock) -> None:
        """``kuberay cluster create my-cluster`` should create a cluster."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["cluster", "create", "my-cluster"])
        assert result.exit_code == 0
        assert "created" in result.output
        mock_client.create_cluster.assert_called_once()

    @patch("kuberay_sdk.cli.cluster._get_client")
    def test_create_with_workers(self, mock_get_client: MagicMock) -> None:
        """``kuberay cluster create my-cluster --workers 4``."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["cluster", "create", "my-cluster", "--workers", "4"])
        assert result.exit_code == 0
        call_kwargs = mock_client.create_cluster.call_args
        assert call_kwargs[1]["workers"] == 4


class TestClusterGet:
    """Test ``kuberay cluster get``."""

    @patch("kuberay_sdk.cli.cluster._get_client")
    def test_get_table(self, mock_get_client: MagicMock) -> None:
        """``kuberay cluster get my-cluster`` should show cluster status."""
        mock_client = MagicMock()
        mock_handle = MagicMock()
        mock_handle.status.return_value = _make_cluster_status("my-cluster")
        mock_client.get_cluster.return_value = mock_handle
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["cluster", "get", "my-cluster"])
        assert result.exit_code == 0
        assert "my-cluster" in result.output
        assert "RUNNING" in result.output


class TestClusterDelete:
    """Test ``kuberay cluster delete``."""

    @patch("kuberay_sdk.cli.cluster._get_client")
    def test_delete(self, mock_get_client: MagicMock) -> None:
        """``kuberay cluster delete my-cluster`` should delete the cluster."""
        mock_client = MagicMock()
        mock_handle = MagicMock()
        mock_client.get_cluster.return_value = mock_handle
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["cluster", "delete", "my-cluster"])
        assert result.exit_code == 0
        assert "deleted" in result.output
        mock_handle.delete.assert_called_once_with(force=False)

    @patch("kuberay_sdk.cli.cluster._get_client")
    def test_delete_force(self, mock_get_client: MagicMock) -> None:
        """``kuberay cluster delete my-cluster --force`` should force delete."""
        mock_client = MagicMock()
        mock_handle = MagicMock()
        mock_client.get_cluster.return_value = mock_handle
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["cluster", "delete", "my-cluster", "--force"])
        assert result.exit_code == 0
        mock_handle.delete.assert_called_once_with(force=True)


class TestClusterScale:
    """Test ``kuberay cluster scale``."""

    @patch("kuberay_sdk.cli.cluster._get_client")
    def test_scale(self, mock_get_client: MagicMock) -> None:
        """``kuberay cluster scale my-cluster --workers 8``."""
        mock_client = MagicMock()
        mock_handle = MagicMock()
        mock_client.get_cluster.return_value = mock_handle
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["cluster", "scale", "my-cluster", "--workers", "8"])
        assert result.exit_code == 0
        assert "scaled" in result.output
        mock_handle.scale.assert_called_once_with(8)


# ──────────────────────────────────────────────
# Error handling
# ──────────────────────────────────────────────


class TestErrorHandling:
    """Test error output with remediation hints."""

    @patch("kuberay_sdk.cli.cluster._get_client")
    def test_error_with_remediation(self, mock_get_client: MagicMock) -> None:
        """Errors should include remediation hint on stderr."""
        mock_client = MagicMock()
        mock_client.list_clusters.side_effect = ClusterNotFoundError("x", "default")
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["cluster", "list"])
        assert result.exit_code == 1
        stderr_output = result.stderr if hasattr(result, "stderr") else result.output
        assert "Error:" in stderr_output
        assert "To fix:" in stderr_output

    @patch("kuberay_sdk.cli.cluster._get_client")
    def test_error_without_remediation(self, mock_get_client: MagicMock) -> None:
        """Errors without remediation should only print the error message."""
        mock_client = MagicMock()
        mock_client.list_clusters.side_effect = KubeRayError("Something broke")
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["cluster", "list"])
        assert result.exit_code == 1
        stderr_output = result.stderr if hasattr(result, "stderr") else result.output
        assert "Error:" in stderr_output
        assert "To fix:" not in stderr_output


# ──────────────────────────────────────────────
# Job commands
# ──────────────────────────────────────────────


class TestJobCommands:
    """Test ``kuberay job`` subcommands."""

    @patch("kuberay_sdk.cli.job._get_client")
    def test_job_create(self, mock_get_client: MagicMock) -> None:
        """``kuberay job create my-job --entrypoint 'python train.py'``."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["job", "create", "my-job", "--entrypoint", "python train.py"])
        assert result.exit_code == 0
        assert "created" in result.output

    @patch("kuberay_sdk.cli.job._get_client")
    def test_job_list_table(self, mock_get_client: MagicMock) -> None:
        """``kuberay job list`` should return table output."""
        mock_client = MagicMock()
        mock_client.list_jobs.return_value = [
            _make_job_status("training-1"),
        ]
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["job", "list"])
        assert result.exit_code == 0
        assert "training-1" in result.output
        assert "RUNNING" in result.output

    @patch("kuberay_sdk.cli.job._get_client")
    def test_job_list_json(self, mock_get_client: MagicMock) -> None:
        """``kuberay job list --output json``."""
        mock_client = MagicMock()
        mock_client.list_jobs.return_value = [
            _make_job_status("training-1"),
        ]
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["job", "list", "--output", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["name"] == "training-1"

    @patch("kuberay_sdk.cli.job._get_client")
    def test_job_get(self, mock_get_client: MagicMock) -> None:
        """``kuberay job get my-job``."""
        mock_client = MagicMock()
        mock_handle = MagicMock()
        mock_handle.status.return_value = _make_job_status("my-job")
        mock_client.get_job.return_value = mock_handle
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["job", "get", "my-job"])
        assert result.exit_code == 0
        assert "my-job" in result.output


# ──────────────────────────────────────────────
# Service commands
# ──────────────────────────────────────────────


class TestServiceCommands:
    """Test ``kuberay service`` subcommands."""

    @patch("kuberay_sdk.cli.service._get_client")
    def test_service_create(self, mock_get_client: MagicMock) -> None:
        """``kuberay service create my-svc --import-path serve:app``."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["service", "create", "my-svc", "--import-path", "serve:app"])
        assert result.exit_code == 0
        assert "created" in result.output

    @patch("kuberay_sdk.cli.service._get_client")
    def test_service_list_table(self, mock_get_client: MagicMock) -> None:
        """``kuberay service list`` should return table output."""
        mock_client = MagicMock()
        mock_client.list_services.return_value = [
            _make_service_status("my-llm"),
        ]
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["service", "list"])
        assert result.exit_code == 0
        assert "my-llm" in result.output
        assert "RUNNING" in result.output

    @patch("kuberay_sdk.cli.service._get_client")
    def test_service_get(self, mock_get_client: MagicMock) -> None:
        """``kuberay service get my-llm``."""
        mock_client = MagicMock()
        mock_handle = MagicMock()
        mock_handle.status.return_value = _make_service_status("my-llm")
        mock_client.get_service.return_value = mock_handle
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["service", "get", "my-llm"])
        assert result.exit_code == 0
        assert "my-llm" in result.output

    @patch("kuberay_sdk.cli.service._get_client")
    def test_service_delete(self, mock_get_client: MagicMock) -> None:
        """``kuberay service delete my-llm``."""
        mock_client = MagicMock()
        mock_handle = MagicMock()
        mock_client.get_service.return_value = mock_handle
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["service", "delete", "my-llm"])
        assert result.exit_code == 0
        assert "deleted" in result.output
        mock_handle.delete.assert_called_once()


# ──────────────────────────────────────────────
# Capabilities command
# ──────────────────────────────────────────────


class TestCapabilities:
    """Test ``kuberay capabilities``."""

    @patch("kuberay_sdk.cli.main._get_client")
    def test_capabilities_table(self, mock_get_client: MagicMock) -> None:
        """``kuberay capabilities`` should show table of capabilities."""
        mock_client = MagicMock()
        mock_client.get_capabilities.return_value = ClusterCapabilities(
            kuberay_installed=True,
            kuberay_version="v1.2.0",
            gpu_available=True,
            gpu_types=["nvidia.com/gpu"],
            kueue_available=False,
            openshift=False,
        )
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["capabilities"])
        assert result.exit_code == 0
        assert "CAPABILITY" in result.output
        assert "KubeRay" in result.output
        assert "v1.2.0" in result.output
        assert "nvidia.com/gpu" in result.output
        assert "not installed" in result.output
        assert "not detected" in result.output

    @patch("kuberay_sdk.cli.main._get_client")
    def test_capabilities_json(self, mock_get_client: MagicMock) -> None:
        """``kuberay capabilities --output json``."""
        mock_client = MagicMock()
        mock_client.get_capabilities.return_value = ClusterCapabilities(
            kuberay_installed=True,
            kuberay_version="v1.2.0",
            gpu_available=False,
            gpu_types=[],
            kueue_available=True,
            openshift=True,
        )
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["capabilities", "--output", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["kuberay"] == "v1.2.0"
        assert data["kueue"] == "available"
        assert data["openshift"] == "detected"


# ──────────────────────────────────────────────
# Formatter tests
# ──────────────────────────────────────────────


class TestFormatters:
    """Test output formatters."""

    def test_format_table_basic(self) -> None:
        from kuberay_sdk.cli.formatters import format_table

        result = format_table(["NAME", "STATE"], [["foo", "RUNNING"], ["bar", "CREATING"]])
        lines = result.strip().split("\n")
        assert len(lines) == 3
        assert "NAME" in lines[0]
        assert "STATE" in lines[0]
        assert "foo" in lines[1]
        assert "bar" in lines[2]

    def test_format_table_empty_rows(self) -> None:
        from kuberay_sdk.cli.formatters import format_table

        result = format_table(["NAME", "STATE"], [])
        lines = result.strip().split("\n")
        assert len(lines) == 1
        assert "NAME" in lines[0]

    def test_format_json(self) -> None:
        from kuberay_sdk.cli.formatters import format_json

        result = format_json({"name": "test", "count": 42})
        data = json.loads(result)
        assert data["name"] == "test"
        assert data["count"] == 42

    def test_format_json_with_timedelta(self) -> None:
        from kuberay_sdk.cli.formatters import format_json

        result = format_json({"age": timedelta(hours=2)})
        data = json.loads(result)
        assert "2:00:00" in data["age"]


# ──────────────────────────────────────────────
# Namespace passing
# ──────────────────────────────────────────────


class TestNamespacePassing:
    """Test that namespace is correctly passed through CLI context."""

    @patch("kuberay_sdk.cli.cluster._get_client")
    def test_global_namespace(self, mock_get_client: MagicMock) -> None:
        """``kuberay -n my-ns cluster list`` should pass namespace."""
        mock_client = MagicMock()
        mock_client.list_clusters.return_value = []
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["-n", "my-ns", "cluster", "list"])
        assert result.exit_code == 0
        # The _get_client should be called with context containing namespace
        mock_client.list_clusters.assert_called_once()

    @patch("kuberay_sdk.cli.cluster._get_client")
    def test_subcommand_namespace_override(self, mock_get_client: MagicMock) -> None:
        """Subcommand --namespace should override global -n."""
        mock_client = MagicMock()
        mock_client.list_clusters.return_value = []
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(cli, ["-n", "global-ns", "cluster", "list", "-n", "local-ns"])
        assert result.exit_code == 0
        # list_clusters should be called with local-ns
        call_kwargs = mock_client.list_clusters.call_args
        assert call_kwargs[1].get("namespace") == "local-ns"
