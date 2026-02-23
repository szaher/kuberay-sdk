"""Kueue integration: label injection, constraint validation, and queue listing (T064).

Kueue provides job queueing and resource management for Kubernetes workloads.
This module handles:
- Injecting Kueue labels (queue-name, priority-class) into resource metadata
- Validating Kueue-specific constraints (shutdownAfterJobFinishes, PodSet limits)
- Listing available LocalQueues in a namespace

Constants:
    KUEUE_QUEUE_LABEL: "kueue.x-k8s.io/queue-name"
    KUEUE_PRIORITY_LABEL: "kueue.x-k8s.io/priority-class"
    MAX_WORKER_GROUPS: 7 (8 PodSets total including head)
"""

from __future__ import annotations

import logging
from typing import Any

from kubernetes.client import CustomObjectsApi

from kuberay_sdk.errors import ValidationError

logger = logging.getLogger(__name__)

# Kueue label keys (must match crd_schemas.py contract)
KUEUE_QUEUE_LABEL = "kueue.x-k8s.io/queue-name"
KUEUE_PRIORITY_LABEL = "kueue.x-k8s.io/priority-class"

# Kueue API coordinates
_KUEUE_GROUP = "kueue.x-k8s.io"
_KUEUE_VERSION = "v1beta1"
_LOCAL_QUEUE_PLURAL = "localqueues"

# Kueue PodSet limit: 8 total (1 head + up to 7 worker groups)
MAX_WORKER_GROUPS = 7
_MAX_PODSETS = 8


def inject_queue_labels(
    metadata_labels: dict[str, str],
    queue_name: str,
    priority_class: str | None = None,
) -> dict[str, str]:
    """Add Kueue queue-name and optional priority-class labels to a labels dict.

    Returns a new dict with the Kueue labels added; the input dict is not mutated.

    Args:
        metadata_labels: Existing labels dict to augment.
        queue_name: The Kueue LocalQueue name to set.
        priority_class: Optional Kueue priority class name.

    Returns:
        A new dict with the original labels plus Kueue labels.

    Example:
        >>> labels = {"app": "ray"}
        >>> inject_queue_labels(labels, "gpu-queue", priority_class="high")
        {'app': 'ray', 'kueue.x-k8s.io/queue-name': 'gpu-queue', 'kueue.x-k8s.io/priority-class': 'high'}
    """
    result = dict(metadata_labels)
    result[KUEUE_QUEUE_LABEL] = queue_name
    if priority_class is not None:
        result[KUEUE_PRIORITY_LABEL] = priority_class
    return result


def validate_kueue_constraints(
    worker_groups_count: int,
    shutdown_after_finish: bool,
    is_rayjob: bool,
) -> None:
    """Validate Kueue-specific constraints for a queued workload.

    Enforces two constraints:
    1. RayJobs with a Kueue queue MUST have shutdownAfterJobFinishes=True.
       This is required because Kueue manages the lifecycle of the workload
       and needs the cluster to be cleaned up when the job finishes.
    2. The total number of PodSets (1 head + N worker groups) must not exceed 8.
       Kueue has a hard limit of 8 PodSets per workload.

    Args:
        worker_groups_count: Number of worker groups in the spec.
        shutdown_after_finish: Value of shutdownAfterJobFinishes.
        is_rayjob: True if the workload is a RayJob, False for RayCluster.

    Raises:
        ValidationError: If any constraint is violated.

    Example:
        >>> validate_kueue_constraints(worker_groups_count=3, shutdown_after_finish=True, is_rayjob=True)
        # OK: 3 worker groups + 1 head = 4 PodSets, within limit
        >>> validate_kueue_constraints(worker_groups_count=8, shutdown_after_finish=True, is_rayjob=True)
        # Raises: 8 worker groups + 1 head = 9 PodSets, exceeds Kueue 8-PodSet limit
    """
    # Constraint 1: shutdownAfterJobFinishes for RayJobs
    if is_rayjob and not shutdown_after_finish:
        raise ValidationError(
            "RayJobs using a Kueue queue must have shutdownAfterJobFinishes=True. "
            "Kueue manages the workload lifecycle and requires the cluster to be "
            "cleaned up when the job finishes.",
            details={"shutdown_after_finish": shutdown_after_finish},
        )

    # Constraint 2: PodSet limit (head + worker groups <= 8)
    total_podsets = 1 + worker_groups_count  # 1 for head group
    if total_podsets > _MAX_PODSETS:
        raise ValidationError(
            f"Too many worker groups for Kueue: {worker_groups_count} worker groups + 1 head = "
            f"{total_podsets} PodSets, but Kueue has a limit of {_MAX_PODSETS} PodSets per workload. "
            f"Maximum allowed worker groups is {MAX_WORKER_GROUPS}.",
            details={
                "worker_groups_count": worker_groups_count,
                "total_podsets": total_podsets,
                "max_podsets": _MAX_PODSETS,
            },
        )


def list_queues(
    api_client: Any,
    namespace: str,
) -> list[dict[str, Any]]:
    """List available Kueue LocalQueues in a namespace.

    Args:
        api_client: A kubernetes.client.ApiClient instance.
        namespace: Namespace to list queues in.

    Returns:
        A list of LocalQueue resource dicts.

    Raises:
        KubeRayError: If the queues cannot be listed.

    Example:
        >>> queues = list_queues(api_client, "my-namespace")
    """
    custom_api = CustomObjectsApi(api_client)
    result = custom_api.list_namespaced_custom_object(
        group=_KUEUE_GROUP,
        version=_KUEUE_VERSION,
        namespace=namespace,
        plural=_LOCAL_QUEUE_PLURAL,
    )
    queues = result.get("items", [])
    logger.info("Found %d LocalQueue(s) in namespace '%s'", len(queues), namespace)
    return queues
