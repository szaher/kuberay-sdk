"""Platform detection and integration for OpenShift, Kueue, and HardwareProfiles."""

from kuberay_sdk.platform.detection import (
    has_hardware_profiles,
    is_kueue_available,
    is_openshift,
)
from kuberay_sdk.platform.kueue import (
    KUEUE_PRIORITY_LABEL,
    KUEUE_QUEUE_LABEL,
    inject_queue_labels,
    list_queues,
    validate_kueue_constraints,
)
from kuberay_sdk.platform.openshift import (
    create_route,
    resolve_hardware_profile,
)

__all__ = [
    "KUEUE_PRIORITY_LABEL",
    "KUEUE_QUEUE_LABEL",
    "create_route",
    "has_hardware_profiles",
    "inject_queue_labels",
    "is_kueue_available",
    "is_openshift",
    "list_queues",
    "resolve_hardware_profile",
    "validate_kueue_constraints",
]
