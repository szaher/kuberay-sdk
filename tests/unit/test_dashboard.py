"""Unit tests for DashboardClient streaming/metrics and PortForwardManager URL discovery.

Covers:
- T035: SSE log streaming (stream_logs, get_logs)
- T036: Artifact download placeholder
- T053: Dashboard URL discovery (Route, Ingress, port-forward fallback)
- T054: Cluster metrics and job progress
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from kuberay_sdk.errors import DashboardUnreachableError
from kuberay_sdk.services.dashboard import DashboardClient
from kuberay_sdk.services.port_forward import PortForwardManager

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_mock_response(
    status_code: int = 200,
    json_data: Any = None,
    text: str = "",
) -> MagicMock:
    """Create a mock httpx.Response."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.text = text
    response.raise_for_status = MagicMock()
    return response


def _setup_httpx_client_mock(mock_client_cls: MagicMock) -> MagicMock:
    """Wire up the httpx.Client context manager mock and return the inner client."""
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
    mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
    return mock_client


# ──────────────────────────────────────────────
# T035 - SSE Log Streaming Tests
# ──────────────────────────────────────────────


class TestDashboardLogStreaming:
    """Verify log streaming and retrieval via the Dashboard API."""

    @patch("kuberay_sdk.services.dashboard.httpx.Client")
    def test_stream_logs_yields_lines(self, mock_client_cls: MagicMock) -> None:
        """stream_logs should yield each non-empty line from the streaming response."""
        mock_client = _setup_httpx_client_mock(mock_client_cls)

        # Build a mock streaming response whose iter_lines yields lines
        mock_stream_response = MagicMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.iter_lines.return_value = iter(["line-1", "line-2", "", "line-3"])
        # client.stream() returns a context manager
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)
        mock_client.stream.return_value = mock_stream_ctx

        dc = DashboardClient("http://localhost:8265")
        lines = list(dc.stream_logs("raysubmit_abc123"))

        assert lines == ["line-1", "line-2", "line-3"]
        mock_client.stream.assert_called_once_with(
            "GET",
            "http://localhost:8265/api/jobs/raysubmit_abc123/logs/tail",
            params={},
        )

    @patch("kuberay_sdk.services.dashboard.httpx.Client")
    def test_stream_logs_follow_mode_sends_follow_param(self, mock_client_cls: MagicMock) -> None:
        """When follow=True, the request must include params={'follow': 'true'}."""
        mock_client = _setup_httpx_client_mock(mock_client_cls)

        mock_stream_response = MagicMock()
        mock_stream_response.raise_for_status = MagicMock()
        mock_stream_response.iter_lines.return_value = iter(["log-output"])
        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_ctx.__exit__ = MagicMock(return_value=False)
        mock_client.stream.return_value = mock_stream_ctx

        dc = DashboardClient("http://localhost:8265")
        list(dc.stream_logs("raysubmit_abc123", follow=True))

        mock_client.stream.assert_called_once_with(
            "GET",
            "http://localhost:8265/api/jobs/raysubmit_abc123/logs/tail",
            params={"follow": "true"},
        )

    @patch("kuberay_sdk.services.dashboard.httpx.Client")
    def test_stream_logs_raises_dashboard_unreachable_on_connection_error(self, mock_client_cls: MagicMock) -> None:
        """stream_logs must raise DashboardUnreachableError on ConnectError."""
        mock_client = _setup_httpx_client_mock(mock_client_cls)

        mock_client.stream.side_effect = httpx.ConnectError("refused")

        dc = DashboardClient("http://localhost:8265")
        with pytest.raises(DashboardUnreachableError, match="Connection failed"):
            list(dc.stream_logs("raysubmit_abc123"))

    @patch("kuberay_sdk.services.dashboard.httpx.Client")
    def test_get_logs_returns_full_text(self, mock_client_cls: MagicMock) -> None:
        """get_logs should return the full log text from the JSON response."""
        mock_client = _setup_httpx_client_mock(mock_client_cls)

        full_logs = "epoch 1\nepoch 2\nepoch 3\ndone"
        mock_client.get.return_value = _make_mock_response(
            json_data={"logs": full_logs},
        )

        dc = DashboardClient("http://localhost:8265")
        result = dc.get_logs("raysubmit_abc123")

        assert result == full_logs
        mock_client.get.assert_called_once_with(
            "http://localhost:8265/api/jobs/raysubmit_abc123/logs",
        )

    @patch("kuberay_sdk.services.dashboard.httpx.Client")
    def test_get_logs_tail_returns_last_n_lines(self, mock_client_cls: MagicMock) -> None:
        """get_logs(tail=N) should return only the last N lines."""
        mock_client = _setup_httpx_client_mock(mock_client_cls)

        full_logs = "line1\nline2\nline3\nline4\nline5"
        mock_client.get.return_value = _make_mock_response(
            json_data={"logs": full_logs},
        )

        dc = DashboardClient("http://localhost:8265")
        result = dc.get_logs("raysubmit_abc123", tail=2)

        assert result == "line4\nline5"

    @patch("kuberay_sdk.services.dashboard.httpx.Client")
    def test_get_logs_raises_on_connection_error(self, mock_client_cls: MagicMock) -> None:
        """get_logs must raise DashboardUnreachableError on ConnectError."""
        mock_client = _setup_httpx_client_mock(mock_client_cls)

        mock_client.get.side_effect = httpx.ConnectError("refused")

        dc = DashboardClient("http://localhost:8265")
        with pytest.raises(DashboardUnreachableError, match="Connection failed"):
            dc.get_logs("raysubmit_abc123")


