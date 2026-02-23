"""KubeRayClient — synchronous SDK entry point (FR-039).

Example:
    >>> from kuberay_sdk import KubeRayClient
    >>> client = KubeRayClient()
    >>> cluster = client.create_cluster("my-cluster", workers=4)
    >>> cluster.wait_until_ready()
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from kuberay_sdk.config import SDKConfig, check_kuberay_crds, get_k8s_client, resolve_namespace
from kuberay_sdk.errors import KubeRayError

if TYPE_CHECKING:

    from kuberay_sdk.models.cluster import ClusterStatus, HeadNodeConfig, WorkerGroup
    from kuberay_sdk.models.runtime_env import ExperimentTracking, RuntimeEnv
    from kuberay_sdk.models.service import ServiceStatus
    from kuberay_sdk.models.storage import StorageVolume

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Resource handles
# ──────────────────────────────────────────────


class ClusterHandle:
    """Handle to a RayCluster. Returned by create/get operations.

    Example:
        >>> cluster = client.create_cluster("my-cluster", workers=4)
        >>> cluster.wait_until_ready()
        >>> print(cluster.status())
    """

    def __init__(
        self,
        name: str,
        namespace: str,
        client: KubeRayClient,
    ) -> None:
        self._name = name
        self._namespace = namespace
        self._client = client

    @property
    def name(self) -> str:
        return self._name

    @property
    def namespace(self) -> str:
        return self._namespace

    def status(self) -> ClusterStatus:
        """Get current cluster status.

        Example:
            >>> status = cluster.status()
            >>> print(status.state, status.workers_ready)
        """
        from kuberay_sdk.services.cluster_service import ClusterService

        svc = ClusterService(self._client._custom_api, self._client._config)
        return svc.get_status(self._name, self._namespace)

    def scale(self, workers: int) -> None:
        """Scale worker count.

        Example:
            >>> cluster.scale(workers=8)
        """
        from kuberay_sdk.services.cluster_service import ClusterService

        svc = ClusterService(self._client._custom_api, self._client._config)
        svc.scale(self._name, self._namespace, workers)

    def delete(self, force: bool = False) -> None:
        """Delete the cluster. Warns if jobs running unless force=True.

        Example:
            >>> cluster.delete()
        """
        from kuberay_sdk.services.cluster_service import ClusterService

        svc = ClusterService(self._client._custom_api, self._client._config)
        svc.delete(self._name, self._namespace, force=force)

    def wait_until_ready(self, timeout: float = 300) -> None:
        """Block until cluster reaches RUNNING state.

        Example:
            >>> cluster.wait_until_ready(timeout=300)
        """
        from kuberay_sdk.services.cluster_service import ClusterService

        svc = ClusterService(self._client._custom_api, self._client._config)
        svc.wait_until_ready(self._name, self._namespace, timeout=timeout)

    def dashboard_url(self) -> str:
        """Get Ray Dashboard URL.

        Checks for OpenShift Route or Ingress first.
        Falls back to auto port-forward.

        Example:
            >>> url = cluster.dashboard_url()
            >>> print(f"Open dashboard: {url}")
        """
        from kuberay_sdk.services.port_forward import PortForwardManager

        pfm = PortForwardManager(self._client._api_client)
        return pfm.get_dashboard_url(self._name, self._namespace)

    def metrics(self) -> dict[str, Any]:
        """Get cluster-level resource metrics from Ray Dashboard.

        Returns:
            Dict with keys: cpu_utilization, gpu_utilization,
            memory_used, memory_total, active_tasks, available_resources.

        Example:
            >>> metrics = cluster.metrics()
            >>> print(f"CPU: {metrics['cpu_utilization']}%")
        """
        from kuberay_sdk.services.dashboard import DashboardClient

        url = self.dashboard_url()
        dc = DashboardClient(url)
        return dc.get_cluster_metrics()

    def submit_job(
        self,
        entrypoint: str,
        *,
        runtime_env: RuntimeEnv | dict | None = None,  # type: ignore[type-arg]
        experiment_tracking: ExperimentTracking | dict | None = None,  # type: ignore[type-arg]
        metadata: dict[str, str] | None = None,
    ) -> JobHandle:
        """Submit a job to this cluster via the Ray Dashboard API.

        Example:
            >>> job = cluster.submit_job(
            ...     entrypoint="python train.py",
            ...     runtime_env={"pip": ["torch"]},
            ... )
            >>> for line in job.logs(stream=True):
            ...     print(line)
        """
        from kuberay_sdk.services.dashboard import DashboardClient
        from kuberay_sdk.services.job_service import JobService

        job_svc = JobService(self._client._custom_api, self._client._config)
        url = self.dashboard_url()
        dc = DashboardClient(url)
        job_id = job_svc.submit_to_dashboard(
            dc,
            entrypoint=entrypoint,
            runtime_env=runtime_env,
            experiment_tracking=experiment_tracking,
            metadata=metadata,
        )
        return JobHandle(
            name=job_id,
            namespace=self._namespace,
            client=self._client,
            mode="DASHBOARD",
            dashboard_url=url,
            cluster_name=self._name,
        )

    def list_jobs(self) -> list[Any]:
        """List all jobs submitted to this cluster via Dashboard.

        Example:
            >>> jobs = cluster.list_jobs()
        """
        from kuberay_sdk.services.dashboard import DashboardClient

        url = self.dashboard_url()
        dc = DashboardClient(url)
        return dc.list_jobs()


class JobHandle:
    """Handle to a Ray job. Returned by create/submit operations.

    Example:
        >>> job = client.create_job("training", entrypoint="python train.py")
        >>> job.wait()
    """

    def __init__(
        self,
        name: str,
        namespace: str,
        client: KubeRayClient,
        mode: str = "CRD",
        dashboard_url: str | None = None,
        cluster_name: str | None = None,
    ) -> None:
        self._name = name
        self._namespace = namespace
        self._client = client
        self._mode = mode
        self._dashboard_url = dashboard_url
        self._cluster_name = cluster_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def namespace(self) -> str:
        return self._namespace

    def status(self) -> Any:
        """Get current job status.

        Example:
            >>> status = job.status()
            >>> print(status.state)
        """
        from kuberay_sdk.services.job_service import JobService

        svc = JobService(self._client._custom_api, self._client._config)
        if self._mode == "DASHBOARD" and self._dashboard_url:
            from kuberay_sdk.services.dashboard import DashboardClient

            dc = DashboardClient(self._dashboard_url)
            return svc.get_dashboard_job_status(dc, self._name)
        return svc.get_status(self._name, self._namespace)

    def logs(
        self,
        *,
        stream: bool = False,
        follow: bool = False,
        tail: int | None = None,
    ) -> str | Iterator[str]:
        """Get job logs.

        Example:
            >>> # Full logs
            >>> print(job.logs())
            >>> # Stream in real-time
            >>> for line in job.logs(stream=True, follow=True):
            ...     print(line)
        """
        from kuberay_sdk.services.dashboard import DashboardClient

        url = self._dashboard_url or self._get_dashboard_url()
        dc = DashboardClient(url)
        if stream:
            return dc.stream_logs(self._name, follow=follow)
        return dc.get_logs(self._name, tail=tail)

    def stop(self) -> None:
        """Stop/cancel the running job.

        Example:
            >>> job.stop()
        """
        from kuberay_sdk.services.job_service import JobService

        svc = JobService(self._client._custom_api, self._client._config)
        if self._mode == "DASHBOARD" and self._dashboard_url:
            from kuberay_sdk.services.dashboard import DashboardClient

            dc = DashboardClient(self._dashboard_url)
            dc.stop_job(self._name)
        else:
            svc.stop(self._name, self._namespace)

    def wait(self, timeout: float = 3600) -> Any:
        """Block until job completes. Returns final status.

        Example:
            >>> job.wait(timeout=3600)
        """
        from kuberay_sdk.services.job_service import JobService

        svc = JobService(self._client._custom_api, self._client._config)
        if self._mode == "DASHBOARD" and self._dashboard_url:
            from kuberay_sdk.services.dashboard import DashboardClient

            dc = DashboardClient(self._dashboard_url)
            return svc.wait_dashboard_job(dc, self._name, timeout=timeout)
        return svc.wait(self._name, self._namespace, timeout=timeout)

    def progress(self) -> dict[str, Any]:
        """Get job progress from Ray Dashboard.

        Example:
            >>> progress = job.progress()
        """
        from kuberay_sdk.services.dashboard import DashboardClient

        url = self._dashboard_url or self._get_dashboard_url()
        dc = DashboardClient(url)
        return dc.get_job_progress(self._name)

    def download_artifacts(self, destination: str) -> None:
        """Download job artifacts to a local directory.

        Example:
            >>> job.download_artifacts("./output")
        """
        from kuberay_sdk.services.dashboard import DashboardClient

        url = self._dashboard_url or self._get_dashboard_url()
        dc = DashboardClient(url)
        dc.download_artifacts(self._name, destination)

    def _get_dashboard_url(self) -> str:
        if self._cluster_name:
            from kuberay_sdk.services.port_forward import PortForwardManager

            pfm = PortForwardManager(self._client._api_client)
            return pfm.get_dashboard_url(self._cluster_name, self._namespace)
        raise KubeRayError("Cannot determine dashboard URL without a cluster name.")


class ServiceHandle:
    """Handle to a RayService. Returned by create/get operations.

    Example:
        >>> service = client.create_service("my-llm", import_path="serve_app:deployment")
        >>> print(service.status())
    """

    def __init__(
        self,
        name: str,
        namespace: str,
        client: KubeRayClient,
    ) -> None:
        self._name = name
        self._namespace = namespace
        self._client = client

    @property
    def name(self) -> str:
        return self._name

    @property
    def namespace(self) -> str:
        return self._namespace

    def status(self) -> ServiceStatus:
        """Get current service status.

        Example:
            >>> status = service.status()
            >>> print(status.state, status.endpoint_url)
        """
        from kuberay_sdk.services.service_service import ServiceService

        svc = ServiceService(self._client._custom_api, self._client._config)
        return svc.get_status(self._name, self._namespace)

    def update(
        self,
        *,
        num_replicas: int | None = None,
        import_path: str | None = None,
        runtime_env: RuntimeEnv | dict | None = None,  # type: ignore[type-arg]
    ) -> None:
        """Update service configuration.

        Example:
            >>> service.update(num_replicas=4)
        """
        from kuberay_sdk.services.service_service import ServiceService

        svc = ServiceService(self._client._custom_api, self._client._config)
        svc.update(
            self._name,
            self._namespace,
            num_replicas=num_replicas,
            import_path=import_path,
            runtime_env=runtime_env,
        )

    def delete(self) -> None:
        """Delete the service.

        Example:
            >>> service.delete()
        """
        from kuberay_sdk.services.service_service import ServiceService

        svc = ServiceService(self._client._custom_api, self._client._config)
        svc.delete(self._name, self._namespace)


# ──────────────────────────────────────────────
# Main client
# ──────────────────────────────────────────────


class KubeRayClient:
    """Synchronous KubeRay SDK client. Main entry point.

    Example:
        >>> from kuberay_sdk import KubeRayClient
        >>> client = KubeRayClient()
        >>> cluster = client.create_cluster("my-cluster", workers=4)
        >>> cluster.wait_until_ready()
    """

    def __init__(self, config: SDKConfig | None = None) -> None:
        self._config = config or SDKConfig()
        self._api_client = get_k8s_client(self._config.auth)

        from kubernetes.client import CustomObjectsApi

        self._custom_api = CustomObjectsApi(self._api_client)

        # Check KubeRay CRDs on first init (FR-038, SC-008)
        check_kuberay_crds(self._api_client)

    # ── Cluster operations ──

    def create_cluster(
        self,
        name: str,
        *,
        namespace: str | None = None,
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
    ) -> ClusterHandle:
        """Create a RayCluster.

        Example:
            >>> cluster = client.create_cluster("my-cluster", workers=4, gpus_per_worker=1)
        """
        from kuberay_sdk.services.cluster_service import ClusterService

        ns = resolve_namespace(self._config, namespace)
        svc = ClusterService(self._custom_api, self._config)
        svc.create(
            name=name,
            namespace=ns,
            workers=workers,
            cpus_per_worker=cpus_per_worker,
            gpus_per_worker=gpus_per_worker,
            memory_per_worker=memory_per_worker,
            worker_groups=worker_groups,
            head=head,
            ray_version=ray_version,
            image=image,
            storage=storage,
            runtime_env=runtime_env,
            labels=labels,
            annotations=annotations,
            tolerations=tolerations,
            node_selector=node_selector,
            hardware_profile=hardware_profile,
            queue=queue,
            enable_autoscaling=enable_autoscaling,
            raw_overrides=raw_overrides,
        )
        return ClusterHandle(name, ns, self)

    def get_cluster(self, name: str, *, namespace: str | None = None) -> ClusterHandle:
        """Get a handle to an existing cluster.

        Example:
            >>> cluster = client.get_cluster("my-cluster")
        """
        ns = resolve_namespace(self._config, namespace)
        # Verify cluster exists
        from kuberay_sdk.services.cluster_service import ClusterService

        svc = ClusterService(self._custom_api, self._config)
        svc.get_status(name, ns)
        return ClusterHandle(name, ns, self)

    def list_clusters(self, *, namespace: str | None = None) -> list[ClusterStatus]:
        """List all RayClusters in the namespace.

        Example:
            >>> clusters = client.list_clusters()
        """
        from kuberay_sdk.services.cluster_service import ClusterService

        ns = resolve_namespace(self._config, namespace)
        svc = ClusterService(self._custom_api, self._config)
        return svc.list(ns)

    # ── Job operations ──

    def create_job(
        self,
        name: str,
        *,
        entrypoint: str,
        namespace: str | None = None,
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
    ) -> JobHandle:
        """Create a RayJob CR (provisions its own disposable cluster).

        Example:
            >>> job = client.create_job(
            ...     "training",
            ...     entrypoint="python train.py",
            ...     workers=4,
            ...     gpus_per_worker=1,
            ... )
            >>> job.wait()
        """
        from kuberay_sdk.services.job_service import JobService

        ns = resolve_namespace(self._config, namespace)
        svc = JobService(self._custom_api, self._config)
        svc.create(
            name=name,
            namespace=ns,
            entrypoint=entrypoint,
            workers=workers,
            cpus_per_worker=cpus_per_worker,
            gpus_per_worker=gpus_per_worker,
            memory_per_worker=memory_per_worker,
            worker_groups=worker_groups,
            head=head,
            ray_version=ray_version,
            image=image,
            storage=storage,
            runtime_env=runtime_env,
            shutdown_after_finish=shutdown_after_finish,
            labels=labels,
            annotations=annotations,
            queue=queue,
            hardware_profile=hardware_profile,
            experiment_tracking=experiment_tracking,
            raw_overrides=raw_overrides,
        )
        return JobHandle(name, ns, self, mode="CRD")

    def get_job(self, name: str, *, namespace: str | None = None) -> JobHandle:
        """Get a handle to an existing RayJob CR.

        Example:
            >>> job = client.get_job("my-job")
        """
        ns = resolve_namespace(self._config, namespace)
        from kuberay_sdk.services.job_service import JobService

        svc = JobService(self._custom_api, self._config)
        svc.get_status(name, ns)
        return JobHandle(name, ns, self, mode="CRD")

    def list_jobs(self, *, namespace: str | None = None) -> list[Any]:
        """List all RayJob CRs in the namespace.

        Example:
            >>> jobs = client.list_jobs()
        """
        from kuberay_sdk.services.job_service import JobService

        ns = resolve_namespace(self._config, namespace)
        svc = JobService(self._custom_api, self._config)
        return svc.list(ns)

    # ── Service operations ──

    def create_service(
        self,
        name: str,
        *,
        import_path: str,
        namespace: str | None = None,
        num_replicas: int = 1,
        runtime_env: RuntimeEnv | dict | None = None,  # type: ignore[type-arg]
        ray_version: str | None = None,
        image: str | None = None,
        workers: int = 1,
        cpus_per_worker: float = 1.0,
        gpus_per_worker: int = 0,
        memory_per_worker: str = "2Gi",
        worker_groups: list[WorkerGroup] | None = None,
        head: HeadNodeConfig | None = None,
        storage: list[StorageVolume] | None = None,
        labels: dict[str, str] | None = None,
        annotations: dict[str, str] | None = None,
        route_enabled: bool | None = None,
        serve_config_v2: str | None = None,
        raw_overrides: dict | None = None,  # type: ignore[type-arg]
    ) -> ServiceHandle:
        """Create a RayService CR.

        Example:
            >>> service = client.create_service(
            ...     "my-llm",
            ...     import_path="serve_app:deployment",
            ...     num_replicas=2,
            ...     gpus_per_worker=1,
            ... )
        """
        from kuberay_sdk.services.service_service import ServiceService

        ns = resolve_namespace(self._config, namespace)
        svc = ServiceService(self._custom_api, self._config)
        svc.create(
            name=name,
            namespace=ns,
            import_path=import_path,
            num_replicas=num_replicas,
            runtime_env=runtime_env,
            ray_version=ray_version,
            image=image,
            workers=workers,
            cpus_per_worker=cpus_per_worker,
            gpus_per_worker=gpus_per_worker,
            memory_per_worker=memory_per_worker,
            worker_groups=worker_groups,
            head=head,
            storage=storage,
            labels=labels,
            annotations=annotations,
            route_enabled=route_enabled,
            serve_config_v2=serve_config_v2,
            raw_overrides=raw_overrides,
        )
        return ServiceHandle(name, ns, self)

    def get_service(self, name: str, *, namespace: str | None = None) -> ServiceHandle:
        """Get a handle to an existing RayService.

        Example:
            >>> service = client.get_service("my-llm")
        """
        ns = resolve_namespace(self._config, namespace)
        from kuberay_sdk.services.service_service import ServiceService

        svc = ServiceService(self._custom_api, self._config)
        svc.get_status(name, ns)
        return ServiceHandle(name, ns, self)

    def list_services(self, *, namespace: str | None = None) -> list[ServiceStatus]:
        """List all RayServices in the namespace.

        Example:
            >>> services = client.list_services()
        """
        from kuberay_sdk.services.service_service import ServiceService

        ns = resolve_namespace(self._config, namespace)
        svc = ServiceService(self._custom_api, self._config)
        return svc.list(ns)
