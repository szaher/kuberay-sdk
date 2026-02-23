"""Job models: JobConfig and JobStatus (T029).

Provides Pydantic models for RayJob configuration and status.
JobConfig.to_crd_dict() generates a ray.io/v1 RayJob CRD manifest
conforming to the RAYJOB_SCHEMA contract.
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
from kuberay_sdk.models.common import (
    JobMode,
    JobState,
    deep_merge,
)
from kuberay_sdk.models.runtime_env import ExperimentTracking, RuntimeEnv
from kuberay_sdk.models.storage import StorageVolume

# K8s name regex: lowercase alphanumeric and hyphens, max 63 chars,
# must start and end with alphanumeric.
_K8S_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")

# Kueue queue label key
_KUEUE_QUEUE_LABEL = "kueue.x-k8s.io/queue-name"


# ──────────────────────────────────────────────
# JobConfig
# ──────────────────────────────────────────────


class JobConfig(BaseModel):
    """RayJob configuration model.

    Supports CRD mode (disposable cluster) with embedded rayClusterSpec.

    Example:
        >>> job = JobConfig(
        ...     name="training",
        ...     entrypoint="python train.py",
        ...     workers=4,
        ...     gpus_per_worker=1,
        ... )
        >>> crd = job.to_crd_dict()
    """

    name: str
    namespace: str | None = None
    entrypoint: str
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
    shutdown_after_finish: bool = True
    labels: dict[str, str] | None = None
    annotations: dict[str, str] | None = None
    queue: str | None = None
    hardware_profile: str | None = None
    experiment_tracking: ExperimentTracking | dict | None = None  # type: ignore[type-arg]
    raw_overrides: dict | None = None  # type: ignore[type-arg]

    @model_validator(mode="before")
    @classmethod
    def _resolve_worker_groups_vs_flat(cls, data: Any) -> Any:
        """Handle mutual exclusivity of worker_groups vs flat worker params."""
        if not isinstance(data, dict):
            return data

        has_worker_groups = "worker_groups" in data and data["worker_groups"] is not None
        has_workers = "workers" in data

        if has_worker_groups and has_workers:
            other_flat = {"cpus_per_worker", "gpus_per_worker", "memory_per_worker"}
            has_other_flat = bool(other_flat & set(data.keys()))
            boilerplate_keys = {"namespace", "ray_version", "name", "entrypoint"}
            has_boilerplate = bool(boilerplate_keys & set(data.keys()))

            if has_boilerplate and not has_other_flat:
                data = dict(data)
                del data["workers"]
            else:
                raise ValueError(
                    "Cannot use both 'workers' (simple mode) and 'worker_groups' (advanced mode). Choose one."
                )
        return data

    @model_validator(mode="after")
    def _validate_job(self) -> JobConfig:
        # Validate K8s name
        if not self.name or not _K8S_NAME_RE.match(self.name):
            raise SDKValidationError(
                f"Invalid job name '{self.name}': must be lowercase alphanumeric "
                f"with hyphens, 1-63 characters, and must not start or end with a hyphen."
            )

        # Validate entrypoint is non-empty
        if not self.entrypoint or not self.entrypoint.strip():
            raise SDKValidationError("JobConfig: 'entrypoint' must not be empty.")

        # Validate queue + shutdown_after_finish constraint
        if self.queue and not self.shutdown_after_finish:
            raise SDKValidationError(
                "JobConfig: when 'queue' is set (Kueue integration), 'shutdown_after_finish' must be True."
            )

        return self

    def _resolve_runtime_env(self) -> RuntimeEnv | None:
        """Resolve runtime_env, merging experiment tracking if present."""
        rt: RuntimeEnv | None = None

        if self.runtime_env is not None:
            rt = RuntimeEnv(**self.runtime_env) if isinstance(self.runtime_env, dict) else self.runtime_env

        # Resolve experiment tracking
        et: ExperimentTracking | None = None
        if self.experiment_tracking is not None:
            if isinstance(self.experiment_tracking, dict):
                et = ExperimentTracking(**self.experiment_tracking)
            else:
                et = self.experiment_tracking

        if et is not None:
            tracking_vars = et.to_env_vars()
            rt = rt.merge_env_vars(tracking_vars) if rt is not None else RuntimeEnv(env_vars=tracking_vars)

        return rt

    def _build_cluster_config(self) -> ClusterConfig:
        """Build a ClusterConfig for the embedded rayClusterSpec."""
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
        if self.hardware_profile is not None:
            config_kwargs["hardware_profile"] = self.hardware_profile

        return ClusterConfig(**config_kwargs)

    def to_crd_dict(self) -> dict[str, Any]:
        """Generate the full ray.io/v1 RayJob CRD manifest.

        Returns a dict conforming to RAYJOB_SCHEMA.

        Example:
            >>> job = JobConfig(name="my-job", entrypoint="python train.py")
            >>> crd = job.to_crd_dict()
            >>> crd["apiVersion"]
            'ray.io/v1'
        """
        # Build embedded cluster spec
        cluster_config = self._build_cluster_config()
        cluster_crd = cluster_config.to_crd_dict()
        # Extract just the spec portion for rayClusterSpec
        ray_cluster_spec = cluster_crd["spec"]

        # Build labels
        metadata_labels: dict[str, str] = dict(self.labels or {})
        if self.queue:
            metadata_labels[_KUEUE_QUEUE_LABEL] = self.queue

        # Build annotations
        metadata_annotations: dict[str, str] = dict(self.annotations or {})

        # Build spec
        spec: dict[str, Any] = {
            "entrypoint": self.entrypoint,
            "shutdownAfterJobFinishes": self.shutdown_after_finish,
            "rayClusterSpec": ray_cluster_spec,
        }

        # Handle runtime env
        resolved_rt = self._resolve_runtime_env()
        if resolved_rt is not None:
            rt_dict = resolved_rt.to_dict()
            if rt_dict:
                spec["runtimeEnvYAML"] = yaml.dump(rt_dict, default_flow_style=False)

        # Build full CRD dict
        crd: dict[str, Any] = {
            "apiVersion": "ray.io/v1",
            "kind": "RayJob",
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


# ──────────────────────────────────────────────
# JobStatus (read-only)
# ──────────────────────────────────────────────


# Mapping from CRD jobStatus strings to JobState enum values
_JOB_STATE_MAP: dict[str, JobState] = {
    "pending": JobState.PENDING,
    "running": JobState.RUNNING,
    "succeeded": JobState.SUCCEEDED,
    "failed": JobState.FAILED,
    "stopped": JobState.STOPPED,
    "suspended": JobState.SUSPENDED,
}


class JobStatus(BaseModel):
    """Read-only job status parsed from a K8s CR response.

    Example:
        >>> status = JobStatus.from_cr(cr_dict)
        >>> print(status.state, status.entrypoint)
    """

    model_config = {"frozen": True}

    name: str
    namespace: str
    state: JobState
    mode: JobMode
    entrypoint: str
    submitted_at: datetime
    duration: timedelta | None = None
    error_message: str | None = None
    cluster_name: str | None = None

    @classmethod
    def from_cr(cls, cr: dict[str, Any]) -> JobStatus:
        """Parse a JobStatus from a Kubernetes CR response dict.

        Example:
            >>> cr = api.get_namespaced_custom_object(...)
            >>> status = JobStatus.from_cr(cr)
        """
        metadata = cr.get("metadata", {})
        spec = cr.get("spec", {})
        status = cr.get("status", {})

        name = metadata.get("name", "")
        namespace = metadata.get("namespace", "default")

        # Parse creation timestamp
        creation_ts = metadata.get("creationTimestamp", "")
        submitted_at = datetime.now(timezone.utc)
        if creation_ts:
            try:
                submitted_at = datetime.fromisoformat(creation_ts.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Determine job state
        raw_state = status.get("jobStatus", "unknown")
        state = _JOB_STATE_MAP.get(raw_state.lower(), JobState.UNKNOWN)

        # Entrypoint
        entrypoint = spec.get("entrypoint", "")

        # Error message
        error_message = status.get("message") or None

        # Duration: compute from startTime and endTime if available
        duration: timedelta | None = None
        start_time_str = status.get("startTime")
        end_time_str = status.get("endTime")
        if start_time_str:
            try:
                start_dt = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                if end_time_str:
                    end_dt = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                    duration = end_dt - start_dt
                elif state in (JobState.RUNNING, JobState.PENDING):
                    duration = datetime.now(timezone.utc) - start_dt
            except (ValueError, TypeError):
                pass

        # Cluster name from status
        cluster_name = status.get("rayClusterName") or None

        return cls(
            name=name,
            namespace=namespace,
            state=state,
            mode=JobMode.CRD,
            entrypoint=entrypoint,
            submitted_at=submitted_at,
            duration=duration,
            error_message=error_message,
            cluster_name=cluster_name,
        )
