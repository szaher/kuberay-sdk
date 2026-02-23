"""KubeRay Python SDK — manage Ray clusters, jobs, and services on Kubernetes.

Example:
    >>> from kuberay_sdk import KubeRayClient
    >>> client = KubeRayClient()
    >>> cluster = client.create_cluster("my-cluster", workers=4)
    >>> cluster.wait_until_ready()
"""

from kuberay_sdk.client import KubeRayClient
from kuberay_sdk.config import SDKConfig

__all__ = [
    "AsyncKubeRayClient",
    "KubeRayClient",
    "SDKConfig",
]


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    if name == "AsyncKubeRayClient":
        from kuberay_sdk.async_client import AsyncKubeRayClient

        return AsyncKubeRayClient
    raise AttributeError(f"module 'kuberay_sdk' has no attribute {name!r}")
