"""AsyncKubeRayClient — asynchronous SDK entry point (FR-040, FR-041).

Mirrors all KubeRayClient methods with async/await syntax.

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

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import TYPE_CHECKING, Any

from kuberay_sdk.config import SDKConfig, check_kuberay_crds, get_k8s_client, resolve_config, resolve_namespace

if TYPE_CHECKING:
    from kuberay_sdk.models.capabilities import ClusterCapabilities
    from kuberay_sdk.models.cluster import ClusterStatus, HeadNodeConfig, WorkerGroup
    from kuberay_sdk.models.runtime_env import ExperimentTracking, RuntimeEnv
    from kuberay_sdk.models.service import ServiceStatus
    from kuberay_sdk.models.storage import StorageVolume

logger = logging.getLogger(__name__)

# Thread pool for blocking K8s operations
_executor = ThreadPoolExecutor(max_workers=4)


async def _run_sync(func: Any, *args: Any, **kwargs: Any) -> Any:
    """Run a synchronous function in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, partial(func, *args, **kwargs))


# ──────────────────────────────────────────────
# Async resource handles
# ──────────────────────────────────────────────


class AsyncClusterHandle:
    """Async handle to a RayCluster."""

    def __init__(self, name: str, namespace: str, client: AsyncKubeRayClient) -> None:
        self._name = name
        self._namespace = namespace
        self._client = client

    def __repr__(self) -> str:
        return f"AsyncClusterHandle(name={self._name!r}, namespace={self._namespace!r})"

    @property
    def name(self) -> str:
        return self._name

    @property
    def namespace(self) -> str:
        return self._namespace

    async def status(self) -> ClusterStatus:
        """Get current cluster status."""
        from kuberay_sdk.services.cluster_service import ClusterService

        svc = ClusterService(self._client._custom_api, self._client._config)
        return await _run_sync(svc.get_status, self._name, self._namespace)

    async def scale(self, workers: int) -> None:
        """Scale worker count."""
        from kuberay_sdk.services.cluster_service import ClusterService

        svc = ClusterService(self._client._custom_api, self._client._config)
        await _run_sync(svc.scale, self._name, self._namespace, workers)

    async def delete(self, force: bool = False) -> None:
        """Delete the cluster."""
        from kuberay_sdk.services.cluster_service import ClusterService

        svc = ClusterService(self._client._custom_api, self._client._config)
        await _run_sync(svc.delete, self._name, self._namespace, force)

    async def wait_until_ready(self, timeout: float = 300, progress_callback: Any = None) -> None:
        """Block until cluster reaches RUNNING state.

        Args:
            timeout: Maximum seconds to wait.
            progress_callback: Optional callable invoked each poll cycle with
                a ``ProgressStatus`` object.
        """
        from kuberay_sdk.services.cluster_service import ClusterService

        svc = ClusterService(self._client._custom_api, self._client._config)
        await _run_sync(
            svc.wait_until_ready,
            self._name,
            self._namespace,
            timeout,
            progress_callback=progress_callback,
        )

    async def dashboard_url(self) -> str:
        """Get Ray Dashboard URL."""
        from kuberay_sdk.services.port_forward import PortForwardManager

        pfm = PortForwardManager(self._client._api_client)
        return await _run_sync(pfm.get_dashboard_url, self._name, self._namespace)

    async def metrics(self) -> dict[str, Any]:
        """Get cluster-level resource metrics."""
        from kuberay_sdk.services.dashboard import DashboardClient

        url = await self.dashboard_url()
        dc = DashboardClient(url)
        return await _run_sync(dc.get_cluster_metrics)

    async def submit_job(
        self,
        entrypoint: str,
        *,
        runtime_env: RuntimeEnv | dict | None = None,  # type: ignore[type-arg]
        experiment_tracking: ExperimentTracking | dict | None = None,  # type: ignore[type-arg]
        metadata: dict[str, str] | None = None,
    ) -> AsyncJobHandle:
        """Submit a job to this cluster via the Ray Dashboard API."""
        from kuberay_sdk.services.dashboard import DashboardClient
        from kuberay_sdk.services.job_service import JobService

        job_svc = JobService(self._client._custom_api, self._client._config)
        url = await self.dashboard_url()
        dc = DashboardClient(url)
        job_id = await _run_sync(
            job_svc.submit_to_dashboard,
            dc,
            entrypoint=entrypoint,
            runtime_env=runtime_env,
            experiment_tracking=experiment_tracking,
            metadata=metadata,
        )
        return AsyncJobHandle(
            name=job_id,
            namespace=self._namespace,
            client=self._client,
            mode="DASHBOARD",
            dashboard_url=url,
            cluster_name=self._name,
        )

    async def list_jobs(self) -> list[Any]:
        """List all jobs submitted to this cluster via Dashboard."""
        from kuberay_sdk.services.dashboard import DashboardClient

        url = await self.dashboard_url()
        dc = DashboardClient(url)
        return await _run_sync(dc.list_jobs)


