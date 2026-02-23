"""DashboardClient — Ray Dashboard HTTP API client (T030).

Implements interaction with the Ray Dashboard REST API using httpx for
job submission, status polling, log retrieval, and cluster metrics.

Example:
    >>> from kuberay_sdk.services.dashboard import DashboardClient
    >>> dc = DashboardClient("http://localhost:8265")
    >>> job_id = dc.submit_job(entrypoint="python train.py")
    >>> status = dc.get_job_status(job_id)
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import httpx

from kuberay_sdk.errors import DashboardUnreachableError, JobError

logger = logging.getLogger(__name__)


class DashboardClient:
    """HTTP client for the Ray Dashboard REST API.

    Example:
        >>> dc = DashboardClient("http://localhost:8265")
        >>> job_id = dc.submit_job(entrypoint="python train.py")
        >>> print(dc.get_job_status(job_id))
    """

    def __init__(self, base_url: str) -> None:
        """Initialize DashboardClient.

        Args:
            base_url: Base URL of the Ray Dashboard (e.g., "http://localhost:8265").
        """
        # Ensure no trailing slash
        self._base_url = base_url.rstrip("/")

    def submit_job(
        self,
        entrypoint: str,
        runtime_env: dict[str, Any] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Submit a job to the Ray Dashboard.

        Args:
            entrypoint: Command to run (e.g., "python train.py").
            runtime_env: Optional runtime environment configuration dict.
            metadata: Optional metadata dict (e.g., {"job_submission_id": "custom-id"}).

        Returns:
            The job ID string assigned by the Dashboard.

        Raises:
            DashboardUnreachableError: If the Dashboard is not reachable.
            JobError: If submission fails.

        Example:
            >>> job_id = dc.submit_job(
            ...     entrypoint="python train.py",
            ...     runtime_env={"pip": ["torch"]},
            ... )
        """
        url = f"{self._base_url}/api/jobs/"
        payload: dict[str, Any] = {"entrypoint": entrypoint}

        if runtime_env is not None:
            payload["runtime_env"] = runtime_env
        if metadata is not None:
            payload["metadata"] = metadata

        try:
            with httpx.Client() as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                job_id = data.get("job_id") or data.get("submission_id", "")
                if not job_id:
                    raise JobError("Dashboard returned empty job_id.")
                return job_id
        except httpx.ConnectError as exc:
            raise DashboardUnreachableError(
                cluster_name="unknown",
                reason=f"Connection failed: {exc}",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise JobError(
                f"Job submission failed with status {exc.response.status_code}: {exc.response.text}"
            ) from exc

    def list_jobs(self) -> list[dict[str, Any]]:
        """List all jobs from the Ray Dashboard.

        Returns:
            List of job status dicts.

        Example:
            >>> jobs = dc.list_jobs()
            >>> for j in jobs:
            ...     print(j["job_id"], j["status"])
        """
        url = f"{self._base_url}/api/jobs/"
        try:
            with httpx.Client() as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError as exc:
            raise DashboardUnreachableError(
                cluster_name="unknown",
                reason=f"Connection failed: {exc}",
            ) from exc

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get the status of a specific job.

        Args:
            job_id: The job ID to query.

        Returns:
            Job status dict matching DASHBOARD_JOB_STATUS_RESPONSE schema.

        Example:
            >>> status = dc.get_job_status("raysubmit_abc123")
            >>> print(status["status"])
        """
        url = f"{self._base_url}/api/jobs/{job_id}"
        try:
            with httpx.Client() as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError as exc:
            raise DashboardUnreachableError(
                cluster_name="unknown",
                reason=f"Connection failed: {exc}",
            ) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise JobError(f"Job '{job_id}' not found on the Dashboard.") from exc
            raise JobError(f"Failed to get job status: {exc.response.status_code}") from exc

    def stop_job(self, job_id: str) -> None:
        """Stop a running job.

        Args:
            job_id: The job ID to stop.

        Example:
            >>> dc.stop_job("raysubmit_abc123")
        """
        url = f"{self._base_url}/api/jobs/{job_id}/stop"
        try:
            with httpx.Client() as client:
                response = client.post(url)
                response.raise_for_status()
        except httpx.ConnectError as exc:
            raise DashboardUnreachableError(
                cluster_name="unknown",
                reason=f"Connection failed: {exc}",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise JobError(f"Failed to stop job '{job_id}': {exc.response.status_code}") from exc

    def get_logs(self, job_id: str, tail: int | None = None) -> str:
        """Get the full logs of a job.

        Args:
            job_id: The job ID to get logs for.
            tail: If set, return only the last N lines.

        Returns:
            The logs as a string.

        Example:
            >>> logs = dc.get_logs("raysubmit_abc123")
            >>> print(logs)
        """
        url = f"{self._base_url}/api/jobs/{job_id}/logs"
        try:
            with httpx.Client() as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()
                logs = data.get("logs", "")
                if tail is not None and tail > 0:
                    lines = logs.split("\n")
                    logs = "\n".join(lines[-tail:])
                return logs
        except httpx.ConnectError as exc:
            raise DashboardUnreachableError(
                cluster_name="unknown",
                reason=f"Connection failed: {exc}",
            ) from exc

    def stream_logs(
        self,
        job_id: str,
        follow: bool = False,
    ) -> Iterator[str]:
        """Stream job logs line by line.

        Uses the /api/jobs/{job_id}/logs/tail endpoint with httpx streaming.

        Args:
            job_id: The job ID to stream logs for.
            follow: If True, continue streaming until the job completes.

        Yields:
            Log lines as strings.

        Example:
            >>> for line in dc.stream_logs("raysubmit_abc123", follow=True):
            ...     print(line)
        """
        url = f"{self._base_url}/api/jobs/{job_id}/logs/tail"
        params: dict[str, str] = {}
        if follow:
            params["follow"] = "true"

        try:
            with httpx.Client(timeout=None) as client, client.stream("GET", url, params=params) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        yield line
        except httpx.ConnectError as exc:
            raise DashboardUnreachableError(
                cluster_name="unknown",
                reason=f"Connection failed: {exc}",
            ) from exc

    def get_cluster_metrics(self) -> dict[str, Any]:
        """Get cluster-level resource metrics from the Dashboard.

        Returns:
            Dict with cluster status and resource information.

        Example:
            >>> metrics = dc.get_cluster_metrics()
            >>> print(metrics)
        """
        url = f"{self._base_url}/api/cluster_status"
        try:
            with httpx.Client() as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError as exc:
            raise DashboardUnreachableError(
                cluster_name="unknown",
                reason=f"Connection failed: {exc}",
            ) from exc

    def get_job_progress(self, job_id: str) -> dict[str, Any]:
        """Get job progress information from the Dashboard.

        Args:
            job_id: The job ID to query.

        Returns:
            Dict with job progress information.

        Example:
            >>> progress = dc.get_job_progress("raysubmit_abc123")
        """
        url = f"{self._base_url}/api/jobs/{job_id}"
        try:
            with httpx.Client() as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError as exc:
            raise DashboardUnreachableError(
                cluster_name="unknown",
                reason=f"Connection failed: {exc}",
            ) from exc

    def download_artifacts(self, job_id: str, destination: str) -> None:
        """Download job artifacts to a local directory.

        This is a placeholder implementation. Full artifact download
        would require additional Ray Dashboard API endpoints or PVC access.

        Args:
            job_id: The job ID to download artifacts for.
            destination: Local directory path to save artifacts.

        Example:
            >>> dc.download_artifacts("raysubmit_abc123", "./output")
        """
        logger.warning(
            "Artifact download is not yet fully implemented. "
            "Job ID: %s, Destination: %s. "
            "Consider copying artifacts from the job's PVC or using "
            "Ray's built-in artifact storage mechanisms.",
            job_id,
            destination,
        )
