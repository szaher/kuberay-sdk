"""Service models: ServiceConfig, ServiceStatus (T043).

Provides Pydantic models for RayService configuration and status.
ServiceConfig.to_crd_dict() generates a ray.io/v1 RayService CRD manifest
conforming to the RAYSERVICE_SCHEMA contract.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator

from kuberay_sdk.errors import ValidationError as SDKValidationError
from kuberay_sdk.models.cluster import (
    ClusterConfig,
    HeadNodeConfig,
    WorkerGroup,
)
from kuberay_sdk.models.common import ServiceState, deep_merge
from kuberay_sdk.models.runtime_env import RuntimeEnv
from kuberay_sdk.models.storage import StorageVolume

# K8s name regex: lowercase alphanumeric and hyphens, max 63 chars,
# must start and end with alphanumeric.
_K8S_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")


# ──────────────────────────────────────────────
# ServiceConfig
# ──────────────────────────────────────────────


class ServiceConfig(BaseModel):
    """RayService configuration model.

    Supports two modes for serve configuration:
    - Simple: import_path + num_replicas (SDK builds serveConfigV2 YAML)
    - Advanced: raw serve_config_v2 YAML string

    Example:
        >>> svc = ServiceConfig(name="my-llm", import_path="serve_app:deployment")
        >>> crd = svc.to_crd_dict()
    """

    name: str
    namespace: str | None = None
    import_path: str | None = None
    num_replicas: int = Field(default=1, ge=1)
    runtime_env: RuntimeEnv | dict | None = None  # type: ignore[type-arg]
    ray_version: str | None = "2.41.0"
    image: str | None = None
    workers: int = Field(default=1, ge=1)
    cpus_per_worker: float = Field(default=1.0, gt=0)
    gpus_per_worker: int = Field(default=0, ge=0)
    memory_per_worker: str = "2Gi"
    worker_groups: list[WorkerGroup] | None = None
    head: HeadNodeConfig | None = None
    storage: list[StorageVolume] | None = None
    labels: dict[str, str] | None = None
    annotations: dict[str, str] | None = None
    route_enabled: bool | None = None
    serve_config_v2: str | None = None
    raw_overrides: dict | None = None  # type: ignore[type-arg]

    @model_validator(mode="after")
    def _validate_service(self) -> ServiceConfig:
        # Validate K8s name
        if not self.name or not _K8S_NAME_RE.match(self.name):
            raise SDKValidationError(
                f"Invalid service name '{self.name}': must be lowercase alphanumeric "
                f"with hyphens, 1-63 characters, and must not start or end with a hyphen."
            )

        # import_path and serve_config_v2 are mutually exclusive
        if self.import_path and self.serve_config_v2:
            raise SDKValidationError(
                "ServiceConfig: 'import_path' and 'serve_config_v2' are mutually exclusive. "
                "Use import_path for simple mode or serve_config_v2 for advanced mode."
            )

        # One of import_path or serve_config_v2 must be provided
        if not self.import_path and not self.serve_config_v2:
            raise SDKValidationError("ServiceConfig: either 'import_path' or 'serve_config_v2' must be provided.")

        return self

    def _resolve_image(self) -> str:
        """Resolve the container image to use."""
        if self.image:
            return self.image
        version = self.ray_version or "2.41.0"
        return f"rayproject/ray:{version}"

    def _build_serve_config_v2(self) -> str:
        """Build the serveConfigV2 YAML string from import_path + num_replicas.

        Generates a Ray Serve V2 config with a single application named 'default'.
        """
        if self.serve_config_v2:
            return self.serve_config_v2

        # Build the deployment config
        deployment: dict[str, Any] = {
            "name": "default",
            "num_replicas": self.num_replicas,
        }

        # Build the application config
        app: dict[str, Any] = {
            "name": "default",
            "import_path": self.import_path,
            "deployments": [deployment],
        }

        # Add runtime_env if provided
        if self.runtime_env:
            if isinstance(self.runtime_env, RuntimeEnv):
                app["runtime_env"] = self.runtime_env.to_dict()
            else:
                app["runtime_env"] = dict(self.runtime_env)

        config: dict[str, Any] = {
            "applications": [app],
        }

        return yaml.dump(config, default_flow_style=False)

    def _build_ray_cluster_config(self) -> dict[str, Any]:
        """Build the rayClusterConfig spec (embedded cluster configuration).

        Reuses ClusterConfig to generate a consistent cluster spec,
        then extracts just the spec portion.
        """
        config_kwargs: dict[str, Any] = {
            "name": self.name,
            "namespace": self.namespace or "default",
        }

        if self.worker_groups is not None:
            config_kwargs["worker_groups"] = self.worker_groups
        else:
            config_kwargs["workers"] = self.workers
            config_kwargs["cpus_per_worker"] = self.cpus_per_worker
            config_kwargs["gpus_per_worker"] = self.gpus_per_worker
            config_kwargs["memory_per_worker"] = self.memory_per_worker

        if self.head is not None:
            config_kwargs["head"] = self.head
        if self.ray_version is not None:
            config_kwargs["ray_version"] = self.ray_version
        if self.image is not None:
            config_kwargs["image"] = self.image
        if self.storage is not None:
            config_kwargs["storage"] = self.storage

        cluster_config = ClusterConfig(**config_kwargs)
        cluster_crd = cluster_config.to_crd_dict()

        # Return just the spec portion as the rayClusterConfig
        return cluster_crd["spec"]

    def to_crd_dict(self) -> dict[str, Any]:
        """Generate the full ray.io/v1 RayService CRD manifest.

        Returns a dict conforming to RAYSERVICE_SCHEMA.

        Example:
            >>> svc = ServiceConfig(name="my-llm", import_path="serve_app:deployment")
            >>> crd = svc.to_crd_dict()
            >>> crd["apiVersion"]
            'ray.io/v1'
        """
        namespace = self.namespace or "default"

        # Build labels
        metadata_labels: dict[str, str] = dict(self.labels or {})

        # Build annotations
        metadata_annotations: dict[str, str] = dict(self.annotations or {})

        # Build spec
        spec: dict[str, Any] = {
            "serveConfigV2": self._build_serve_config_v2(),
            "rayClusterConfig": self._build_ray_cluster_config(),
        }

        # Build full CRD dict
        crd: dict[str, Any] = {
            "apiVersion": "ray.io/v1",
            "kind": "RayService",
            "metadata": {
                "name": self.name,
                "namespace": namespace,
                "labels": metadata_labels,
                "annotations": metadata_annotations,
            },
            "spec": spec,
        }

        # Apply raw overrides via deep merge
        if self.raw_overrides:
            crd = deep_merge(crd, self.raw_overrides)

        return crd

    def to_crd(self) -> dict[str, Any]:
        """Alias for to_crd_dict() used by contract tests.

        Example:
            >>> svc = ServiceConfig(name="my-llm", import_path="serve_app:deployment")
            >>> crd = svc.to_crd()
        """
        return self.to_crd_dict()


# ──────────────────────────────────────────────
# ServiceStatus (read-only)
# ──────────────────────────────────────────────


class ServiceStatus(BaseModel):
    """Read-only service status parsed from a K8s CR response.

    Example:
        >>> status = ServiceStatus.from_cr(cr_dict)
        >>> print(status.state, status.replicas_ready)
    """

    model_config = {"frozen": True}

    name: str
    namespace: str
    state: str  # ServiceState value
    endpoint_url: str | None = None
    route_url: str | None = None
    replicas_ready: int
    replicas_desired: int
    age: timedelta

    @classmethod
    def from_cr(cls, cr: dict[str, Any]) -> ServiceStatus:
        """Parse a ServiceStatus from a Kubernetes CR response dict.

        Example:
            >>> cr = api.get_namespaced_custom_object(...)
            >>> status = ServiceStatus.from_cr(cr)
        """
        metadata = cr.get("metadata", {})
        spec = cr.get("spec", {})
        status = cr.get("status", {})

        name = metadata.get("name", "")
        namespace = metadata.get("namespace", "default")

        # Parse creation timestamp for age
        creation_ts = metadata.get("creationTimestamp", "")
        age = timedelta(seconds=0)
        if creation_ts:
            try:
                created = datetime.fromisoformat(creation_ts.replace("Z", "+00:00"))
                age = datetime.now(timezone.utc) - created
            except (ValueError, TypeError):
                pass

        # Determine service state
        raw_state = status.get("serviceStatus", "unknown")
        state = _map_service_state(raw_state)

        # Parse active service status for replica counts
        active_status = status.get("activeServiceStatus", {})
        app_statuses = active_status.get("applicationStatuses", {})

        replicas_ready = 0
        replicas_desired = 0

        # Count replicas across all applications
        for _app_name, app_status in app_statuses.items():
            deployments = app_status.get("serveDeploymentStatuses", [])
            for dep in deployments:
                replicas_ready += dep.get("healthyReplicas", 0)
                replicas_desired += dep.get("desiredReplicas", 0)

        # If no deployment statuses were found, try to infer from serveConfigV2
        if replicas_desired == 0:
            serve_config_str = spec.get("serveConfigV2", "")
            if serve_config_str:
                try:
                    serve_config = yaml.safe_load(serve_config_str)
                    if isinstance(serve_config, dict):
                        for app in serve_config.get("applications", []):
                            for dep in app.get("deployments", []):
                                replicas_desired += dep.get("num_replicas", 1)
                except (yaml.YAMLError, AttributeError):
                    pass

        # Endpoint URL from dashboard service
        dashboard_status = status.get("dashboardStatus", {})
        endpoint_url = None
        if dashboard_status:
            is_healthy = dashboard_status.get("isHealthy", False)
            if is_healthy:
                # Try to construct from service name
                endpoint_url = dashboard_status.get("dashboardUrl")

        # Route URL (OpenShift)
        route_url = None

        return cls(
            name=name,
            namespace=namespace,
            state=state,
            endpoint_url=endpoint_url,
            route_url=route_url,
            replicas_ready=replicas_ready,
            replicas_desired=replicas_desired,
            age=age,
        )


def _map_service_state(raw: str) -> str:
    """Map raw K8s service state string to ServiceState enum value."""
    mapping = {
        "running": ServiceState.RUNNING.value,
        "deploying": ServiceState.DEPLOYING.value,
        "waitforfailover": ServiceState.DEPLOYING.value,
        "waitforserverapplication": ServiceState.DEPLOYING.value,
        "unhealthy": ServiceState.UNHEALTHY.value,
        "failed": ServiceState.FAILED.value,
        "deleting": ServiceState.DELETING.value,
    }
    return mapping.get(raw.lower(), ServiceState.UNKNOWN.value)
