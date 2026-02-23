"""OpenShift-specific features: HardwareProfile resolution and Route creation (T063, T065).

This module provides integration with OpenShift-specific resources:
- HardwareProfile CRs (infrastructure.opendatahub.io/v1) for resource allocation
- Routes (route.openshift.io/v1) for exposing Ray Dashboard

Functions:
    resolve_hardware_profile: Reads a HardwareProfile CR and extracts resource
        requirements, node scheduling, and Kueue configuration.
    create_route: Creates an OpenShift Route with edge TLS termination.
"""

from __future__ import annotations

import logging
from typing import Any

from kubernetes.client import CustomObjectsApi

from kuberay_sdk.errors import KubeRayError

logger = logging.getLogger(__name__)

# HardwareProfile CRD coordinates
_HP_GROUP = "infrastructure.opendatahub.io"
_HP_VERSION = "v1"
_HP_PLURAL = "hardwareprofiles"

# Route CRD coordinates
_ROUTE_GROUP = "route.openshift.io"
_ROUTE_VERSION = "v1"
_ROUTE_PLURAL = "routes"


def resolve_hardware_profile(
    api_client: Any,
    profile_name: str,
    namespace: str,
) -> dict[str, Any]:
    """Read a HardwareProfile CR and extract resource requirements and scheduling config.

    Reads the HardwareProfile custom resource from the specified namespace,
    then extracts:
    - identifiers: mapped to resource requests (cpu, memory, gpu)
    - scheduling.node: mapped to node_selector and tolerations
    - scheduling.kueue: mapped to queue and priority_class

    Args:
        api_client: A kubernetes.client.ApiClient instance.
        profile_name: Name of the HardwareProfile CR.
        namespace: Namespace where the HardwareProfile lives.

    Returns:
        A dict with keys:
            - resources: dict mapping identifier to defaultCount (e.g., {"cpu": "4", "memory": "8Gi"})
            - node_selector: dict of node selector labels (empty if Queue scheduling)
            - tolerations: list of toleration dicts (empty if Queue scheduling)
            - queue: Kueue LocalQueue name or None (set if Queue scheduling)
            - priority_class: Kueue priority class or None

    Raises:
        KubeRayError: If the HardwareProfile is not found or cannot be read.

    Example:
        >>> result = resolve_hardware_profile(api_client, "gpu-large", "redhat-ods-applications")
        >>> result["resources"]
        {'cpu': '4', 'memory': '8Gi', 'nvidia.com/gpu': '1'}
        >>> result["node_selector"]
        {'nvidia.com/gpu.present': 'true'}
    """
    try:
        custom_api = CustomObjectsApi(api_client)
        cr = custom_api.get_namespaced_custom_object(
            group=_HP_GROUP,
            version=_HP_VERSION,
            namespace=namespace,
            plural=_HP_PLURAL,
            name=profile_name,
        )
    except Exception as exc:
        status = getattr(exc, "status", None)
        if status == 404:
            raise KubeRayError(
                f"HardwareProfile '{profile_name}' not found in namespace '{namespace}'.",
                details={"profile_name": profile_name, "namespace": namespace},
            ) from exc
        raise KubeRayError(
            f"Failed to read HardwareProfile '{profile_name}': {exc}",
            details={"profile_name": profile_name, "namespace": namespace},
        ) from exc

    spec = cr.get("spec", {})

    # Extract resource requirements from identifiers
    resources: dict[str, str] = {}
    for identifier in spec.get("identifiers", []):
        id_name = identifier.get("identifier", "")
        default_count = identifier.get("defaultCount", "")
        if id_name and default_count:
            resources[id_name] = default_count

    # Extract scheduling configuration
    scheduling = spec.get("scheduling", {})
    scheduling_type = scheduling.get("schedulingType", "")

    node_selector: dict[str, str] = {}
    tolerations: list[dict[str, Any]] = []
    queue: str | None = None
    priority_class: str | None = None

    if scheduling_type == "Node":
        node_config = scheduling.get("node", {})
        node_selector = node_config.get("nodeSelector", {})
        tolerations = node_config.get("tolerations", [])
    elif scheduling_type == "Queue":
        kueue_config = scheduling.get("kueue", {})
        queue = kueue_config.get("localQueueName")
        priority_class = kueue_config.get("priorityClass")

    logger.info(
        "Resolved HardwareProfile '%s': resources=%s, scheduling=%s",
        profile_name,
        resources,
        scheduling_type,
    )

    return {
        "resources": resources,
        "node_selector": node_selector,
        "tolerations": tolerations,
        "queue": queue,
        "priority_class": priority_class,
    }


def create_route(
    api_client: Any,
    name: str,
    namespace: str,
    service_name: str,
    port: int = 8265,
) -> dict[str, Any]:
    """Create an OpenShift Route with edge TLS termination.

    Creates a route.openshift.io/v1 Route pointing to the specified service.
    The route uses edge TLS termination with redirect for insecure traffic.

    Args:
        api_client: A kubernetes.client.ApiClient instance.
        name: Route name.
        namespace: Target namespace.
        service_name: Name of the K8s Service to route to.
        port: Target port on the service (default: 8265 for Ray Dashboard).

    Returns:
        The created Route resource as a dict.

    Raises:
        KubeRayError: If the Route cannot be created.

    Example:
        >>> route = create_route(api_client, "my-cluster-dashboard", "default", "my-cluster-head-svc")
    """
    route_body: dict[str, Any] = {
        "apiVersion": f"{_ROUTE_GROUP}/{_ROUTE_VERSION}",
        "kind": "Route",
        "metadata": {
            "name": name,
            "namespace": namespace,
        },
        "spec": {
            "to": {
                "kind": "Service",
                "name": service_name,
                "weight": 100,
            },
            "port": {
                "targetPort": port,
            },
            "tls": {
                "termination": "edge",
                "insecureEdgeTerminationPolicy": "Redirect",
            },
        },
    }

    try:
        custom_api = CustomObjectsApi(api_client)
        result = custom_api.create_namespaced_custom_object(
            group=_ROUTE_GROUP,
            version=_ROUTE_VERSION,
            namespace=namespace,
            plural=_ROUTE_PLURAL,
            body=route_body,
        )
        logger.info("Created OpenShift Route '%s' in namespace '%s'", name, namespace)
        return result
    except Exception as exc:
        raise KubeRayError(
            f"Failed to create OpenShift Route '{name}': {exc}",
            details={"name": name, "namespace": namespace, "service": service_name},
        ) from exc