class AsyncJobHandle:
    """Async handle to a Ray job."""

    def __init__(
        self,
        name: str,
        namespace: str,
        client: AsyncKubeRayClient,
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

    def __repr__(self) -> str:
        return f"AsyncJobHandle(name={self._name!r}, namespace={self._namespace!r}, mode={self._mode!r})"

    @property
    def name(self) -> str:
        return self._name

    @property
    def namespace(self) -> str:
        return self._namespace

    async def status(self) -> Any:
        """Get current job status."""
        from kuberay_sdk.services.job_service import JobService

        svc = JobService(self._client._custom_api, self._client._config)
        if self._mode == "DASHBOARD" and self._dashboard_url:
            from kuberay_sdk.services.dashboard import DashboardClient

            dc = DashboardClient(self._dashboard_url)
            return await _run_sync(svc.get_dashboard_job_status, dc, self._name)
        return await _run_sync(svc.get_status, self._name, self._namespace)

    async def logs(
        self,
        *,
        stream: bool = False,
        follow: bool = False,
        tail: int | None = None,
    ) -> Any:
        """Get job logs."""
        from kuberay_sdk.services.dashboard import DashboardClient

        url = self._dashboard_url or await self._get_dashboard_url()
        dc = DashboardClient(url)
        if stream:
            return await _run_sync(dc.stream_logs, self._name, follow)
        return await _run_sync(dc.get_logs, self._name, tail)

    async def stop(self) -> None:
        """Stop/cancel the running job."""
        from kuberay_sdk.services.job_service import JobService

        svc = JobService(self._client._custom_api, self._client._config)
        if self._mode == "DASHBOARD" and self._dashboard_url:
            from kuberay_sdk.services.dashboard import DashboardClient

            dc = DashboardClient(self._dashboard_url)
            await _run_sync(dc.stop_job, self._name)
        else:
            await _run_sync(svc.stop, self._name, self._namespace)

    async def wait(self, timeout: float = 3600, progress_callback: Any = None) -> Any:
        """Block until job completes. Returns final status.

        Args:
            timeout: Maximum seconds to wait.
            progress_callback: Optional callable invoked each poll cycle with
                a ``ProgressStatus`` object.
        """
        from kuberay_sdk.services.job_service import JobService

        svc = JobService(self._client._custom_api, self._client._config)
        if self._mode == "DASHBOARD" and self._dashboard_url:
            from kuberay_sdk.services.dashboard import DashboardClient

            dc = DashboardClient(self._dashboard_url)
            return await _run_sync(
                svc.wait_dashboard_job,
                dc,
                self._name,
                timeout,
                progress_callback=progress_callback,
            )
        return await _run_sync(
            svc.wait,
            self._name,
            self._namespace,
            timeout,
            progress_callback=progress_callback,
        )

    async def progress(self) -> dict[str, Any]:
        """Get job progress from Ray Dashboard."""
        from kuberay_sdk.services.dashboard import DashboardClient

        url = self._dashboard_url or await self._get_dashboard_url()
        dc = DashboardClient(url)
        return await _run_sync(dc.get_job_progress, self._name)

    async def download_artifacts(self, destination: str) -> None:
        """Download job artifacts to a local directory."""
        from kuberay_sdk.services.dashboard import DashboardClient

        url = self._dashboard_url or await self._get_dashboard_url()
        dc = DashboardClient(url)
        await _run_sync(dc.download_artifacts, self._name, destination)

    async def _get_dashboard_url(self) -> str:
        if self._cluster_name:
            from kuberay_sdk.services.port_forward import PortForwardManager

            pfm = PortForwardManager(self._client._api_client)
            return await _run_sync(pfm.get_dashboard_url, self._cluster_name, self._namespace)
        from kuberay_sdk.errors import KubeRayError

        raise KubeRayError("Cannot determine dashboard URL without a cluster name.")


class AsyncServiceHandle:
    """Async handle to a RayService."""

    def __init__(self, name: str, namespace: str, client: AsyncKubeRayClient) -> None:
        self._name = name
        self._namespace = namespace
        self._client = client

    def __repr__(self) -> str:
        return f"AsyncServiceHandle(name={self._name!r}, namespace={self._namespace!r})"

    @property
    def name(self) -> str:
        return self._name

    @property
    def namespace(self) -> str:
        return self._namespace

    async def status(self) -> ServiceStatus:
        """Get current service status."""
        from kuberay_sdk.services.service_service import ServiceService

        svc = ServiceService(self._client._custom_api, self._client._config)
        return await _run_sync(svc.get_status, self._name, self._namespace)

    async def update(
        self,
        *,
        num_replicas: int | None = None,
        import_path: str | None = None,
        runtime_env: RuntimeEnv | dict | None = None,  # type: ignore[type-arg]
    ) -> None:
        """Update service configuration."""
        from kuberay_sdk.services.service_service import ServiceService

        svc = ServiceService(self._client._custom_api, self._client._config)
        await _run_sync(
            svc.update,
            self._name,
            self._namespace,
            num_replicas=num_replicas,
            import_path=import_path,
            runtime_env=runtime_env,
        )

    async def delete(self) -> None:
        """Delete the service."""
        from kuberay_sdk.services.service_service import ServiceService

        svc = ServiceService(self._client._custom_api, self._client._config)
        await _run_sync(svc.delete, self._name, self._namespace)


# ──────────────────────────────────────────────
# Async client
# ──────────────────────────────────────────────


class AsyncKubeRayClient:
    """Asynchronous KubeRay SDK client. Mirrors KubeRayClient with async/await.

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

    def __init__(self, config: SDKConfig | None = None) -> None:
        self._config = resolve_config(config)
        self._api_client = get_k8s_client(self._config.auth)
        from kubernetes.client import CustomObjectsApi

        self._custom_api = CustomObjectsApi(self._api_client)
        check_kuberay_crds(self._api_client)

    # ── Cluster operations ──

    async def create_cluster(
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
        preset: str | Any | None = None,
        dry_run: bool = False,
    ) -> AsyncClusterHandle | Any:
        """Create a RayCluster."""
        # Resolve preset defaults
        if preset is not None:
            from kuberay_sdk.presets import get_preset

            resolved_preset = get_preset(preset) if isinstance(preset, str) else preset
            if workers == 1:  # default
                workers = resolved_preset.workers
            if cpus_per_worker == 1.0:  # default
                cpus_per_worker = float(resolved_preset.worker_cpu)
            if gpus_per_worker == 0:  # default
                gpus_per_worker = resolved_preset.worker_gpu
            if memory_per_worker == "2Gi":  # default
                memory_per_worker = resolved_preset.worker_memory
            if head is None:
                from kuberay_sdk.models.cluster import HeadNodeConfig as _HeadNodeConfig

                head = _HeadNodeConfig(
                    cpus=float(resolved_preset.head_cpu),
                    memory=resolved_preset.head_memory,
                )
            if ray_version is None:
                ray_version = resolved_preset.ray_version

        ns = resolve_namespace(self._config, namespace)

        if dry_run:
            from kuberay_sdk.models.cluster import ClusterConfig
            from kuberay_sdk.models.common import DryRunResult

            config_model = ClusterConfig(
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
            return DryRunResult(config_model.to_crd_dict(), "RayCluster")

        from kuberay_sdk.services.cluster_service import ClusterService

        svc = ClusterService(self._custom_api, self._config)
        await _run_sync(
            svc.create,
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
        return AsyncClusterHandle(name, ns, self)

    async def get_cluster(self, name: str, *, namespace: str | None = None) -> AsyncClusterHandle:
        """Get a handle to an existing cluster."""
        from kuberay_sdk.services.cluster_service import ClusterService

        ns = resolve_namespace(self._config, namespace)
        svc = ClusterService(self._custom_api, self._config)
        await _run_sync(svc.get_status, name, ns)
        return AsyncClusterHandle(name, ns, self)

    async def list_clusters(self, *, namespace: str | None = None) -> list[ClusterStatus]:
        """List all RayClusters in the namespace."""
        from kuberay_sdk.services.cluster_service import ClusterService

        ns = resolve_namespace(self._config, namespace)
        svc = ClusterService(self._custom_api, self._config)
        return await _run_sync(svc.list, ns)

    # ── Job operations ──

    async def create_job(
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
        dry_run: bool = False,
    ) -> AsyncJobHandle | Any:
        """Create a RayJob CR."""
        ns = resolve_namespace(self._config, namespace)

        if dry_run:
            from kuberay_sdk.models.common import DryRunResult
            from kuberay_sdk.models.job import JobConfig

            config_model = JobConfig(
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
            return DryRunResult(config_model.to_crd_dict(), "RayJob")

        from kuberay_sdk.services.job_service import JobService

        svc = JobService(self._custom_api, self._config)
        await _run_sync(
            svc.create,
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
        return AsyncJobHandle(name, ns, self, mode="CRD")

    async def get_job(self, name: str, *, namespace: str | None = None) -> AsyncJobHandle:
        """Get a handle to an existing RayJob CR."""
        from kuberay_sdk.services.job_service import JobService

        ns = resolve_namespace(self._config, namespace)
        svc = JobService(self._custom_api, self._config)
        await _run_sync(svc.get_status, name, ns)
        return AsyncJobHandle(name, ns, self, mode="CRD")

    async def list_jobs(self, *, namespace: str | None = None) -> list[Any]:
        """List all RayJob CRs in the namespace."""
        from kuberay_sdk.services.job_service import JobService

        ns = resolve_namespace(self._config, namespace)
        svc = JobService(self._custom_api, self._config)
        return await _run_sync(svc.list, ns)

    # ── Service operations ──

    async def create_service(
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
        dry_run: bool = False,
    ) -> AsyncServiceHandle | Any:
        """Create a RayService CR."""
        ns = resolve_namespace(self._config, namespace)

        if dry_run:
            from kuberay_sdk.models.common import DryRunResult
            from kuberay_sdk.models.service import ServiceConfig

            config_model = ServiceConfig(
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
            return DryRunResult(config_model.to_crd_dict(), "RayService")

        from kuberay_sdk.services.service_service import ServiceService

        svc = ServiceService(self._custom_api, self._config)
        await _run_sync(
            svc.create,
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
        return AsyncServiceHandle(name, ns, self)

    async def get_service(self, name: str, *, namespace: str | None = None) -> AsyncServiceHandle:
        """Get a handle to an existing RayService."""
        from kuberay_sdk.services.service_service import ServiceService

        ns = resolve_namespace(self._config, namespace)
        svc = ServiceService(self._custom_api, self._config)
        await _run_sync(svc.get_status, name, ns)
        return AsyncServiceHandle(name, ns, self)

    async def list_services(self, *, namespace: str | None = None) -> list[ServiceStatus]:
        """List all RayServices in the namespace."""
        from kuberay_sdk.services.service_service import ServiceService

        ns = resolve_namespace(self._config, namespace)
        svc = ServiceService(self._custom_api, self._config)
        return await _run_sync(svc.list, ns)

    # ── Compound operations ──

    async def create_cluster_and_submit_job(
        self,
        cluster_name: str,
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
        preset: str | Any | None = None,
        wait_timeout: float = 300,
        progress_callback: Any = None,
    ) -> AsyncJobHandle:
        """Create a cluster, wait for it to be ready, then submit a job.

        On failure, the cluster is NOT deleted -- the error includes
        the cluster handle for inspection/cleanup.

        Example:
            >>> job = await client.create_cluster_and_submit_job(
            ...     "my-cluster",
            ...     entrypoint="python train.py",
            ...     workers=4,
            ... )
        """
        cluster = await self.create_cluster(
            cluster_name,
            namespace=namespace,
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
            preset=preset,
        )
        try:
            await cluster.wait_until_ready(
                timeout=wait_timeout,
                progress_callback=progress_callback,
            )
        except Exception as exc:
            # Attach cluster handle so user can clean up
            exc.cluster = cluster  # type: ignore[attr-defined]
            raise
        return await cluster.submit_job(entrypoint=entrypoint, runtime_env=runtime_env)

    # ── Capability discovery ──

    async def get_capabilities(self) -> ClusterCapabilities:
        """Discover cluster capabilities (KubeRay, GPU, Kueue, OpenShift).

        Returns a :class:`~kuberay_sdk.models.capabilities.ClusterCapabilities`
        object. Fields set to ``None`` mean the SDK could not determine the
        capability (e.g. insufficient RBAC permissions).

        Example:
            >>> caps = await client.get_capabilities()
            >>> if caps.gpu_available:
            ...     print(f"GPU types: {caps.gpu_types}")
        """
        from kuberay_sdk.capabilities import detect_capabilities

        return await _run_sync(detect_capabilities, self._api_client)
