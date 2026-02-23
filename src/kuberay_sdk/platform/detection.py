"""Platform detection for OpenShift, Kueue, and HardwareProfiles (T062).

Detects platform capabilities by checking for the presence of specific
API groups via the Kubernetes API server discovery endpoint.

Functions:
    is_openshift: Checks for route.openshift.io and config.openshift.io
    is_kueue_available: Checks for kueue.x-k8s.io
    has_hardware_profiles: Checks for infrastructure.opendatahub.io
"""

from __future__ import annotations

import logging
from typing import Any

from kubernetes.client import ApisApi

logger = logging.getLogger(__name__)

# API groups used for platform detection
_OPENSHIFT_ROUTE_GROUP = "route.openshift.io"
_OPENSHIFT_CONFIG_GROUP = "config.openshift.io"
_KUEUE_GROUP = "kueue.x-k8s.io"
_HARDWARE_PROFILE_GROUP = "infrastructure.opendatahub.io"


def _get_api_groups(api_client: Any) -> set[str]:
    """Discover available API groups on the cluster.

    Returns a set of API group names (e.g., {"apps", "route.openshift.io"}).
    Returns an empty set if discovery fails.
    """
    try:
        apis_api = ApisApi(api_client)
        group_list = apis_api.get_api_versions()
        return {group.name for group in group_list.groups}
    except Exception as exc:
        logger.debug("API group discovery failed: %s", exc)
        return set()


def is_openshift(api_client: Any) -> bool:
    """Detect if the cluster is OpenShift by checking for route.openshift.io API group.

    Args:
        api_client: A kubernetes.client.ApiClient instance.

    Returns:
        True if route.openshift.io API group exists, False otherwise.

    Example:
        >>> from kuberay_sdk.platform.detection import is_openshift
        >>> is_openshift(api_client)
        True  # on OpenShift clusters
    """
    groups = _get_api_groups(api_client)
    result = _OPENSHIFT_ROUTE_GROUP in groups
    if result:
        logger.info("OpenShift platform detected (route.openshift.io API group found)")
    return result


def is_kueue_available(api_client: Any) -> bool:
    """Detect if Kueue is installed by checking for kueue.x-k8s.io API group.

    Args:
        api_client: A kubernetes.client.ApiClient instance.

    Returns:
        True if kueue.x-k8s.io API group exists, False otherwise.

    Example:
        >>> from kuberay_sdk.platform.detection import is_kueue_available
        >>> is_kueue_available(api_client)
        True  # when Kueue is installed
    """
    groups = _get_api_groups(api_client)
    result = _KUEUE_GROUP in groups
    if result:
        logger.info("Kueue detected (kueue.x-k8s.io API group found)")
    return result


def has_hardware_profiles(api_client: Any) -> bool:
    """Detect if HardwareProfile CRDs are installed (OpenShift AI / ODH).

    Checks for the infrastructure.opendatahub.io API group.

    Args:
        api_client: A kubernetes.client.ApiClient instance.

    Returns:
        True if infrastructure.opendatahub.io API group exists, False otherwise.

    Example:
        >>> from kuberay_sdk.platform.detection import has_hardware_profiles
        >>> has_hardware_profiles(api_client)
        True  # on OpenShift AI clusters
    """
    groups = _get_api_groups(api_client)
    result = _HARDWARE_PROFILE_GROUP in groups
    if result:
        logger.info("HardwareProfiles detected (infrastructure.opendatahub.io API group found)")
    return result