# ──────────────────────────────────────────────
# T036 - Artifact Download Tests
# ──────────────────────────────────────────────


class TestDashboardArtifactDownload:
    """Verify the artifact download placeholder behaviour."""

    def test_download_artifacts_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """download_artifacts should emit a warning since it is a placeholder."""
        dc = DashboardClient("http://localhost:8265")

        with caplog.at_level(logging.WARNING):
            dc.download_artifacts("raysubmit_abc123", "/tmp/output")

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelno == logging.WARNING
        assert "not yet fully implemented" in record.message
        assert "raysubmit_abc123" in record.message
        assert "/tmp/output" in record.message


# ──────────────────────────────────────────────
# T053 - Dashboard URL Discovery Tests
# ──────────────────────────────────────────────


class TestDashboardURL:
    """Verify PortForwardManager URL discovery (Route -> Ingress -> port-forward)."""

    @patch("kubernetes.client.CustomObjectsApi")
    def test_port_forward_manager_check_route(self, mock_custom_api_cls: MagicMock) -> None:
        """When an OpenShift Route exists for the head-svc, return its URL."""
        mock_api = MagicMock()
        mock_custom_api_cls.return_value = mock_api

        mock_api.list_namespaced_custom_object.return_value = {
            "items": [
                {
                    "spec": {
                        "to": {"name": "my-cluster-head-svc"},
                        "host": "my-cluster.apps.example.com",
                        "tls": {"termination": "edge"},
                    }
                }
            ]
        }

        pfm = PortForwardManager(MagicMock())
        url = pfm._check_route("my-cluster", "default")

        assert url == "https://my-cluster.apps.example.com"
        mock_api.list_namespaced_custom_object.assert_called_once_with(
            group="route.openshift.io",
            version="v1",
            namespace="default",
            plural="routes",
        )

    @patch("kubernetes.client.NetworkingV1Api")
    def test_port_forward_manager_check_ingress(self, mock_networking_cls: MagicMock) -> None:
        """When a Kubernetes Ingress exists for the head-svc, return its URL."""
        mock_api = MagicMock()
        mock_networking_cls.return_value = mock_api

        # Build mock Ingress objects matching the kubernetes-client model structure
        mock_backend = MagicMock()
        mock_backend.service.name = "my-cluster-head-svc"

        mock_path = MagicMock()
        mock_path.backend = mock_backend

        mock_rule = MagicMock()
        mock_rule.host = "my-cluster.example.com"
        mock_rule.http.paths = [mock_path]

        mock_tls = MagicMock()
        mock_tls.hosts = ["my-cluster.example.com"]

        mock_ingress = MagicMock()
        mock_ingress.spec.rules = [mock_rule]
        mock_ingress.spec.tls = [mock_tls]

        mock_ingress_list = MagicMock()
        mock_ingress_list.items = [mock_ingress]
        mock_api.list_namespaced_ingress.return_value = mock_ingress_list

        pfm = PortForwardManager(MagicMock())
        url = pfm._check_ingress("my-cluster", "default")

        assert url == "https://my-cluster.example.com"
        mock_api.list_namespaced_ingress.assert_called_once_with(namespace="default")

    @patch.object(PortForwardManager, "_start_port_forward", return_value="http://localhost:54321")
    @patch.object(PortForwardManager, "_check_ingress", return_value=None)
    @patch.object(PortForwardManager, "_check_route", return_value=None)
    def test_port_forward_manager_fallback_to_port_forward(
        self,
        mock_check_route: MagicMock,
        mock_check_ingress: MagicMock,
        mock_start_pf: MagicMock,
    ) -> None:
        """When both Route and Ingress return None, fall back to port-forward."""
        pfm = PortForwardManager(MagicMock())
        url = pfm.get_dashboard_url("my-cluster", "default")

        assert url == "http://localhost:54321"
        mock_check_route.assert_called_once_with("my-cluster", "default")
        mock_check_ingress.assert_called_once_with("my-cluster", "default")
        mock_start_pf.assert_called_once_with("my-cluster", "default")


