"""SDK configuration, namespace resolution, and platform detection (FR-001, FR-002, FR-038)."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from kuberay_sdk.errors import AuthenticationError, KubeRayOperatorNotFoundError

logger = logging.getLogger(__name__)

_KUBERAY_GROUP = "ray.io"
_KUBERAY_VERSION = "v1"
_KUBERAY_PLURALS = ("rayclusters", "rayjobs", "rayservices")


class SDKConfig(BaseModel):
    """SDK-level configuration. Passed to the client constructor.

    Example:
        >>> config = SDKConfig(namespace="my-namespace")
        >>> from kuberay_sdk import KubeRayClient
        >>> client = KubeRayClient(config=config)

        >>> # With explicit authentication via kube-authkit
        >>> from kube_authkit import AuthConfig
        >>> config = SDKConfig(
        ...     namespace="ml-team",
        ...     auth=AuthConfig(method="oidc", oidc_issuer="https://...", client_id="my-app"),
        ... )
        >>> client = KubeRayClient(config=config)
    """

    auth: Any = None
    """Optional ``kube_authkit.AuthConfig`` for Kubernetes authentication.

    If None, falls back to kubeconfig / in-cluster auto-detection.
    """

    namespace: str | None = None
    """Default namespace. If None, uses kubeconfig active context namespace."""

    retry_max_attempts: int = Field(default=3, ge=0)
    retry_backoff_factor: float = Field(default=0.5, gt=0)
    retry_timeout: float = Field(default=60.0, gt=0)

    hardware_profile_namespace: str = "redhat-ods-applications"
    """Namespace where OpenShift HardwareProfile CRs live."""

    model_config = {"frozen": False, "arbitrary_types_allowed": True}


def get_k8s_client(auth: Any | None = None) -> Any:
    """Get an authenticated Kubernetes API client via kube-authkit.

    Args:
        auth: Optional ``kube_authkit.AuthConfig`` instance. If None,
            falls back to kubeconfig / in-cluster auto-detection.

    Returns a ``kubernetes.client.ApiClient`` instance.
    """
    try:
        from kube_authkit import AuthConfig
        from kube_authkit import get_k8s_client as _authkit_get_client

        effective_auth = auth if auth is not None else AuthConfig(method="auto")
        return _authkit_get_client(effective_auth)
    except ImportError:
        # Fallback: try direct kubernetes client
        try:
            import kubernetes

            kubernetes.config.load_incluster_config()
        except kubernetes.config.ConfigException:
            kubernetes.config.load_kube_config()
        return kubernetes.client.ApiClient()
    except Exception as exc:
        raise AuthenticationError(str(exc)) from exc


def resolve_namespace(config: SDKConfig, override: str | None = None) -> str:
    """Resolve the effective namespace for an operation.

    Priority: per-call override > config default > kubeconfig context.
    """
    if override:
        return override
    if config.namespace:
        return config.namespace
    # Fall back to kubeconfig context namespace
    try:
        import kubernetes

        _, active_context = kubernetes.config.list_kube_config_contexts()
        ns = active_context.get("context", {}).get("namespace", "default")
        return ns or "default"
    except Exception:
        return "default"


def check_kuberay_crds(api_client: Any) -> bool:
    """Check if KubeRay CRDs are installed on the cluster (FR-038).

    Returns True if CRDs found, raises KubeRayOperatorNotFoundError otherwise.
    """
    try:
        from kubernetes.client import ApiextensionsV1Api

        ext_api = ApiextensionsV1Api(api_client)
        crds = ext_api.list_custom_resource_definition()
        crd_names = {crd.metadata.name for crd in crds.items}
        required = {f"{plural}.{_KUBERAY_GROUP}" for plural in _KUBERAY_PLURALS}
        if not required.issubset(crd_names):
            missing = required - crd_names
            logger.warning("Missing KubeRay CRDs: %s", missing)
            raise KubeRayOperatorNotFoundError()
        return True
    except KubeRayOperatorNotFoundError:
        raise
    except Exception as exc:
        logger.warning("Could not verify KubeRay CRDs: %s", exc)
        raise KubeRayOperatorNotFoundError() from exc
