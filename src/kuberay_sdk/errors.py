"""KubeRay SDK error hierarchy.

All SDK errors inherit from KubeRayError. Kubernetes API errors are
translated to domain-specific exceptions with user-friendly messages
in Ray/ML terms (FR-037, FR-038).
"""

from __future__ import annotations

from typing import Any


class KubeRayError(Exception):
    """Base exception for all SDK errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


# ── Cluster errors ──


class ClusterError(KubeRayError):
    """Cluster operation failed."""


class ClusterNotFoundError(ClusterError):
    """Cluster does not exist."""

    def __init__(self, name: str, namespace: str) -> None:
        super().__init__(
            f"Ray cluster '{name}' not found in namespace '{namespace}'.",
            details={"name": name, "namespace": namespace},
        )


class ClusterAlreadyExistsError(ClusterError):
    """Cluster exists with a different configuration."""

    def __init__(self, name: str, namespace: str) -> None:
        super().__init__(
            f"Cluster '{name}' already exists in namespace '{namespace}' with a different configuration.",
            details={"name": name, "namespace": namespace},
        )


# ── Job errors ──


class JobError(KubeRayError):
    """Job operation failed."""


class JobNotFoundError(JobError):
    """Job does not exist."""

    def __init__(self, name: str, namespace: str) -> None:
        super().__init__(
            f"Ray job '{name}' not found in namespace '{namespace}'.",
            details={"name": name, "namespace": namespace},
        )


# ── Service errors ──


class ServiceError(KubeRayError):
    """Service operation failed."""


class ServiceNotFoundError(ServiceError):
    """Service does not exist."""

    def __init__(self, name: str, namespace: str) -> None:
        super().__init__(
            f"Ray service '{name}' not found in namespace '{namespace}'.",
            details={"name": name, "namespace": namespace},
        )


# ── Infrastructure errors ──


class DashboardUnreachableError(KubeRayError):
    """Ray Dashboard is not accessible."""

    def __init__(self, cluster_name: str, reason: str = "") -> None:
        msg = f"Ray Dashboard for cluster '{cluster_name}' is not reachable."
        if reason:
            msg += f" {reason}"
        super().__init__(msg, details={"cluster_name": cluster_name})


class KubeRayOperatorNotFoundError(KubeRayError):
    """KubeRay operator CRDs are not installed on the cluster."""

    def __init__(self) -> None:
        super().__init__(
            "KubeRay operator is not installed on this cluster. "
            "The required CRDs (ray.io/v1) were not found. "
            "Please install the KubeRay operator before using this SDK. "
            "See: https://docs.ray.io/en/latest/cluster/kubernetes/getting-started.html"
        )


class AuthenticationError(KubeRayError):
    """Authentication failed or credentials expired."""

    def __init__(self, reason: str = "") -> None:
        msg = "Authentication failed."
        if reason:
            msg += f" {reason}"
        msg += " Please check your kubeconfig or re-authenticate."
        super().__init__(msg)


class ValidationError(KubeRayError):
    """Input validation failed."""


class ResourceConflictError(KubeRayError):
    """Resource exists with different configuration."""

    def __init__(self, kind: str, name: str, namespace: str) -> None:
        super().__init__(
            f"{kind} '{name}' already exists in namespace '{namespace}' with a different configuration.",
            details={"kind": kind, "name": name, "namespace": namespace},
        )


class TimeoutError(KubeRayError):
    """Operation timed out."""

    def __init__(self, operation: str, timeout: float) -> None:
        super().__init__(
            f"Operation '{operation}' timed out after {timeout:.0f} seconds.",
            details={"operation": operation, "timeout": timeout},
        )


# ── K8s error translation (FR-037) ──

_K8S_STATUS_MAP: dict[int, type[KubeRayError]] = {
    401: AuthenticationError,
    403: AuthenticationError,
    409: ResourceConflictError,
}


def translate_k8s_error(
    exc: Exception,
    *,
    resource_kind: str = "resource",
    resource_name: str = "",
    namespace: str = "",
) -> KubeRayError:
    """Translate a kubernetes.client.ApiException to a domain-specific error.

    Example:
        >>> from kubernetes.client import ApiException
        >>> try:
        ...     api.get_namespaced_custom_object(...)
        ... except ApiException as e:
        ...     raise translate_k8s_error(e, resource_kind="RayCluster", resource_name="my-cluster")
    """
    status: int = getattr(exc, "status", 0) or 0
    reason: str = getattr(exc, "reason", "") or ""

    if status == 404:
        if resource_kind == "RayCluster":
            return ClusterNotFoundError(resource_name, namespace)
        if resource_kind == "RayJob":
            return JobNotFoundError(resource_name, namespace)
        if resource_kind == "RayService":
            return ServiceNotFoundError(resource_name, namespace)
        return KubeRayError(
            f"{resource_kind} '{resource_name}' not found in namespace '{namespace}'.",
            details={"status": status},
        )

    if status == 401 or status == 403:
        return AuthenticationError(reason)

    if status == 409:
        return ResourceConflictError(resource_kind, resource_name, namespace)

    if status == 422:
        return ValidationError(
            f"Invalid {resource_kind} specification: {reason}",
            details={"status": status, "reason": reason},
        )

    if 500 <= status < 600:
        return KubeRayError(
            f"Kubernetes API server error ({status}). This is usually transient — the SDK will retry automatically.",
            details={"status": status, "reason": reason},
        )

    return KubeRayError(
        f"{resource_kind} operation failed: {reason}",
        details={"status": status, "reason": reason},
    )
