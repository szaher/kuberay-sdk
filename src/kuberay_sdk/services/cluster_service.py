"""ClusterService — CRUD operations for RayCluster CRs (T019-T023).

Manages RayCluster custom resources via the Kubernetes CustomObjectsApi.
Implements create (with idempotency), get_status, list, scale, delete,
and wait_until_ready operations.

Example:
    >>> from kuberay_sdk.services.cluster_service import ClusterService
    >>> svc = ClusterService(custom_api, config)
    >>> svc.create(name="my-cluster", namespace="default", workers=4)
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from kuberay_sdk.errors import (
    ClusterNotFoundError,
    TimeoutError,
    ValidationError,
)
from kuberay_sdk.models.cluster import (
    ClusterConfig,
    ClusterStatus,
    HeadNodeConfig,
    WorkerGroup,
)
from kuberay_sdk.retry import idempotent_create

if TYPE_CHECKING:
    from kuberay_sdk.config import SDKConfig
    from kuberay_sdk.models.runtime_env import RuntimeEnv
    from kuberay_sdk.models.storage import StorageVolume

logger = logging.getLogger(__name__)

# K8s API constants for RayCluster
GROUP = "ray.io"
VERSION = "v1"
PLURAL = "rayclusters"


class ClusterService:
    """Service for managing RayCluster custom resources.

    Example:
        >>> svc = ClusterService(custom_api, config)
        >>> svc.create(name="my-cluster", namespace="default", workers=4)
        >>> status = svc.get_status("my-cluster", "default")
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
        labels: dict[str, str] | None = None,
        annotations: dict[str, str] | None = None,
        tolerations: list[dict] | None = None,  # type: ignore[type-arg]
        node_selector: dict[str, str] | None = None,
        hardware_profile: str | None = None,
        queue: str | None = None,
        enable_autoscaling: bool = False,
        raw_overrides: dict | None = None,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Create a RayCluster CR.

        Builds a ClusterConfig, generates the CRD manifest, and applies
        it via create_namespaced_custom_object. Uses idempotent_create
        for 409 conflict handling (FR-043).

        Returns:
            The created (or existing identical) CR dict.

        Example:
            >>> svc.create(name="my-cluster", namespace="default", workers=4, gpus_per_worker=1)
        """
        # Build ClusterConfig kwargs
        config_kwargs: dict[str, Any] = {
            "name": name,
            "namespace": namespace,
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
        if tolerations is not None:
            config_kwargs["tolerations"] = tolerations
        if node_selector is not None:
            config_kwargs["node_selector"] = node_selector
        if hardware_profile is not None:
            config_kwargs["hardware_profile"] = hardware_profile
        if queue is not None:
            config_kwargs["queue"] = queue
        if enable_autoscaling:
            config_kwargs["enable_autoscaling"] = enable_autoscaling
        if raw_overrides is not None:
            config_kwargs["raw_overrides"] = raw_overrides

        cluster_config = ClusterConfig(**config_kwargs)
        body = cluster_config.to_crd_dict()

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

    def get_status(self, name: str, namespace: str) -> ClusterStatus:
        """Get the status of a RayCluster.

        Returns:
            ClusterStatus parsed from the CR.

        Raises:
            ClusterNotFoundError: If the cluster does not exist.

        Example:
            >>> status = svc.get_status("my-cluster", "default")
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
                raise ClusterNotFoundError(name, namespace) from exc
            raise
        return ClusterStatus.from_cr(cr)

    def list(self, namespace: str) -> list[ClusterStatus]:
        """List all RayClusters in a namespace.

        Returns:
            List of ClusterStatus objects.

        Example:
            >>> clusters = svc.list("default")
            >>> for c in clusters:
            ...     print(c.name, c.state)
        """
        response = self._api.list_namespaced_custom_object(
            group=self.GROUP,
            version=self.VERSION,
            namespace=namespace,
            plural=self.PLURAL,
        )
        items = response.get("items", [])
        return [ClusterStatus.from_cr(item) for item in items]

    def scale(self, name: str, namespace: str, workers: int) -> None:
        """Scale the first worker group of a RayCluster.

        Args:
            name: Cluster name.
            namespace: Cluster namespace.
            workers: New desired worker count (must be >= 1).

        Raises:
            ValidationError: If workers < 1.
            ClusterNotFoundError: If the cluster does not exist.

        Example:
            >>> svc.scale("my-cluster", "default", 8)
        """
        if workers < 1:
            raise ValidationError(f"Cannot scale to {workers} workers. Workers must be >= 1.")

        # Get the current cluster to know the existing spec structure
        cr = self._api.get_namespaced_custom_object(
            group=self.GROUP,
            version=self.VERSION,
            namespace=namespace,
            plural=self.PLURAL,
            name=name,
        )

        # Build a patch that updates the first worker group's replicas
        worker_specs = cr.get("spec", {}).get("workerGroupSpecs", [])
        if worker_specs:
            patched_specs = []
            for i, ws in enumerate(worker_specs):
                if i == 0:
                    patched_ws = dict(ws)
                    patched_ws["replicas"] = workers
                    patched_ws["minReplicas"] = workers
                    patched_ws["maxReplicas"] = workers
                    patched_specs.append(patched_ws)
                else:
                    patched_specs.append(ws)
        else:
            patched_specs = [
                {
                    "groupName": "default-workers",
                    "replicas": workers,
                    "minReplicas": workers,
                    "maxReplicas": workers,
                    "rayStartParams": {},
                }
            ]

        patch_body: dict[str, Any] = {
            "spec": {
                "workerGroupSpecs": patched_specs,
            }
        }

        self._api.patch_namespaced_custom_object(
            group=self.GROUP,
            version=self.VERSION,
            namespace=namespace,
            plural=self.PLURAL,
            name=name,
            body=patch_body,
        )

    def delete(
        self,
        name: str,
        namespace: str,
        force: bool = False,
    ) -> None:
        """Delete a RayCluster.

        Args:
            name: Cluster name.
            namespace: Cluster namespace.
            force: If False, performs a best-effort check for running jobs.

        Raises:
            ClusterNotFoundError: If the cluster does not exist.

        Example:
            >>> svc.delete("my-cluster", "default")
        """
        if not force:
            # Best-effort check for running jobs
            try:
                self._check_running_jobs(name, namespace)
            except Exception:
                # Best-effort only; don't block deletion on check failure
                pass

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
                raise ClusterNotFoundError(name, namespace) from exc
            raise

    def _check_running_jobs(self, cluster_name: str, namespace: str) -> None:
        """Best-effort check if any RayJobs reference this cluster."""
        try:
            jobs = self._api.list_namespaced_custom_object(
                group=self.GROUP,
                version=self.VERSION,
                namespace=namespace,
                plural="rayjobs",
            )
            for job in jobs.get("items", []):
                job_status = job.get("status", {}).get("jobStatus", "")
                if job_status.lower() in ("running", "pending"):
                    logger.warning(
                        "Job '%s' is still %s on cluster '%s'. Use force=True to delete anyway.",
                        job.get("metadata", {}).get("name", "unknown"),
                        job_status,
                        cluster_name,
                    )
        except Exception:
            pass

    def wait_until_ready(
        self,
        name: str,
        namespace: str,
        timeout: float = 300,
        poll_interval: float = 2.0,
        progress_callback: Any = None,
    ) -> None:
        """Poll until the cluster reaches RUNNING state with head ready.

        Args:
            name: Cluster name.
            namespace: Cluster namespace.
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between polls.
            progress_callback: Optional callable invoked each poll cycle with
                a ``ProgressStatus`` object. Exceptions raised by the callback
                are caught and logged (never propagate).

        Raises:
            TimeoutError: If the cluster does not become ready within timeout.

        Example:
            >>> svc.wait_until_ready("my-cluster", "default", timeout=300)
        """
        from kuberay_sdk.models.progress import ProgressStatus

        start = time.monotonic()
        last_progress: ProgressStatus | None = None

        while True:
            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                raise TimeoutError(
                    f"wait_until_ready({name})",
                    timeout,
                    last_status=last_progress,
                )

            status = self.get_status(name, namespace)
            progress = ProgressStatus(
                state=status.state,
                elapsed_seconds=elapsed,
                message=f"State: {status.state}, head_ready: {status.head_ready}",
            )
            last_progress = progress

            if progress_callback is not None:
                try:
                    progress_callback(progress)
                except Exception:
                    logger.warning("Progress callback raised an exception", exc_info=True)

            if status.state == "RUNNING" and status.head_ready:
                return

            time.sleep(poll_interval)
