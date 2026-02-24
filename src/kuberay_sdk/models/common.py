"""Shared types used across kuberay_sdk models."""

from __future__ import annotations

import enum
from typing import Any


class ClusterState(str, enum.Enum):
    """RayCluster lifecycle states."""

    CREATING = "CREATING"
    RUNNING = "RUNNING"
    SUSPENDED = "SUSPENDED"
    FAILED = "FAILED"
    DELETING = "DELETING"
    UNKNOWN = "UNKNOWN"


class JobState(str, enum.Enum):
    """RayJob lifecycle states."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"
    SUSPENDED = "SUSPENDED"
    UNKNOWN = "UNKNOWN"


class JobMode(str, enum.Enum):
    """How a job was submitted."""

    CRD = "CRD"
    DASHBOARD = "DASHBOARD"


class ServiceState(str, enum.Enum):
    """RayService lifecycle states."""

    DEPLOYING = "DEPLOYING"
    RUNNING = "RUNNING"
    UNHEALTHY = "UNHEALTHY"
    FAILED = "FAILED"
    DELETING = "DELETING"
    UNKNOWN = "UNKNOWN"


class Condition:
    """A Kubernetes-style condition (read-only)."""

    __slots__ = ("message", "reason", "status", "type")

    def __init__(
        self,
        type: str,
        status: str,
        reason: str = "",
        message: str = "",
    ) -> None:
        self.type = type
        self.status = status
        self.reason = reason
        self.message = message

    def __repr__(self) -> str:
        return f"Condition(type={self.type!r}, status={self.status!r})"


class ResourceRequirements:
    """CPU/memory/GPU resource specification."""

    __slots__ = ("cpu", "gpu", "gpu_type", "memory")

    def __init__(
        self,
        cpu: str = "1",
        memory: str = "2Gi",
        gpu: str = "0",
        gpu_type: str = "nvidia.com/gpu",
    ) -> None:
        self.cpu = cpu
        self.memory = memory
        self.gpu = gpu
        self.gpu_type = gpu_type

    def to_k8s_resources(self) -> dict[str, dict[str, str]]:
        """Convert to K8s container resource requests/limits.

        Example:
            >>> r = ResourceRequirements(cpu="2", memory="4Gi", gpu="1")
            >>> r.to_k8s_resources()
            {'requests': {'cpu': '2', 'memory': '4Gi', 'nvidia.com/gpu': '1'}, ...}
        """
        resources: dict[str, str] = {"cpu": self.cpu, "memory": self.memory}
        if self.gpu and self.gpu != "0":
            resources[self.gpu_type] = self.gpu
        return {"requests": dict(resources), "limits": dict(resources)}


class DryRunResult:
    """Wrapper for dry-run CRD manifest preview."""

    __slots__ = ("kind", "manifest")

    def __init__(self, manifest: dict[str, Any], kind: str) -> None:
        """Create a DryRunResult from a CRD manifest dict.

        Raises ValueError if the manifest is missing required top-level keys.
        """
        required = {"apiVersion", "kind", "metadata", "spec"}
        missing = required - set(manifest.keys())
        if missing:
            raise ValueError(f"Manifest missing required keys: {missing}")
        self.manifest = manifest
        self.kind = kind

    def to_dict(self) -> dict[str, Any]:
        """Return the raw CRD manifest dictionary."""
        return dict(self.manifest)

    def to_yaml(self) -> str:
        """Return the CRD manifest as a YAML string."""
        import yaml

        return yaml.dump(self.manifest, default_flow_style=False, sort_keys=False)

    def __repr__(self) -> str:
        name = self.manifest.get("metadata", {}).get("name", "?")
        return f"DryRunResult(kind={self.kind!r}, name={name!r})"


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge override into base, returning a new dict.

    Example:
        >>> deep_merge({"a": {"b": 1}}, {"a": {"c": 2}})
        {'a': {'b': 1, 'c': 2}}
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
