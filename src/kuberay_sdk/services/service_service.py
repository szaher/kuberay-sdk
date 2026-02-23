"""ServiceService -- CRUD operations for RayService CRs (T044).

Manages RayService custom resources via the Kubernetes CustomObjectsApi.
Implements create (with idempotency), get_status, list, update, and delete
operations.

Example:
    >>> from kuberay_sdk.services.service_service import ServiceService
    >>> svc = ServiceService(custom_api, config)
    >>> svc.create(name="my-llm", namespace="default", import_path="serve_app:deployment")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import yaml

from kuberay_sdk.errors import ServiceNotFoundError
from kuberay_sdk.models.cluster import HeadNodeConfig, WorkerGroup
from kuberay_sdk.models.service import ServiceConfig, ServiceStatus
from kuberay_sdk.retry import idempotent_create

if TYPE_CHECKING:
    from kuberay_sdk.config import SDKConfig
    from kuberay_sdk.models.runtime_env import RuntimeEnv
    from kuberay_sdk.models.storage import StorageVolume

logger = logging.getLogger(__name__)

# K8s API constants for RayService
GROUP = "ray.io"
VERSION = "v1"
PLURAL = "rayservices"


class ServiceService:
    """Service for managing RayService custom resources.

    Example:
        >>> svc = ServiceService(custom_api, config)
        >>> svc.create(name="my-llm", namespace="default", import_path="serve_app:deployment")
        >>> status = svc.get_status("my-llm", "default")
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
        import_path: str | None = None,
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
    ) -> dict[str, Any]:
        """Create a RayService CR.

        Builds a ServiceConfig, generates the CRD manifest, and applies
        it via create_namespaced_custom_object. Uses idempotent_create
        for 409 conflict handling.

        Returns:
            The created (or existing identical) CR dict.

        Example:
            >>> svc.create(name="my-llm", namespace="default", import_path="serve_app:deployment")
        """
        config_kwargs: dict[str, Any] = {
            "name": name,
            "namespace": namespace,
            "num_replicas": num_replicas,
        }

        if import_path is not None:
            config_kwargs["import_path"] = import_path
        if serve_config_v2 is not None:
            config_kwargs["serve_config_v2"] = serve_config_v2
        if runtime_env is not None:
            config_kwargs["runtime_env"] = runtime_env
        if ray_version is not None:
            config_kwargs["ray_version"] = ray_version
        if image is not None:
            config_kwargs["image"] = image

        if worker_groups is not None:
            config_kwargs["worker_groups"] = worker_groups
        else:
            config_kwargs["workers"] = workers
            config_kwargs["cpus_per_worker"] = cpus_per_worker
            config_kwargs["gpus_per_worker"] = gpus_per_worker
            config_kwargs["memory_per_worker"] = memory_per_worker

        if head is not None:
            config_kwargs["head"] = head
        if storage is not None:
            config_kwargs["storage"] = storage
        if labels is not None:
            config_kwargs["labels"] = labels
        if annotations is not None:
            config_kwargs["annotations"] = annotations
        if route_enabled is not None:
            config_kwargs["route_enabled"] = route_enabled
        if raw_overrides is not None:
            config_kwargs["raw_overrides"] = raw_overrides

        service_config = ServiceConfig(**config_kwargs)
        body = service_config.to_crd_dict()

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

    def get_status(self, name: str, namespace: str) -> ServiceStatus:
        """Get the status of a RayService.

        Returns:
            ServiceStatus parsed from the CR.

        Raises:
            ServiceNotFoundError: If the service does not exist.

        Example:
            >>> status = svc.get_status("my-llm", "default")
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
                raise ServiceNotFoundError(name, namespace) from exc
            raise
        return ServiceStatus.from_cr(cr)

    def list(self, namespace: str) -> list[ServiceStatus]:
        """List all RayServices in a namespace.

        Returns:
            List of ServiceStatus objects.

        Example:
            >>> services = svc.list("default")
            >>> for s in services:
            ...     print(s.name, s.state)
        """
        response = self._api.list_namespaced_custom_object(
            group=self.GROUP,
            version=self.VERSION,
            namespace=namespace,
            plural=self.PLURAL,
        )
        items = response.get("items", [])
        return [ServiceStatus.from_cr(item) for item in items]

    def update(
        self,
        name: str,
        namespace: str,
        num_replicas: int | None = None,
        import_path: str | None = None,
        runtime_env: RuntimeEnv | dict | None = None,  # type: ignore[type-arg]
    ) -> None:
        """Update a RayService's serve configuration.

        Patches the serveConfigV2 field with updated parameters.

        Args:
            name: Service name.
            namespace: Service namespace.
            num_replicas: New desired replica count.
            import_path: New Python import path.
            runtime_env: New runtime environment.

        Raises:
            ServiceNotFoundError: If the service does not exist.

        Example:
            >>> svc.update("my-llm", "default", num_replicas=4)
        """
        # Get the current service
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
                raise ServiceNotFoundError(name, namespace) from exc
            raise

        # Parse existing serveConfigV2
        existing_serve_config_str = cr.get("spec", {}).get("serveConfigV2", "")
        try:
            serve_config = yaml.safe_load(existing_serve_config_str) or {}
        except yaml.YAMLError:
            serve_config = {}

        # Apply updates
        apps = serve_config.get("applications", [])
        if not apps:
            # Build a minimal application entry
            apps = [{"name": "default", "import_path": import_path or "", "deployments": []}]
            serve_config["applications"] = apps

        app = apps[0]

        if import_path is not None:
            app["import_path"] = import_path

        if runtime_env is not None:
            from kuberay_sdk.models.runtime_env import RuntimeEnv as RuntimeEnvModel

            if isinstance(runtime_env, RuntimeEnvModel):
                app["runtime_env"] = runtime_env.to_dict()
            else:
                app["runtime_env"] = dict(runtime_env)

        if num_replicas is not None:
            deployments = app.get("deployments", [])
            if deployments:
                deployments[0]["num_replicas"] = num_replicas
            else:
                deployments = [{"name": "default", "num_replicas": num_replicas}]
                app["deployments"] = deployments

        # Serialize back to YAML
        new_serve_config_str = yaml.dump(serve_config, default_flow_style=False)

        # Build the patch
        patch_body: dict[str, Any] = {
            "spec": {
                "serveConfigV2": new_serve_config_str,
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

    def delete(self, name: str, namespace: str) -> None:
        """Delete a RayService.

        Args:
            name: Service name.
            namespace: Service namespace.

        Raises:
            ServiceNotFoundError: If the service does not exist.

        Example:
            >>> svc.delete("my-llm", "default")
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
                raise ServiceNotFoundError(name, namespace) from exc
            raise
