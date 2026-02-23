"""Contract tests: Dashboard submission payload matches DASHBOARD_JOB_SUBMISSION_PAYLOAD (T025).

These tests verify that payloads submitted via the DashboardClient conform to
the expected Dashboard API format defined in
``specs/.../contracts/crd_schemas.py::DASHBOARD_JOB_SUBMISSION_PAYLOAD``.

TDD: these tests are written BEFORE ``kuberay_sdk.services.dashboard`` is
implemented. They will fail on import until the implementation is created.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from kuberay_sdk.services.dashboard import DashboardClient

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


# ──────────────────────────────────────────────
# Entrypoint required
# ──────────────────────────────────────────────


class TestDashboardPayloadEntrypoint:
    """Verify entrypoint is required in submission payload."""

    @patch("httpx.Client")
    def test_entrypoint_in_payload(self, mock_client_cls: MagicMock):
        """The POST body must include 'entrypoint' as a string."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        submit_response = _make_mock_response(
            status_code=200,
            json_data={"job_id": "raysubmit_test123", "submission_id": "raysubmit_test123"},
        )
        mock_client.post.return_value = submit_response

        dc = DashboardClient("http://localhost:8265")
        dc.submit_job(entrypoint="python train.py")

        # Extract the JSON payload sent to the dashboard
        call_args = mock_client.post.call_args
        payload = call_args[1].get("json") or call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("json")
        assert payload is not None
        assert "entrypoint" in payload
        assert payload["entrypoint"] == "python train.py"

    @patch("httpx.Client")
    def test_entrypoint_is_string(self, mock_client_cls: MagicMock):
        """Entrypoint must be a string, not a list or dict."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        submit_response = _make_mock_response(
            status_code=200,
            json_data={"job_id": "raysubmit_test123"},
        )
        mock_client.post.return_value = submit_response

        dc = DashboardClient("http://localhost:8265")
        dc.submit_job(entrypoint="python -m my_module")

        call_args = mock_client.post.call_args
        payload = call_args[1].get("json")
        assert isinstance(payload["entrypoint"], str)


# ──────────────────────────────────────────────
# runtime_env dict format
# ──────────────────────────────────────────────


class TestDashboardPayloadRuntimeEnv:
    """Verify runtime_env is passed as a dict (not YAML string)."""

    @patch("httpx.Client")
    def test_runtime_env_is_dict(self, mock_client_cls: MagicMock):
        """runtime_env must be a dict in the payload, not a YAML string."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        submit_response = _make_mock_response(
            status_code=200,
            json_data={"job_id": "raysubmit_test123"},
        )
        mock_client.post.return_value = submit_response

        runtime_env = {"pip": ["torch", "transformers"], "env_vars": {"KEY": "val"}}
        dc = DashboardClient("http://localhost:8265")
        dc.submit_job(entrypoint="python train.py", runtime_env=runtime_env)

        call_args = mock_client.post.call_args
        payload = call_args[1].get("json")
        assert isinstance(payload["runtime_env"], dict)
        assert "pip" in payload["runtime_env"]

    @patch("httpx.Client")
    def test_runtime_env_optional(self, mock_client_cls: MagicMock):
        """runtime_env should be omitted or empty when not provided."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        submit_response = _make_mock_response(
            status_code=200,
            json_data={"job_id": "raysubmit_test123"},
        )
        mock_client.post.return_value = submit_response

        dc = DashboardClient("http://localhost:8265")
        dc.submit_job(entrypoint="python train.py")

        call_args = mock_client.post.call_args
        payload = call_args[1].get("json")
        # runtime_env should be absent, None, or an empty dict
        rt = payload.get("runtime_env")
        assert rt is None or rt == {}


# ──────────────────────────────────────────────
# metadata structure
# ──────────────────────────────────────────────


class TestDashboardPayloadMetadata:
    """Verify metadata structure in the submission payload."""

    @patch("httpx.Client")
    def test_metadata_is_dict(self, mock_client_cls: MagicMock):
        """metadata must be a dict in the payload."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        submit_response = _make_mock_response(
            status_code=200,
            json_data={"job_id": "raysubmit_test123"},
        )
        mock_client.post.return_value = submit_response

        metadata = {"job_submission_id": "custom-id-123", "user": "tester"}
        dc = DashboardClient("http://localhost:8265")
        dc.submit_job(
            entrypoint="python train.py",
            metadata=metadata,
        )

        call_args = mock_client.post.call_args
        payload = call_args[1].get("json")
        assert isinstance(payload.get("metadata"), dict)
        assert payload["metadata"]["job_submission_id"] == "custom-id-123"

    @patch("httpx.Client")
    def test_metadata_optional(self, mock_client_cls: MagicMock):
        """metadata should be omitted or empty when not provided."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        submit_response = _make_mock_response(
            status_code=200,
            json_data={"job_id": "raysubmit_test123"},
        )
        mock_client.post.return_value = submit_response

        dc = DashboardClient("http://localhost:8265")
        dc.submit_job(entrypoint="python train.py")

        call_args = mock_client.post.call_args
        payload = call_args[1].get("json")
        md = payload.get("metadata")
        assert md is None or md == {}


# ──────────────────────────────────────────────
# POST endpoint
# ──────────────────────────────────────────────


class TestDashboardSubmitEndpoint:
    """Verify the correct endpoint is used for job submission."""

    @patch("httpx.Client")
    def test_submit_posts_to_correct_url(self, mock_client_cls: MagicMock):
        """submit_job must POST to /api/jobs/."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        submit_response = _make_mock_response(
            status_code=200,
            json_data={"job_id": "raysubmit_test123"},
        )
        mock_client.post.return_value = submit_response

        dc = DashboardClient("http://localhost:8265")
        dc.submit_job(entrypoint="python train.py")

        call_args = mock_client.post.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
        assert "/api/jobs/" in url

    @patch("httpx.Client")
    def test_submit_returns_job_id(self, mock_client_cls: MagicMock):
        """submit_job must return a job_id string."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        submit_response = _make_mock_response(
            status_code=200,
            json_data={"job_id": "raysubmit_abc123", "submission_id": "raysubmit_abc123"},
        )
        mock_client.post.return_value = submit_response

        dc = DashboardClient("http://localhost:8265")
        job_id = dc.submit_job(entrypoint="python train.py")
        assert isinstance(job_id, str)
        assert len(job_id) > 0


# ──────────────────────────────────────────────
# Full payload shape
# ──────────────────────────────────────────────


class TestDashboardPayloadShape:
    """Verify the full payload shape matches the contract."""

    @patch("httpx.Client")
    def test_full_payload_keys(self, mock_client_cls: MagicMock):
        """Verify payload has the expected keys when all fields provided."""
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        submit_response = _make_mock_response(
            status_code=200,
            json_data={"job_id": "raysubmit_test123"},
        )
        mock_client.post.return_value = submit_response

        dc = DashboardClient("http://localhost:8265")
        dc.submit_job(
            entrypoint="python train.py",
            runtime_env={"pip": ["torch"]},
            metadata={"user": "tester"},
        )

        call_args = mock_client.post.call_args
        payload = call_args[1].get("json")
        assert "entrypoint" in payload
        # Other fields are optional but should be valid types if present
        if "runtime_env" in payload:
            assert isinstance(payload["runtime_env"], dict)
        if "metadata" in payload:
            assert isinstance(payload["metadata"], dict)
