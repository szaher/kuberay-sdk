"""Capability discovery for Kubernetes clusters (US11).

Detects available features in the target cluster:
- KubeRay CRDs and version
- GPU resources on nodes
- Kueue integration
- OpenShift platform
"""

from __future__ import annotations

import logging
from typing import Any

from kubernetes.client import ApiextensionsV1Api, CoreV1Api

from kuberay_sdk.models.capabilities import ClusterCapabilities

logger = logging.getLogger(__name__)


def detect_capabilities(api_client: Any) -> ClusterCapabilities:
    """Detect cluster capabilities.

    RBAC errors result in ``None`` for affected fields.
    Network errors that prevent all discovery raise ``KubeRayError``.
    """
    caps = ClusterCapabilities()

    # ── 1. Check CRDs (KubeRay, Kueue, OpenShift) ──
    try:
        ext_api = ApiextensionsV1Api(api_client)
        crds = ext_api.list_custom_resource_definition()
        crd_names = {crd.metadata.name for crd in crds.items}

        # KubeRay
        if "rayclusters.ray.io" in crd_names:
            caps.kuberay_installed = True
            for crd in crds.items:
                if crd.metadata.name == "rayclusters.ray.io":
                    labels = crd.metadata.labels or {}
                    annotations = crd.metadata.annotations or {}
                    caps.kuberay_version = labels.get("app.kubernetes.io/version") or annotations.get(
                        "controller-gen.kubebuilder.io/version"
                    )
                    break

        # Kueue
        caps.kueue_available = "workloads.kueue.x-k8s.io" in crd_names

        # OpenShift
        caps.openshift = "routes.route.openshift.io" in crd_names

    except Exception as exc:
        status_code = getattr(exc, "status", None)
        if status_code in (401, 403):
            # RBAC error: cannot list CRDs, so we cannot determine kueue/openshift
            caps.kueue_available = None
            caps.openshift = None
        else:
            from kuberay_sdk.errors import KubeRayError

            raise KubeRayError(f"Failed to discover cluster capabilities: {exc}") from exc

    # ── 2. GPU detection ──
    try:
        core_api = CoreV1Api(api_client)
        nodes = core_api.list_node()
        gpu_types_found: set[str] = set()
        for node in nodes.items:
            allocatable = node.status.allocatable or {}
            for resource_name, quantity in allocatable.items():
                if "gpu" in resource_name.lower() and quantity and str(quantity) != "0":
                    gpu_types_found.add(resource_name)
        caps.gpu_available = len(gpu_types_found) > 0
        caps.gpu_types = sorted(gpu_types_found)
    except Exception as exc:
        status_code = getattr(exc, "status", None)
        if status_code in (401, 403):
            caps.gpu_available = None
        else:
            logger.warning("GPU detection failed: %s", exc)
            caps.gpu_available = None

    return caps