# ──────────────────────────────────────────────
# T054 - Cluster Metrics Tests
# ──────────────────────────────────────────────


class TestDashboardMetrics:
    """Verify cluster metrics and job progress retrieval."""

    @patch("kuberay_sdk.services.dashboard.httpx.Client")
    def test_get_cluster_metrics_returns_dict(self, mock_client_cls: MagicMock) -> None:
        """get_cluster_metrics should return the JSON dict from /api/cluster_status."""
        mock_client = _setup_httpx_client_mock(mock_client_cls)

        expected = {
            "result": True,
            "data": {
                "clusterStatus": {
                    "loadMetricsReport": {
                        "numAvailableCpus": 8.0,
                        "numAvailableGpus": 2.0,
                    }
                }
            },
        }
        mock_client.get.return_value = _make_mock_response(json_data=expected)

        dc = DashboardClient("http://localhost:8265")
        result = dc.get_cluster_metrics()

        assert result == expected
        mock_client.get.assert_called_once_with(
            "http://localhost:8265/api/cluster_status",
        )

    @patch("kuberay_sdk.services.dashboard.httpx.Client")
    def test_get_cluster_metrics_raises_on_connection_error(self, mock_client_cls: MagicMock) -> None:
        """get_cluster_metrics must raise DashboardUnreachableError on ConnectError."""
        mock_client = _setup_httpx_client_mock(mock_client_cls)

        mock_client.get.side_effect = httpx.ConnectError("refused")

        dc = DashboardClient("http://localhost:8265")
        with pytest.raises(DashboardUnreachableError, match="Connection failed"):
            dc.get_cluster_metrics()

    @patch("kuberay_sdk.services.dashboard.httpx.Client")
    def test_get_job_progress_returns_dict(self, mock_client_cls: MagicMock) -> None:
        """get_job_progress should return the JSON dict from /api/jobs/{job_id}."""
        mock_client = _setup_httpx_client_mock(mock_client_cls)

        expected = {
            "job_id": "raysubmit_abc123",
            "status": "RUNNING",
            "start_time": 1700000000,
            "driver_info": {"pid": "12345"},
        }
        mock_client.get.return_value = _make_mock_response(json_data=expected)

        dc = DashboardClient("http://localhost:8265")
        result = dc.get_job_progress("raysubmit_abc123")

        assert result == expected
        mock_client.get.assert_called_once_with(
            "http://localhost:8265/api/jobs/raysubmit_abc123",
        )

    @patch("kuberay_sdk.services.dashboard.httpx.Client")
    def test_get_job_progress_raises_on_connection_error(self, mock_client_cls: MagicMock) -> None:
        """get_job_progress must raise DashboardUnreachableError on ConnectError."""
        mock_client = _setup_httpx_client_mock(mock_client_cls)

        mock_client.get.side_effect = httpx.ConnectError("refused")

        dc = DashboardClient("http://localhost:8265")
        with pytest.raises(DashboardUnreachableError, match="Connection failed"):
            dc.get_job_progress("raysubmit_abc123")
