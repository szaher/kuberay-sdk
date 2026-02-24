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
    "ClusterConfig",
    "ExperimentTracking",
    "HeadNodeConfig",
    "JobConfig",
    "KubeRayClient",
    "RuntimeEnv",
    "SDKConfig",
    "ServiceConfig",
    "StorageVolume",
    "WorkerGroup",
]

# Lazy-loaded names and their source modules
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "AsyncKubeRayClient": ("kuberay_sdk.async_client", "AsyncKubeRayClient"),
    "ClusterConfig": ("kuberay_sdk.models.cluster", "ClusterConfig"),
    "ExperimentTracking": ("kuberay_sdk.models.runtime_env", "ExperimentTracking"),
    "HeadNodeConfig": ("kuberay_sdk.models.cluster", "HeadNodeConfig"),
    "JobConfig": ("kuberay_sdk.models.job", "JobConfig"),
    "RuntimeEnv": ("kuberay_sdk.models.runtime_env", "RuntimeEnv"),
    "ServiceConfig": ("kuberay_sdk.models.service", "ServiceConfig"),
    "StorageVolume": ("kuberay_sdk.models.storage", "StorageVolume"),
    "WorkerGroup": ("kuberay_sdk.models.cluster", "WorkerGroup"),
}


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        import importlib

        module = importlib.import_module(module_path)
        return getattr(module, attr_name)
    raise AttributeError(f"module 'kuberay_sdk' has no attribute {name!r}")
