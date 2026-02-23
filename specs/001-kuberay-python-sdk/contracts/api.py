"""
KubeRay Python SDK — Public API Contract

This file defines the public interface of the kuberay_sdk package.
All public classes, methods, and their signatures are declared here
as the API contract. Implementation must conform to these signatures.

This contract is the source of truth for:
- What users can import and call
- Method signatures and return types
- Parameter names and types

Note: This is a design artifact, not runnable code. It uses Python
type annotation syntax for clarity but may reference types not yet
implemented.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Iterator, Optional, Union


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

class SDKConfig:
    """SDK-level configuration. Passed to client constructor."""

    namespace: Optional[str]
    """Default namespace. If None, uses kubeconfig active context namespace."""

    retry_max_attempts: int  # default: 3
    retry_backoff_factor: float  # default: 0.5
    retry_timeout: float  # default: 60.0

    hardware_profile_namespace: str  # default: "redhat-ods-applications"

    def __init__(
        self,
        *,
        namespace: Optional[str] = None,
        auth: Optional[Any] = None,  # kube_authkit.AuthConfig
        retry_max_attempts: int = 3,
        retry_backoff_factor: float = 0.5,
        retry_timeout: float = 60.0,
        hardware_profile_namespace: str = "redhat-ods-applications",
    ) -> None: ...


# ──────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────

class WorkerGroup:
    """A homogeneous group of workers within a RayCluster."""

    def __init__(
        self,
        *,
        name: str,
        replicas: int,
        cpus: float = 1.0,
        gpus: int = 0,
        memory: str = "2Gi",
        min_replicas: Optional[int] = None,
        max_replicas: Optional[int] = None,
        gpu_type: Optional[str] = None,
        ray_start_params: Optional[dict[str, str]] = None,
    ) -> None: ...


class HeadNodeConfig:
    """Override head node resource defaults."""

    def __init__(
        self,
        *,
        cpus: float = 1.0,
        memory: str = "2Gi",
        gpus: int = 0,
        ray_start_params: Optional[dict[str, str]] = None,
    ) -> None: ...


class StorageVolume:
    """Volume attachment for clusters and jobs."""

    def __init__(
        self,
        *,
        name: str,
        mount_path: str,
        size: Optional[str] = None,
        existing_claim: Optional[str] = None,
        access_mode: str = "ReadWriteOnce",
        storage_class: Optional[str] = None,
    ) -> None: ...


class RuntimeEnv:
    """Ray runtime environment configuration."""

    def __init__(
        self,
        *,
        pip: Optional[list[str]] = None,
        conda: Optional[Union[str, dict]] = None,
        env_vars: Optional[dict[str, str]] = None,
        working_dir: Optional[str] = None,
        py_modules: Optional[list[str]] = None,
    ) -> None: ...


class ExperimentTracking:
    """Experiment tracking configuration (MLflow)."""

    def __init__(
        self,
        *,
        provider: str,  # "mlflow"
        tracking_uri: str,
        experiment_name: Optional[str] = None,
        env_vars: Optional[dict[str, str]] = None,
    ) -> None: ...


# ──────────────────────────────────────────────
# Status objects (read-only)
# ──────────────────────────────────────────────

class ClusterStatus:
    """Read-only cluster status."""

    name: str
    namespace: str
    state: str  # ClusterState enum value
    head_ready: bool
    workers_ready: int
    workers_desired: int
    ray_version: str
    dashboard_url: Optional[str]
    age: timedelta
    conditions: list[dict[str, str]]


class JobStatus:
    """Read-only job status."""

    name: str
    namespace: str
    state: str  # JobState enum value
    mode: str  # "CRD" | "DASHBOARD"
    entrypoint: str
    submitted_at: datetime
    duration: Optional[timedelta]
    error_message: Optional[str]
    cluster_name: Optional[str]


class ServiceStatus:
    """Read-only service status."""

    name: str
    namespace: str
    state: str  # ServiceState enum value
    endpoint_url: Optional[str]
    route_url: Optional[str]
    replicas_ready: int
    replicas_desired: int
    age: timedelta


# ──────────────────────────────────────────────
# Resource handles
# ──────────────────────────────────────────────

class ClusterHandle:
    """Handle to a RayCluster. Returned by create/get operations."""

    def status(self) -> ClusterStatus:
        """Get current cluster status."""
        ...

    def scale(self, workers: int) -> None:
        """Scale worker count."""
        ...

    def delete(self, force: bool = False) -> None:
        """Delete the cluster. Warns if jobs running unless force=True."""
        ...

    def wait_until_ready(self, timeout: float = 300) -> None:
        """Block until cluster reaches RUNNING state."""
        ...

    def dashboard_url(self) -> str:
        """
        Get Ray Dashboard URL.

        Checks for OpenShift Route or Ingress first.
        Falls back to auto port-forward.

        Example:
            >>> url = cluster.dashboard_url()
            >>> print(f"Open dashboard: {url}")
        """
        ...

    def metrics(self) -> dict[str, Any]:
        """
        Get cluster-level resource metrics from Ray Dashboard.

        Returns:
            Dict with keys: cpu_utilization, gpu_utilization,
            memory_used, memory_total, active_tasks, available_resources.
        """
        ...

    def submit_job(
        self,
        entrypoint: str,
        *,
        runtime_env: Optional[Union[RuntimeEnv, dict]] = None,
        experiment_tracking: Optional[Union[ExperimentTracking, dict]] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> JobHandle:
        """
        Submit a job to this cluster via the Ray Dashboard API.

        Example:
            >>> job = cluster.submit_job(
            ...     entrypoint="python train.py",
            ...     runtime_env={"pip": ["torch"]},
            ... )
            >>> for line in job.logs(stream=True):
            ...     print(line)
        """
        ...

    def list_jobs(self) -> list[JobStatus]:
        """List all jobs submitted to this cluster via Dashboard."""
        ...


class JobHandle:
    """Handle to a Ray job. Returned by create/submit operations."""

    def status(self) -> JobStatus:
        """Get current job status."""
        ...

    def logs(
        self,
        *,
        stream: bool = False,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Union[str, Iterator[str]]:
        """
        Get job logs.

        Args:
            stream: If True, return an iterator yielding log lines.
            follow: If True (with stream=True), block until job completes.
            tail: Return only the last N lines.

        Example:
            >>> # Full logs
            >>> print(job.logs())
            >>>
            >>> # Stream in real-time
            >>> for line in job.logs(stream=True, follow=True):
            ...     print(line)
        """
        ...

    def stop(self) -> None:
        """Stop/cancel the running job."""
        ...

    def wait(self, timeout: float = 3600) -> JobStatus:
        """Block until job completes. Returns final status."""
        ...

    def progress(self) -> dict[str, Any]:
        """Get job progress from Ray Dashboard."""
        ...

    def download_artifacts(self, destination: str) -> None:
        """
        Download job artifacts to a local directory.

        Downloads via Ray Dashboard API or PVC copy.

        Args:
            destination: Local directory path.
        """
        ...


class ServiceHandle:
    """Handle to a RayService. Returned by create/get operations."""

    def status(self) -> ServiceStatus:
        """Get current service status."""
        ...

    def update(
        self,
        *,
        num_replicas: Optional[int] = None,
        import_path: Optional[str] = None,
        runtime_env: Optional[Union[RuntimeEnv, dict]] = None,
    ) -> None:
        """Update service configuration."""
        ...

    def delete(self) -> None:
        """Delete the service."""
        ...


# ──────────────────────────────────────────────
# Sync client
# ──────────────────────────────────────────────

class KubeRayClient:
    """
    Synchronous KubeRay SDK client. Main entry point.

    Example:
        >>> from kuberay_sdk import KubeRayClient
        >>> client = KubeRayClient()
        >>> cluster = client.create_cluster("my-cluster", workers=4)
        >>> cluster.wait_until_ready()
    """

    def __init__(self, config: Optional[SDKConfig] = None) -> None:
        """
        Initialize the client.

        Args:
            config: SDK configuration. If None, uses defaults
                    (auto auth, kubeconfig namespace).
        """
        ...

    # ── Cluster operations ──

    def create_cluster(
        self,
        name: str,
        *,
        namespace: Optional[str] = None,
        workers: int = 1,
        cpus_per_worker: float = 1.0,
        gpus_per_worker: int = 0,
        memory_per_worker: str = "2Gi",
        worker_groups: Optional[list[WorkerGroup]] = None,
        head: Optional[HeadNodeConfig] = None,
        ray_version: Optional[str] = None,
        image: Optional[str] = None,
        storage: Optional[list[StorageVolume]] = None,
        runtime_env: Optional[Union[RuntimeEnv, dict]] = None,
        labels: Optional[dict[str, str]] = None,
        annotations: Optional[dict[str, str]] = None,
        tolerations: Optional[list[dict]] = None,
        node_selector: Optional[dict[str, str]] = None,
        hardware_profile: Optional[str] = None,
        queue: Optional[str] = None,
        enable_autoscaling: bool = False,
        raw_overrides: Optional[dict] = None,
    ) -> ClusterHandle:
        """
        Create a RayCluster.

        Simple usage (flat params):
            >>> cluster = client.create_cluster("my-cluster", workers=4, gpus_per_worker=1)

        Advanced usage (worker groups):
            >>> cluster = client.create_cluster(
            ...     "my-cluster",
            ...     worker_groups=[
            ...         WorkerGroup(name="cpu", replicas=4, cpus=4),
            ...         WorkerGroup(name="gpu", replicas=2, gpus=1),
            ...     ],
            ... )
        """
        ...

    def get_cluster(
        self, name: str, *, namespace: Optional[str] = None
    ) -> ClusterHandle:
        """Get a handle to an existing cluster."""
        ...

    def list_clusters(
        self, *, namespace: Optional[str] = None
    ) -> list[ClusterStatus]:
        """List all RayClusters in the namespace."""
        ...

    # ── Job operations ──

    def create_job(
        self,
        name: str,
        *,
        entrypoint: str,
        namespace: Optional[str] = None,
        workers: int = 1,
        cpus_per_worker: float = 1.0,
        gpus_per_worker: int = 0,
        memory_per_worker: str = "2Gi",
        worker_groups: Optional[list[WorkerGroup]] = None,
        head: Optional[HeadNodeConfig] = None,
        ray_version: Optional[str] = None,
        image: Optional[str] = None,
        storage: Optional[list[StorageVolume]] = None,
        runtime_env: Optional[Union[RuntimeEnv, dict]] = None,
        shutdown_after_finish: bool = True,
        labels: Optional[dict[str, str]] = None,
        annotations: Optional[dict[str, str]] = None,
        queue: Optional[str] = None,
        hardware_profile: Optional[str] = None,
        experiment_tracking: Optional[Union[ExperimentTracking, dict]] = None,
        raw_overrides: Optional[dict] = None,
    ) -> JobHandle:
        """
        Create a RayJob CR (provisions its own disposable cluster).

        Example:
            >>> job = client.create_job(
            ...     "training",
            ...     entrypoint="python train.py",
            ...     workers=4,
            ...     gpus_per_worker=1,
            ... )
            >>> job.wait()
        """
        ...

    def get_job(
        self, name: str, *, namespace: Optional[str] = None
    ) -> JobHandle:
        """Get a handle to an existing RayJob CR."""
        ...

    def list_jobs(
        self, *, namespace: Optional[str] = None
    ) -> list[JobStatus]:
        """List all RayJob CRs in the namespace."""
        ...

    # ── Service operations ──

    def create_service(
        self,
        name: str,
        *,
        import_path: str,
        namespace: Optional[str] = None,
        num_replicas: int = 1,
        runtime_env: Optional[Union[RuntimeEnv, dict]] = None,
        ray_version: Optional[str] = None,
        image: Optional[str] = None,
        workers: int = 1,
        cpus_per_worker: float = 1.0,
        gpus_per_worker: int = 0,
        memory_per_worker: str = "2Gi",
        worker_groups: Optional[list[WorkerGroup]] = None,
        head: Optional[HeadNodeConfig] = None,
        storage: Optional[list[StorageVolume]] = None,
        labels: Optional[dict[str, str]] = None,
        annotations: Optional[dict[str, str]] = None,
        route_enabled: Optional[bool] = None,
        serve_config_v2: Optional[str] = None,
        raw_overrides: Optional[dict] = None,
    ) -> ServiceHandle:
        """
        Create a RayService CR.

        Example:
            >>> service = client.create_service(
            ...     "my-llm",
            ...     import_path="serve_app:deployment",
            ...     num_replicas=2,
            ...     gpus_per_worker=1,
            ... )
        """
        ...

    def get_service(
        self, name: str, *, namespace: Optional[str] = None
    ) -> ServiceHandle:
        """Get a handle to an existing RayService."""
        ...

    def list_services(
        self, *, namespace: Optional[str] = None
    ) -> list[ServiceStatus]:
        """List all RayServices in the namespace."""
        ...


# ──────────────────────────────────────────────
# Async client
# ──────────────────────────────────────────────

class AsyncKubeRayClient:
    """
    Asynchronous KubeRay SDK client. Mirrors KubeRayClient with async/await.

    Example:
        >>> import asyncio
        >>> from kuberay_sdk import AsyncKubeRayClient
        >>>
        >>> async def main():
        ...     client = AsyncKubeRayClient()
        ...     cluster = await client.create_cluster("my-cluster", workers=4)
        ...     await cluster.wait_until_ready()
        >>>
        >>> asyncio.run(main())
    """

    def __init__(self, config: Optional[SDKConfig] = None) -> None: ...

    # All methods mirror KubeRayClient but return coroutines.
    # Signatures are identical except for async def and awaitable returns.

    # ── Cluster operations ──

    async def create_cluster(
        self,
        name: str,
        *,
        namespace: Optional[str] = None,
        workers: int = 1,
        cpus_per_worker: float = 1.0,
        gpus_per_worker: int = 0,
        memory_per_worker: str = "2Gi",
        worker_groups: Optional[list[WorkerGroup]] = None,
        head: Optional[HeadNodeConfig] = None,
        ray_version: Optional[str] = None,
        image: Optional[str] = None,
        storage: Optional[list[StorageVolume]] = None,
        runtime_env: Optional[Union[RuntimeEnv, dict]] = None,
        labels: Optional[dict[str, str]] = None,
        annotations: Optional[dict[str, str]] = None,
        tolerations: Optional[list[dict]] = None,
        node_selector: Optional[dict[str, str]] = None,
        hardware_profile: Optional[str] = None,
        queue: Optional[str] = None,
        enable_autoscaling: bool = False,
        raw_overrides: Optional[dict] = None,
    ) -> ClusterHandle: ...

    async def get_cluster(
        self, name: str, *, namespace: Optional[str] = None
    ) -> ClusterHandle: ...

    async def list_clusters(
        self, *, namespace: Optional[str] = None
    ) -> list[ClusterStatus]: ...

    # ── Job operations ──

    async def create_job(
        self,
        name: str,
        *,
        entrypoint: str,
        namespace: Optional[str] = None,
        workers: int = 1,
        cpus_per_worker: float = 1.0,
        gpus_per_worker: int = 0,
        memory_per_worker: str = "2Gi",
        worker_groups: Optional[list[WorkerGroup]] = None,
        head: Optional[HeadNodeConfig] = None,
        ray_version: Optional[str] = None,
        image: Optional[str] = None,
        storage: Optional[list[StorageVolume]] = None,
        runtime_env: Optional[Union[RuntimeEnv, dict]] = None,
        shutdown_after_finish: bool = True,
        labels: Optional[dict[str, str]] = None,
        annotations: Optional[dict[str, str]] = None,
        queue: Optional[str] = None,
        hardware_profile: Optional[str] = None,
        experiment_tracking: Optional[Union[ExperimentTracking, dict]] = None,
        raw_overrides: Optional[dict] = None,
    ) -> JobHandle: ...

    async def get_job(
        self, name: str, *, namespace: Optional[str] = None
    ) -> JobHandle: ...

    async def list_jobs(
        self, *, namespace: Optional[str] = None
    ) -> list[JobStatus]: ...

    # ── Service operations ──

    async def create_service(
        self,
        name: str,
        *,
        import_path: str,
        namespace: Optional[str] = None,
        num_replicas: int = 1,
        runtime_env: Optional[Union[RuntimeEnv, dict]] = None,
        ray_version: Optional[str] = None,
        image: Optional[str] = None,
        workers: int = 1,
        cpus_per_worker: float = 1.0,
        gpus_per_worker: int = 0,
        memory_per_worker: str = "2Gi",
        worker_groups: Optional[list[WorkerGroup]] = None,
        head: Optional[HeadNodeConfig] = None,
        storage: Optional[list[StorageVolume]] = None,
        labels: Optional[dict[str, str]] = None,
        annotations: Optional[dict[str, str]] = None,
        route_enabled: Optional[bool] = None,
        serve_config_v2: Optional[str] = None,
        raw_overrides: Optional[dict] = None,
    ) -> ServiceHandle: ...

    async def get_service(
        self, name: str, *, namespace: Optional[str] = None
    ) -> ServiceHandle: ...

    async def list_services(
        self, *, namespace: Optional[str] = None
    ) -> list[ServiceStatus]: ...


# ──────────────────────────────────────────────
# Errors
# ──────────────────────────────────────────────

class KubeRayError(Exception):
    """Base exception for all SDK errors."""
    ...

class ClusterError(KubeRayError):
    """Cluster operation failed."""
    ...

class ClusterNotFoundError(ClusterError):
    """Cluster does not exist."""
    ...

class ClusterAlreadyExistsError(ClusterError):
    """Cluster exists with a different configuration."""
    ...

class JobError(KubeRayError):
    """Job operation failed."""
    ...

class JobNotFoundError(JobError):
    """Job does not exist."""
    ...

class ServiceError(KubeRayError):
    """Service operation failed."""
    ...

class DashboardUnreachableError(KubeRayError):
    """Ray Dashboard is not accessible."""
    ...

class KubeRayOperatorNotFoundError(KubeRayError):
    """KubeRay operator CRDs are not installed on the cluster."""
    ...

class AuthenticationError(KubeRayError):
    """Authentication failed or credentials expired."""
    ...

class ValidationError(KubeRayError):
    """Input validation failed (e.g., invalid runtime_env)."""
    ...

class ResourceConflictError(KubeRayError):
    """Resource exists with different configuration."""
    ...

class TimeoutError(KubeRayError):
    """Operation timed out (e.g., wait_until_ready)."""
    ...
