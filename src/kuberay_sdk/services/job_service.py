"""JobService — CRUD operations for RayJob CRs and Dashboard submissions (T032).

Manages RayJob custom resources via the Kubernetes CustomObjectsApi and
supports job submission via the Ray Dashboard API. Implements create
(with idempotency), submit_to_dashboard, get_status, list, stop, and
wait operations.

Example:
    >>> from kuberay_sdk.services.job_service import JobService
    >>> svc = JobService(custom_api, config)
    >>> svc.create(name="my-job", namespace="default", entrypoint="python train.py")
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from kuberay_sdk.errors import (
    JobNotFoundError,
    TimeoutError,
)
from kuberay_sdk.models.job import JobConfig, JobStatus
from kuberay_sdk.models.runtime_env import ExperimentTracking, RuntimeEnv
from kuberay_sdk.retry import idempotent_create

if TYPE_CHECKING:
    from kuberay_sdk.config import SDKConfig
    from kuberay_sdk.models.cluster import HeadNodeConfig, WorkerGroup
    from kuberay_sdk.models.storage import StorageVolume
    from kuberay_sdk.services.dashboard import DashboardClient

logger = logging.getLogger(__name__)

# K8s API constants for RayJob
GROUP = "ray.io"
VERSION = "v1"
PLURAL = "rayjobs"

# Terminal states for job completion polling
_CRD_TERMINAL_STATES = {"SUCCEEDED", "FAILED", "STOPPED"}
_DASHBOARD_TERMINAL_STATES = {"SUCCEEDED", "FAILED", "STOPPED"}


class JobService:
    """Service for managing RayJob custom resources and Dashboard submissions.

    Example:
        >>> svc = JobService(custom_api, config)
        >>> svc.create(name="my-job", namespace="default", entrypoint="python train.py")
        >>> status = svc.get_status("my-job", "default")
    """

    GROUP = GROUP
    VERSION = VERSION
    PLURAL = PLURAL

    def __init__(self, custom_api: Any, config: SDKConfig) -> None:
        self._api = custom_api
        self._config = config

    def create(
        self,
        name: str,
        namespace: str,
        entrypoint: str,
        workers: int = 1,
        cpus_per_worker: float = 1.0,
        gpus_per_worker: int = 0,
        memory_per_worker: str = "2Gi",
        worker_groups: list[WorkerGroup] | None = None,
        head: HeadNodeConfig | None = None,
        ray_version: str | None = None,
        image: str | None = None,
        storage: list[StorageVolume] | None = None,
        runtime_env: RuntimeEnv | dict | None = None,  # type: ignore[type-arg]
        shutdown_after_finish: bool = True,
        labels: dict[str, str] | None = None,
        annotations: dict[str, str] | None = None,
        queue: str | None = None,
        hardware_profile: str | None = None,
        experiment_tracking: ExperimentTracking | dict | None = None,  # type: ignore[type-arg]
        raw_overrides: dict | None = None,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Create a RayJob CR.

        Builds a JobConfig, generates the CRD manifest, and applies it via
        create_namespaced_custom_object. Uses idempotent_create for 409
        conflict handling (FR-043).

        Returns:
            The created (or existing identical) CR dict.

        Example:
            >>> svc.create(
            ...     name="my-job",
            ...     namespace="default",
            ...     entrypoint="python train.py",
            ...     workers=4,
            ...     gpus_per_worker=1,
            ... )
        """
        # Build JobConfig kwargs
        config_kwargs: dict[str, Any] = {
            "name": name,
            "namespace": namespace,
            "entrypoint": entrypoint,
            "shutdown_after_finish": shutdown_after_finish,
        }

        if worker_groups is not None:
            config_kwargs["worker_groups"] = worker_groups
        else:
            config_kwargs["workers"] = workers
            config_kwargs["cpus_per_worker"] = cpus_per_worker
            config_kwargs["gpus_per_worker"] = gpus_per_worker
            config_kwargs["memory_per_worker"] = memory_per_worker

        if head is not None:
            config_kwargs["head"] = head
        if ray_version is not None:
            config_kwargs["ray_version"] = ray_version
        if image is not None:
            config_kwargs["image"] = image
        if storage is not None:
            config_kwargs["storage"] = storage
        if runtime_env is not None:
            config_kwargs["runtime_env"] = runtime_env
        if labels is not None:
            config_kwargs["labels"] = labels
        if annotations is not None:
            config_kwargs["annotations"] = annotations
        if queue is not None:
            config_kwargs["queue"] = queue
        if hardware_profile is not None:
            config_kwargs["hardware_profile"] = hardware_profile
        if experiment_tracking is not None:
            config_kwargs["experiment_tracking"] = experiment_tracking
        if raw_overrides is not None:
            config_kwargs["raw_overrides"] = raw_overrides

        job_config = JobConfig(**config_kwargs)
        body = job_config.to_crd_dict()

        def _create_fn(**kwargs: Any) -> Any:
            return self._api.create_namespaced_custom_object(**kwargs)

        def _get_fn(**kwargs: Any) -> Any:
            return self._api.get_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=namespace,
                plural=self.PLURAL,
                name=name,
            )

        def _compare_fn(existing: Any, desired: Any) -> bool:
            """Compare existing CR spec with desired spec."""
            existing_spec = existing.get("spec", {})
            desired_spec = desired.get("spec", {})
            return existing_spec == desired_spec

        return idempotent_create(
            create_fn=_create_fn,
            get_fn=_get_fn,
            compare_fn=_compare_fn,
            desired_spec=body,
            group=self.GROUP,
            version=self.VERSION,
            namespace=namespace,
            plural=self.PLURAL,
            body=body,
        )

    def submit_to_dashboard(
        self,
        dashboard_client: DashboardClient,
        entrypoint: str,
        runtime_env: RuntimeEnv | dict | None = None,  # type: ignore[type-arg]
        experiment_tracking: ExperimentTracking | dict | None = None,  # type: ignore[type-arg]
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Submit a job via the Ray Dashboard API.

        Args:
            dashboard_client: An initialized DashboardClient.
            entrypoint: Command to run.
            runtime_env: Optional RuntimeEnv or dict.
            experiment_tracking: Optional ExperimentTracking config.
            metadata: Optional metadata dict.

        Returns:
            The job ID string from the Dashboard.

        Example:
            >>> job_id = svc.submit_to_dashboard(dc, entrypoint="python train.py")
        """
        # Resolve runtime_env to a dict
        rt_dict: dict[str, Any] | None = None
        if runtime_env is not None:
            if isinstance(runtime_env, RuntimeEnv):
                rt_dict = runtime_env.to_dict()
            elif isinstance(runtime_env, dict):
                rt_dict = dict(runtime_env)

        # Resolve experiment tracking and merge env vars
        if experiment_tracking is not None:
            et: ExperimentTracking
            if isinstance(experiment_tracking, dict):
                et = ExperimentTracking(**experiment_tracking)
            else:
                et = experiment_tracking

            tracking_vars = et.to_env_vars()
            if rt_dict is None:
                rt_dict = {"env_vars": tracking_vars}
            else:
                existing_env = rt_dict.get("env_vars", {})
                existing_env.update(tracking_vars)
                rt_dict["env_vars"] = existing_env

        return dashboard_client.submit_job(
            entrypoint=entrypoint,
            runtime_env=rt_dict,
            metadata=metadata,
        )

    def get_status(self, name: str, namespace: str) -> JobStatus:
        """Get the status of a RayJob CR.

        Returns:
            JobStatus parsed from the CR.

        Raises:
            JobNotFoundError: If the job does not exist.

        Example:
            >>> status = svc.get_status("my-job", "default")
            >>> print(status.state)
        """
        try:
            cr = self._api.get_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=namespace,
                plural=self.PLURAL,
                name=name,
            )
        except Exception as exc:
            status_code = getattr(exc, "status", None)
            if status_code == 404:
                raise JobNotFoundError(name, namespace) from exc
            raise
        return JobStatus.from_cr(cr)

    def get_dashboard_job_status(
        self,
        dashboard_client: DashboardClient,
        job_id: str,
    ) -> dict[str, Any]:
        """Get job status from the Ray Dashboard.

        Args:
            dashboard_client: An initialized DashboardClient.
            job_id: The Dashboard job ID.

        Returns:
            Job status dict from the Dashboard.

        Example:
            >>> status = svc.get_dashboard_job_status(dc, "raysubmit_abc123")
        """
        return dashboard_client.get_job_status(job_id)

    def list(self, namespace: str) -> list[JobStatus]:
        """List all RayJob CRs in a namespace.

        Returns:
            List of JobStatus objects.

        Example:
            >>> jobs = svc.list("default")
            >>> for j in jobs:
            ...     print(j.name, j.state)
        """
        response = self._api.list_namespaced_custom_object(
            group=self.GROUP,
            version=self.VERSION,
            namespace=namespace,
            plural=self.PLURAL,
        )
        items = response.get("items", [])
        return [JobStatus.from_cr(item) for item in items]

    def stop(self, name: str, namespace: str) -> None:
        """Stop/delete a RayJob CR.

        Args:
            name: Job name.
            namespace: Job namespace.

        Raises:
            JobNotFoundError: If the job does not exist.

        Example:
            >>> svc.stop("my-job", "default")
        """
        try:
            self._api.delete_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=namespace,
                plural=self.PLURAL,
                name=name,
            )
        except Exception as exc:
            status_code = getattr(exc, "status", None)
            if status_code == 404:
                raise JobNotFoundError(name, namespace) from exc
            raise

    def wait(
        self,
        name: str,
        namespace: str,
        timeout: float = 3600,
        poll_interval: float = 2.0,
        progress_callback: Any = None,
    ) -> JobStatus:
        """Poll until a RayJob CR reaches a terminal state.

        Terminal states: SUCCEEDED, FAILED, STOPPED.

        Args:
            name: Job name.
            namespace: Job namespace.
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between polls.
            progress_callback: Optional callable invoked each poll cycle with
                a ``ProgressStatus`` object. Exceptions raised by the callback
                are caught and logged (never propagate).

        Returns:
            The final JobStatus.

        Raises:
            TimeoutError: If the job does not complete within timeout.

        Example:
            >>> status = svc.wait("my-job", "default", timeout=3600)
        """
        from kuberay_sdk.models.progress import ProgressStatus

        start = time.monotonic()
        last_progress: ProgressStatus | None = None

        while True:
            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                raise TimeoutError(
                    f"wait({name})",
                    timeout,
                    last_status=last_progress,
                )

            status = self.get_status(name, namespace)
            progress = ProgressStatus(
                state=status.state.value,
                elapsed_seconds=elapsed,
                message=f"Job state: {status.state.value}",
            )
            last_progress = progress

            if progress_callback is not None:
                try:
                    progress_callback(progress)
                except Exception:
                    logger.warning("Progress callback raised an exception", exc_info=True)

            if status.state.value in _CRD_TERMINAL_STATES:
                return status

            time.sleep(poll_interval)

    def wait_dashboard_job(
        self,
        dashboard_client: DashboardClient,
        job_id: str,
        timeout: float = 3600,
        poll_interval: float = 2.0,
        progress_callback: Any = None,
    ) -> dict[str, Any]:
        """Poll the Dashboard until a job reaches a terminal state.

        Terminal states: SUCCEEDED, FAILED, STOPPED.

        Args:
            dashboard_client: An initialized DashboardClient.
            job_id: The Dashboard job ID.
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between polls.
            progress_callback: Optional callable invoked each poll cycle with
                a ``ProgressStatus`` object. Exceptions raised by the callback
                are caught and logged (never propagate).

        Returns:
            The final job status dict from the Dashboard.

        Raises:
            TimeoutError: If the job does not complete within timeout.

        Example:
            >>> result = svc.wait_dashboard_job(dc, "raysubmit_abc123", timeout=3600)
        """
        from kuberay_sdk.models.progress import ProgressStatus

        start = time.monotonic()
        last_progress: ProgressStatus | None = None

        while True:
            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                raise TimeoutError(
                    f"wait_dashboard_job({job_id})",
                    timeout,
                    last_status=last_progress,
                )

            status_dict = dashboard_client.get_job_status(job_id)
            job_status = status_dict.get("status", "").upper()
            progress = ProgressStatus(
                state=job_status,
                elapsed_seconds=elapsed,
                message=status_dict.get("message", ""),
            )
            last_progress = progress

            if progress_callback is not None:
                try:
                    progress_callback(progress)
                except Exception:
                    logger.warning("Progress callback raised an exception", exc_info=True)

            if job_status in _DASHBOARD_TERMINAL_STATES:
                return status_dict

            time.sleep(poll_interval)
