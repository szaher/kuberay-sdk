"""KubeRay SDK error hierarchy.

All SDK errors inherit from KubeRayError. Kubernetes API errors are
translated to domain-specific exceptions with user-friendly messages
in Ray/ML terms (FR-037, FR-038).

Every error carries an actionable ``remediation`` hint with kubectl /
helm commands users can run to diagnose or fix the problem (FR-038).
"""

from __future__ import annotations

from typing import Any


class KubeRayError(Exception):
    """Base exception for all SDK errors."""

    def __init__(
        self,
        message: str,
        remediation: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.remediation = remediation
        self.details = details or {}


# ── Cluster errors ──


class ClusterError(KubeRayError):
    """Cluster operation failed."""


class ClusterNotFoundError(ClusterError):
    """Cluster does not exist."""

    def __init__(self, name: str, namespace: str) -> None:
        super().__init__(
            f"Ray cluster '{name}' not found in namespace '{namespace}'.",
            remediation=(
                f"Verify the cluster exists:\n"
                f"  kubectl get rayclusters -n {namespace}\n"
                f"Check you are targeting the correct namespace."
            ),
            details={"name": name, "namespace": namespace},
        )


class ClusterAlreadyExistsError(ClusterError):
    """Cluster exists with a different configuration."""

    def __init__(self, name: str, namespace: str) -> None:
        super().__init__(
            f"Cluster '{name}' already exists in namespace '{namespace}' with a different configuration.",
            remediation=(
                f"Inspect the existing cluster:\n"
                f"  kubectl get raycluster {name} -n {namespace} -o yaml\n"
                f"Delete it first if you want to recreate:\n"
                f"  kubectl delete raycluster {name} -n {namespace}"
            ),
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
            remediation=(
                f"Verify the job exists:\n"
                f"  kubectl get rayjobs -n {namespace}\n"
                f"Check you are targeting the correct namespace."
            ),
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
            remediation=(
                f"Verify the service exists:\n"
                f"  kubectl get rayservices -n {namespace}\n"
                f"Check you are targeting the correct namespace."
            ),
            details={"name": name, "namespace": namespace},
        )


# ── Infrastructure errors ──


class DashboardUnreachableError(KubeRayError):
    """Ray Dashboard is not accessible."""

    def __init__(self, cluster_name: str, reason: str = "") -> None:
        msg = f"Ray Dashboard for cluster '{cluster_name}' is not reachable."
        if reason:
            msg += f" {reason}"
        super().__init__(
            msg,
            remediation=(
                f"Check that the cluster is running:\n"
                f"  kubectl get raycluster {cluster_name} -o jsonpath='{{.status.state}}'\n"
                f"Check the head pod is healthy:\n"
                f"  kubectl get pods -l ray.io/cluster={cluster_name} -l ray.io/node-type=head\n"
                f"Port-forward the dashboard locally:\n"
                f"  kubectl port-forward svc/{cluster_name}-head-svc 8265:8265"
            ),
            details={"cluster_name": cluster_name},
        )


class KubeRayOperatorNotFoundError(KubeRayError):
    """KubeRay operator CRDs are not installed on the cluster."""

    def __init__(self) -> None:
        super().__init__(
            "KubeRay operator is not installed on this cluster. "
            "The required CRDs (ray.io/v1) were not found. "
            "Please install the KubeRay operator before using this SDK. "
            "See: https://docs.ray.io/en/latest/cluster/kubernetes/getting-started.html",
            remediation=(
                "Install the KubeRay operator with Helm:\n"
                "  helm repo add kuberay https://ray-project.github.io/kuberay-helm/\n"
                "  helm repo update\n"
                "  helm install kuberay-operator kuberay/kuberay-operator\n"
                "Then verify the CRDs are registered:\n"
                "  kubectl get crd rayclusters.ray.io"
            ),
        )


class AuthenticationError(KubeRayError):
    """Authentication failed or credentials expired."""

    def __init__(self, reason: str = "") -> None:
        msg = "Authentication failed."
        if reason:
            msg += f" {reason}"
        msg += " Please check your kubeconfig or re-authenticate."
        super().__init__(
            msg,
            remediation=(
                "Check your current kubeconfig context:\n"
                "  kubectl config current-context\n"
                "Re-authenticate if your credentials have expired:\n"
                "  kubectl auth whoami\n"
                "Verify RBAC permissions for Ray resources:\n"
                "  kubectl auth can-i list rayclusters"
            ),
        )


class ValidationError(KubeRayError):
    """Input validation failed."""


class ResourceConflictError(KubeRayError):
    """Resource exists with different configuration."""

    def __init__(self, kind: str, name: str, namespace: str) -> None:
        super().__init__(
            f"{kind} '{name}' already exists in namespace '{namespace}' with a different configuration.",
            remediation=(
                f"Inspect the existing resource:\n"
                f"  kubectl get {kind.lower()} {name} -n {namespace} -o yaml\n"
                f"Delete it first if you want to recreate:\n"
                f"  kubectl delete {kind.lower()} {name} -n {namespace}"
            ),
            details={"kind": kind, "name": name, "namespace": namespace},
        )


class TimeoutError(KubeRayError):
    """Operation timed out."""

    def __init__(
        self,
        operation: str,
        timeout: float,
        last_status: Any = None,
    ) -> None:
        super().__init__(
            f"Operation '{operation}' timed out after {timeout:.0f} seconds.",
            remediation=(
                f"Increase the timeout (current: {timeout:.0f}s) and retry.\n"
                f"Check cluster events for issues:\n"
                f"  kubectl get events --sort-by=.lastTimestamp\n"
                f"Verify the cluster has sufficient resources:\n"
                f"  kubectl describe nodes | grep -A5 'Allocated resources'"
            ),
            details={"operation": operation, "timeout": timeout},
        )
        self.last_status = last_status


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
            remediation=(
                f"Verify the resource exists:\n"
                f"  kubectl get {resource_kind.lower()} -n {namespace}\n"
                f"Check you are targeting the correct namespace."
            ),
            details={"status": status},
        )

    if status == 401 or status == 403:
        return AuthenticationError(reason)

    if status == 409:
        return ResourceConflictError(resource_kind, resource_name, namespace)

    if status == 422:
        return ValidationError(
            f"Invalid {resource_kind} specification: {reason}",
            remediation=(
                f"Review your {resource_kind} spec for invalid fields.\n"
                f"Check the KubeRay CRD schema:\n"
                f"  kubectl explain {resource_kind.lower()}.spec"
            ),
            details={"status": status, "reason": reason},
        )

    if 500 <= status < 600:
        return KubeRayError(
            f"Kubernetes API server error ({status}). This is usually transient — the SDK will retry automatically.",
            remediation=(
                "Check the API server health:\n"
                "  kubectl cluster-info\n"
                "  kubectl get componentstatuses\n"
                "If the problem persists, check API server logs."
            ),
            details={"status": status, "reason": reason},
        )

    return KubeRayError(
        f"{resource_kind} operation failed: {reason}",
        remediation=(
            f"Check the status of your {resource_kind}:\n"
            f"  kubectl get {resource_kind.lower()} -n {namespace}\n"
            f"  kubectl describe {resource_kind.lower()} {resource_name} -n {namespace}"
        ),
        details={"status": status, "reason": reason},
    )
