"""Cluster models: WorkerGroup, HeadNodeConfig, ClusterConfig, ClusterStatus (T018).

Provides Pydantic models for RayCluster configuration and status.
ClusterConfig.to_crd_dict() generates a ray.io/v1 RayCluster CRD manifest
conforming to the RAYCLUSTER_SCHEMA contract.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel, Field, model_validator

from kuberay_sdk.errors import ValidationError as SDKValidationError
from kuberay_sdk.models.common import (
    ClusterState,
    ResourceRequirements,
    deep_merge,
)
from kuberay_sdk.models.runtime_env import RuntimeEnv
from kuberay_sdk.models.storage import StorageVolume

# K8s name regex: lowercase alphanumeric and hyphens, max 63 chars,
# must start and end with alphanumeric.
_K8S_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")

# Kueue queue label key
_KUEUE_QUEUE_LABEL = "kueue.x-k8s.io/queue-name"


# ──────────────────────────────────────────────
# WorkerGroup
# ──────────────────────────────────────────────


class WorkerGroup(BaseModel):
    """A homogeneous group of workers within a RayCluster.

    Example:
        >>> wg = WorkerGroup(name="gpu-pool", replicas=4, gpus=1, memory="16Gi")
    """

    name: str
    replicas: int = Field(..., ge=1)
    cpus: float = 1.0
    gpus: int = 0
    memory: str = "2Gi"
    min_replicas: int | None = None
    max_replicas: int | None = None
    gpu_type: str | None = None
    ray_start_params: dict[str, str] | None = None

    @model_validator(mode="after")
    def _validate_replicas(self) -> WorkerGroup:
        effective_min = self.min_replicas if self.min_replicas is not None else self.replicas
        effective_max = self.max_replicas if self.max_replicas is not None else self.replicas

        if effective_min > self.replicas:
            raise SDKValidationError(
                f"WorkerGroup '{self.name}': min_replicas ({effective_min}) must be <= replicas ({self.replicas})."
            )
        if self.replicas > effective_max:
            raise SDKValidationError(
                f"WorkerGroup '{self.name}': replicas ({self.replicas}) must be <= max_replicas ({effective_max})."
            )
        if effective_min > effective_max:
            raise SDKValidationError(
                f"WorkerGroup '{self.name}': min_replicas ({effective_min}) must be <= max_replicas ({effective_max})."
            )
        return self


# ──────────────────────────────────────────────
# HeadNodeConfig
# ──────────────────────────────────────────────


class HeadNodeConfig(BaseModel):
    """Override head node resource defaults.

    Example:
        >>> head = HeadNodeConfig(cpus=4.0, memory="8Gi")
    """

    cpus: float = 1.0
    memory: str = "2Gi"
    gpus: int = 0
    ray_start_params: dict[str, str] | None = None


# ──────────────────────────────────────────────
# ClusterConfig
# ──────────────────────────────────────────────


class ClusterConfig(BaseModel):
    """RayCluster configuration model.

    Supports two modes:
    - Simple: flat params (workers, cpus_per_worker, etc.)
    - Advanced: explicit worker_groups list

    Example:
        >>> cluster = ClusterConfig(name="my-cluster", workers=4, gpus_per_worker=1)
        >>> crd = cluster.to_crd()
    """

    name: str
    namespace: str | None = None
    workers: int = Field(default=1, ge=1)
    cpus_per_worker: float = Field(default=1.0, gt=0)
    gpus_per_worker: int = Field(default=0, ge=0)
    memory_per_worker: str = "2Gi"
    worker_groups: list[WorkerGroup] | None = None
    head: HeadNodeConfig | None = None
    ray_version: str | None = "2.41.0"
    image: str | None = None
    storage: list[StorageVolume] | None = None
    runtime_env: RuntimeEnv | dict | None = None  # type: ignore[type-arg]
    labels: dict[str, str] | None = None
    annotations: dict[str, str] | None = None
    tolerations: list[dict] | None = None  # type: ignore[type-arg]
    node_selector: dict[str, str] | None = None
    hardware_profile: str | None = None
    queue: str | None = None
    enable_autoscaling: bool = False
    raw_overrides: dict | None = None  # type: ignore[type-arg]

    @model_validator(mode="before")
    @classmethod
    def _resolve_worker_groups_vs_flat(cls, data: Any) -> Any:
        """Handle mutual exclusivity of worker_groups vs flat worker params.

        When both worker_groups and workers are present in the raw data,
        determines intent:
        - If workers is the only flat param and other config keys indicate
          a dict-merge pattern (e.g. namespace, ray_version also present),
          silently drop workers to allow worker_groups to take precedence.
        - Otherwise, raise a ValueError for the ambiguity.
        """
        if not isinstance(data, dict):
            return data

        has_worker_groups = "worker_groups" in data and data["worker_groups"] is not None
        has_workers = "workers" in data

        if has_worker_groups and has_workers:
            # Check if other flat worker params are also present
            other_flat = {"cpus_per_worker", "gpus_per_worker", "memory_per_worker"}
            has_other_flat = bool(other_flat & set(data.keys()))
            # Check for "boilerplate" keys that indicate a dict-merge pattern
            boilerplate_keys = {"namespace", "ray_version"}
            has_boilerplate = bool(boilerplate_keys & set(data.keys()))

            if has_boilerplate and not has_other_flat:
                # Likely from a dict merge/helper — silently drop workers
                # so that worker_groups takes precedence
                data = dict(data)
                del data["workers"]
            else:
                raise ValueError(
                    "Cannot use both 'workers' (simple mode) and 'worker_groups' (advanced mode). Choose one."
                )
        return data

    @model_validator(mode="after")
    def _validate_cluster(self) -> ClusterConfig:
        # Validate K8s name
        if not self.name or not _K8S_NAME_RE.match(self.name):
            raise SDKValidationError(
                f"Invalid cluster name '{self.name}': must be lowercase alphanumeric "
                f"with hyphens, 1-63 characters, and must not start or end with a hyphen."
            )
        return self

    def _resolve_image(self) -> str:
        """Resolve the container image to use."""
        if self.image:
            return self.image
        version = self.ray_version or "2.41.0"
        return f"rayproject/ray:{version}"

    def _build_resource_requirements(
        self,
        cpus: float,
        memory: str,
        gpus: int,
        gpu_type: str | None = None,
    ) -> dict[str, dict[str, str]]:
        """Build K8s resources dict for a container."""
        effective_gpu_type = gpu_type or "nvidia.com/gpu"
        res = ResourceRequirements(
            cpu=str(int(cpus)) if cpus == int(cpus) else str(cpus),
            memory=memory,
            gpu=str(gpus),
            gpu_type=effective_gpu_type,
        )
        return res.to_k8s_resources()

    def _build_container(
        self,
        name: str,
        image: str,
        cpus: float,
        memory: str,
        gpus: int,
        gpu_type: str | None = None,
        volume_mounts: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Build a K8s container spec."""
        container: dict[str, Any] = {
            "name": name,
            "image": image,
            "resources": self._build_resource_requirements(cpus, memory, gpus, gpu_type),
        }
        if volume_mounts:
            container["volumeMounts"] = volume_mounts
        return container

    def _build_pod_spec(
        self,
        containers: list[dict[str, Any]],
        volumes: list[dict[str, Any]] | None = None,
        node_selector: dict[str, str] | None = None,
        tolerations: list[dict] | None = None,  # type: ignore[type-arg]
    ) -> dict[str, Any]:
        """Build a K8s pod template spec."""
        spec: dict[str, Any] = {"containers": containers}
        if volumes:
            spec["volumes"] = volumes
        if node_selector:
            spec["nodeSelector"] = node_selector
        if tolerations:
            spec["tolerations"] = tolerations
        return spec

    def _get_volume_specs(self) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        """Get volumes and volume mounts from storage config."""
        volumes: list[dict[str, Any]] = []
        mounts: list[dict[str, str]] = []
        if self.storage:
            for vol in self.storage:
                volumes.append(vol.to_volume_spec())
                mounts.append(vol.to_volume_mount())
        return volumes, mounts

    def to_crd_dict(self) -> dict[str, Any]:
        """Generate the full ray.io/v1 RayCluster CRD manifest.

        Returns a dict conforming to RAYCLUSTER_SCHEMA.

        Example:
            >>> cluster = ClusterConfig(name="my-cluster", workers=2)
            >>> crd = cluster.to_crd_dict()
            >>> crd["apiVersion"]
            'ray.io/v1'
        """
        image = self._resolve_image()
        ray_version = self.ray_version or "2.41.0"
        head_config = self.head or HeadNodeConfig()
        volumes, volume_mounts = self._get_volume_specs()

        # Build labels
        metadata_labels: dict[str, str] = dict(self.labels or {})
        if self.queue:
            metadata_labels[_KUEUE_QUEUE_LABEL] = self.queue

        # Build annotations
        metadata_annotations: dict[str, str] = dict(self.annotations or {})

        # Head ray start params
        head_ray_params: dict[str, str] = {"dashboard-host": "0.0.0.0"}
        if head_config.ray_start_params:
            head_ray_params.update(head_config.ray_start_params)

        # Head container
        head_container = self._build_container(
            name="ray-head",
            image=image,
            cpus=head_config.cpus,
            memory=head_config.memory,
            gpus=head_config.gpus,
            volume_mounts=volume_mounts if volume_mounts else None,
        )

        # Head pod spec
        head_pod_spec = self._build_pod_spec(
            containers=[head_container],
            volumes=volumes if volumes else None,
            node_selector=self.node_selector,
            tolerations=self.tolerations,
        )

        head_group_spec: dict[str, Any] = {
            "rayStartParams": head_ray_params,
            "template": {"spec": head_pod_spec},
        }

        # Worker group specs
        worker_group_specs: list[dict[str, Any]] = []

        if self.worker_groups:
            # Advanced mode: explicit worker groups
            for wg in self.worker_groups:
                effective_min = wg.min_replicas if wg.min_replicas is not None else wg.replicas
                effective_max = wg.max_replicas if wg.max_replicas is not None else wg.replicas

                worker_container = self._build_container(
                    name="ray-worker",
                    image=image,
                    cpus=wg.cpus,
                    memory=wg.memory,
                    gpus=wg.gpus,
                    gpu_type=wg.gpu_type,
                    volume_mounts=volume_mounts if volume_mounts else None,
                )
                worker_pod_spec = self._build_pod_spec(
                    containers=[worker_container],
                    volumes=volumes if volumes else None,
                    node_selector=self.node_selector,
                    tolerations=self.tolerations,
                )
                ray_start_params = dict(wg.ray_start_params) if wg.ray_start_params else {}

                worker_group_specs.append(
                    {
                        "groupName": wg.name,
                        "replicas": wg.replicas,
                        "minReplicas": effective_min,
                        "maxReplicas": effective_max,
                        "rayStartParams": ray_start_params,
                        "template": {"spec": worker_pod_spec},
                    }
                )
        else:
            # Simple mode: single default worker group
            worker_container = self._build_container(
                name="ray-worker",
                image=image,
                cpus=self.cpus_per_worker,
                memory=self.memory_per_worker,
                gpus=self.gpus_per_worker,
                volume_mounts=volume_mounts if volume_mounts else None,
            )
            worker_pod_spec = self._build_pod_spec(
                containers=[worker_container],
                volumes=volumes if volumes else None,
                node_selector=self.node_selector,
                tolerations=self.tolerations,
            )
            worker_group_specs.append(
                {
                    "groupName": "default-workers",
                    "replicas": self.workers,
                    "minReplicas": self.workers,
                    "maxReplicas": self.workers,
                    "rayStartParams": {},
                    "template": {"spec": worker_pod_spec},
                }
            )

        # Build spec
        spec: dict[str, Any] = {
            "rayVersion": ray_version,
            "headGroupSpec": head_group_spec,
            "workerGroupSpecs": worker_group_specs,
        }

        if self.enable_autoscaling:
            spec["enableInTreeAutoscaling"] = True

        # Build full CRD dict
        crd: dict[str, Any] = {
            "apiVersion": "ray.io/v1",
            "kind": "RayCluster",
            "metadata": {
                "name": self.name,
                "namespace": self.namespace or "default",
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
            >>> cluster = ClusterConfig(name="my-cluster", workers=2)
            >>> crd = cluster.to_crd()
        """
        return self.to_crd_dict()


# ──────────────────────────────────────────────
# ClusterStatus (read-only)
# ──────────────────────────────────────────────


class ClusterStatus(BaseModel):
    """Read-only cluster status parsed from a K8s CR response.

    Example:
        >>> status = ClusterStatus.from_cr(cr_dict)
        >>> print(status.state, status.workers_ready)
    """

    model_config = {"frozen": True}

    name: str
    namespace: str
    state: str  # ClusterState value
    head_ready: bool
    workers_ready: int
    workers_desired: int
    ray_version: str
    dashboard_url: str | None = None
    age: timedelta
    conditions: list[Any] = Field(default_factory=list)

    @classmethod
    def from_cr(cls, cr: dict[str, Any]) -> ClusterStatus:
        """Parse a ClusterStatus from a Kubernetes CR response dict.

        Example:
            >>> cr = api.get_namespaced_custom_object(...)
            >>> status = ClusterStatus.from_cr(cr)
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
                # Handle ISO format timestamps
                created = datetime.fromisoformat(creation_ts.replace("Z", "+00:00"))
                age = datetime.now(timezone.utc) - created
            except (ValueError, TypeError):
                pass

        # Determine cluster state
        raw_state = status.get("state", "unknown")
        state = _map_cluster_state(raw_state)

        # Head readiness from conditions
        head_ready = False
        conditions_raw = status.get("conditions", [])
        for cond in conditions_raw:
            if cond.get("type") == "HeadPodReady" and cond.get("status") == "True":
                head_ready = True
                break

        # Worker counts
        workers_ready = status.get("readyWorkerReplicas", 0)
        workers_desired = status.get("desiredWorkerReplicas", 0)

        # Ray version
        ray_version = spec.get("rayVersion", "")

        # Dashboard URL (from status if available)
        dashboard_url = None
        head_info = status.get("head", {})
        if head_info:
            service_ip = head_info.get("serviceIP")
            if service_ip:
                dashboard_url = f"http://{service_ip}:8265"

        return cls(
            name=name,
            namespace=namespace,
            state=state,
            head_ready=head_ready,
            workers_ready=workers_ready,
            workers_desired=workers_desired,
            ray_version=ray_version,
            dashboard_url=dashboard_url,
            age=age,
            conditions=conditions_raw,
        )


def _map_cluster_state(raw: str) -> str:
    """Map raw K8s state string to ClusterState enum value."""
    mapping = {
        "ready": ClusterState.RUNNING.value,
        "running": ClusterState.RUNNING.value,
        "creating": ClusterState.CREATING.value,
        "suspended": ClusterState.SUSPENDED.value,
        "failed": ClusterState.FAILED.value,
        "deleting": ClusterState.DELETING.value,
    }
    return mapping.get(raw.lower(), ClusterState.UNKNOWN.value)
