"""ClusterCapabilities model for capability discovery (US11)."""

from __future__ import annotations

from pydantic import BaseModel


class ClusterCapabilities(BaseModel):
    """Cluster capability discovery result.

    Fields set to ``None`` indicate that the SDK could not determine the
    capability (e.g. due to RBAC restrictions). ``False`` means the
    capability was checked and confirmed absent.
    """

    kuberay_installed: bool = False
    kuberay_version: str | None = None
    gpu_available: bool | None = None
    gpu_types: list[str] = []
    kueue_available: bool | None = None
    openshift: bool | None = None
