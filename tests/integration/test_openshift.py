"""Integration tests for OpenShift features (T082).

Tests OpenShift-specific functionality:
- HardwareProfile CR resolution (resource extraction, scheduling config)
- Kueue queue label injection into resource metadata
- Kueue constraint validation (shutdownAfterJobFinishes, PodSet limits)

All Kubernetes API calls are mocked. The tests verify that platform-specific
logic composes correctly with the core SDK services.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from kuberay_sdk.errors import KubeRayError, ValidationError
from kuberay_sdk.platform.kueue import (
    KUEUE_PRIORITY_LABEL,
    KUEUE_QUEUE_LABEL,
    MAX_WORKER_GROUPS,
    inject_queue_labels,
    validate_kueue_constraints,
)
from kuberay_sdk.platform.openshift import resolve_hardware_profile

# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


def _make_hardware_profile_cr(
    name: str = "gpu-large",
    namespace: str = "redhat-ods-applications",
    identifiers: list[dict[str, str]] | None = None,
    scheduling_type: str = "Node",
    node_selector: dict[str, str] | None = None,
    tolerations: list[dict[str, Any]] | None = None,
    queue_name: str | None = None,
    priority_class: str | None = None,
) -> dict[str, Any]:
    """Build a mock HardwareProfile CR for testing."""
    if identifiers is None:
        identifiers = [
            {"identifier": "cpu", "defaultCount": "4"},
            {"identifier": "memory", "defaultCount": "8Gi"},
            {"identifier": "nvidia.com/gpu", "defaultCount": "1"},
        ]

    scheduling: dict[str, Any] = {"schedulingType": scheduling_type}
    if scheduling_type == "Node":
        scheduling["node"] = {
            "nodeSelector": node_selector or {"nvidia.com/gpu.present": "true"},
            "tolerations": tolerations or [
                {
                    "key": "nvidia.com/gpu",
                    "operator": "Exists",
                    "effect": "NoSchedule",
                }
            ],
        }
    elif scheduling_type == "Queue":
        kueue_config: dict[str, Any] = {}
        if queue_name:
            kueue_config["localQueueName"] = queue_name
        if priority_class:
            kueue_config["priorityClass"] = priority_class
        scheduling["kueue"] = kueue_config

    return {
        "apiVersion": "infrastructure.opendatahub.io/v1",
        "kind": "HardwareProfile",
        "metadata": {
            "name": name,
            "namespace": namespace,
        },
        "spec": {
            "identifiers": identifiers,
            "scheduling": scheduling,
        },
    }


# ──────────────────────────────────────────────
# T082: HardwareProfile resolution
# ──────────────────────────────────────────────


@pytest.mark.integration
class TestHardwareProfileResolution:
    """Test HardwareProfile CR resolution extracts correct resources and scheduling."""

    def test_hardware_profile_resolution_node_scheduling(self):
        """Mocks a HardwareProfile CR with Node scheduling and verifies
        resolve_hardware_profile returns correct resources, node_selector,
        and tolerations.
        """
        hp_cr = _make_hardware_profile_cr(
            name="gpu-large",
            namespace="redhat-ods-applications",
            identifiers=[
                {"identifier": "cpu", "defaultCount": "4"},
                {"identifier": "memory", "defaultCount": "8Gi"},
                {"identifier": "nvidia.com/gpu", "defaultCount": "1"},
            ],
            scheduling_type="Node",
            node_selector={"nvidia.com/gpu.present": "true"},
            tolerations=[
                {
                    "key": "nvidia.com/gpu",
                    "operator": "Exists",
                    "effect": "NoSchedule",
                }
            ],
        )

        mock_api_client = MagicMock()

        with patch("kuberay_sdk.platform.openshift.CustomObjectsApi") as mock_custom_cls:
            mock_custom_api = MagicMock()
            mock_custom_cls.return_value = mock_custom_api
            mock_custom_api.get_namespaced_custom_object.return_value = hp_cr

            result = resolve_hardware_profile(
                mock_api_client,
                profile_name="gpu-large",
                namespace="redhat-ods-applications",
            )

        # Verify resources extracted from identifiers
        assert result["resources"] == {
            "cpu": "4",
            "memory": "8Gi",
            "nvidia.com/gpu": "1",
        }

        # Verify node scheduling config
        assert result["node_selector"] == {"nvidia.com/gpu.present": "true"}
        assert len(result["tolerations"]) == 1
        assert result["tolerations"][0]["key"] == "nvidia.com/gpu"
        assert result["tolerations"][0]["effect"] == "NoSchedule"

        # Queue fields should be None for Node scheduling
        assert result["queue"] is None
        assert result["priority_class"] is None

    def test_hardware_profile_resolution_queue_scheduling(self):
        """HardwareProfile with Queue scheduling should return queue and priority_class
        instead of node_selector and tolerations.
        """
        hp_cr = _make_hardware_profile_cr(
            name="gpu-medium",
            namespace="redhat-ods-applications",
            identifiers=[
                {"identifier": "cpu", "defaultCount": "2"},
                {"identifier": "memory", "defaultCount": "4Gi"},
            ],
            scheduling_type="Queue",
            queue_name="gpu-queue",
            priority_class="high-priority",
        )

        mock_api_client = MagicMock()

        with patch("kuberay_sdk.platform.openshift.CustomObjectsApi") as mock_custom_cls:
            mock_custom_api = MagicMock()
            mock_custom_cls.return_value = mock_custom_api
            mock_custom_api.get_namespaced_custom_object.return_value = hp_cr

            result = resolve_hardware_profile(
                mock_api_client,
                profile_name="gpu-medium",
                namespace="redhat-ods-applications",
            )

        # Resources still extracted
        assert result["resources"] == {"cpu": "2", "memory": "4Gi"}

        # Queue scheduling fields
        assert result["queue"] == "gpu-queue"
        assert result["priority_class"] == "high-priority"

        # Node scheduling fields should be empty for Queue scheduling
        assert result["node_selector"] == {}
        assert result["tolerations"] == []

    def test_hardware_profile_not_found_raises(self):
        """Missing HardwareProfile should raise KubeRayError."""
        mock_api_client = MagicMock()
        api_exception = type(
            "ApiException", (Exception,), {"status": 404, "reason": "Not Found"},
        )()

        with patch("kuberay_sdk.platform.openshift.CustomObjectsApi") as mock_custom_cls:
            mock_custom_api = MagicMock()
            mock_custom_cls.return_value = mock_custom_api
            mock_custom_api.get_namespaced_custom_object.side_effect = api_exception

            with pytest.raises(KubeRayError, match="not found"):
                resolve_hardware_profile(
                    mock_api_client,
                    profile_name="nonexistent-profile",
                    namespace="redhat-ods-applications",
                )

    def test_hardware_profile_cpu_only(self):
        """HardwareProfile with CPU-only identifiers (no GPU)."""
        hp_cr = _make_hardware_profile_cr(
            name="cpu-small",
            namespace="redhat-ods-applications",
            identifiers=[
                {"identifier": "cpu", "defaultCount": "1"},
                {"identifier": "memory", "defaultCount": "2Gi"},
            ],
            scheduling_type="Node",
            node_selector={},
            tolerations=[],
        )

        mock_api_client = MagicMock()

        with patch("kuberay_sdk.platform.openshift.CustomObjectsApi") as mock_custom_cls:
            mock_custom_api = MagicMock()
            mock_custom_cls.return_value = mock_custom_api
            mock_custom_api.get_namespaced_custom_object.return_value = hp_cr

            result = resolve_hardware_profile(
                mock_api_client,
                profile_name="cpu-small",
                namespace="redhat-ods-applications",
            )

        assert result["resources"] == {"cpu": "1", "memory": "2Gi"}
        assert "nvidia.com/gpu" not in result["resources"]


# ──────────────────────────────────────────────
# T082: Kueue queue injection
# ──────────────────────────────────────────────


@pytest.mark.integration
class TestKueueQueueInjection:
    """Test Kueue label injection into resource metadata."""

    def test_inject_queue_labels_basic(self):
        """inject_queue_labels should add the queue-name label."""
        labels = {"app": "ray", "team": "ml"}

        result = inject_queue_labels(labels, "gpu-queue")

        assert result[KUEUE_QUEUE_LABEL] == "gpu-queue"
        # Original labels preserved
        assert result["app"] == "ray"
        assert result["team"] == "ml"
        # No priority class by default
        assert KUEUE_PRIORITY_LABEL not in result

    def test_inject_queue_labels_with_priority_class(self):
        """inject_queue_labels should add both queue-name and priority-class labels."""
        labels = {"app": "ray"}

        result = inject_queue_labels(
            labels, "gpu-queue", priority_class="high-priority",
        )

        assert result[KUEUE_QUEUE_LABEL] == "gpu-queue"
        assert result[KUEUE_PRIORITY_LABEL] == "high-priority"
        assert result["app"] == "ray"

    def test_inject_queue_labels_empty_input(self):
        """inject_queue_labels should work with an empty labels dict."""
        result = inject_queue_labels({}, "default-queue")

        assert result[KUEUE_QUEUE_LABEL] == "default-queue"
        assert len(result) == 1

    def test_inject_queue_labels_does_not_mutate_input(self):
        """inject_queue_labels should return a new dict, not mutate the input."""
        original = {"app": "ray"}
        result = inject_queue_labels(original, "my-queue")

        assert KUEUE_QUEUE_LABEL in result
        assert KUEUE_QUEUE_LABEL not in original
        assert result is not original

    def test_inject_queue_labels_overwrites_existing(self):
        """If an existing queue label is present, it should be overwritten."""
        labels = {KUEUE_QUEUE_LABEL: "old-queue", "app": "ray"}

        result = inject_queue_labels(labels, "new-queue")

        assert result[KUEUE_QUEUE_LABEL] == "new-queue"


# ──────────────────────────────────────────────
# T082: Kueue validation
# ──────────────────────────────────────────────


@pytest.mark.integration
class TestKueueValidation:
    """Test Kueue constraint validation logic."""

    def test_valid_rayjob_with_shutdown(self):
        """RayJob with shutdown_after_finish=True and valid worker count should pass."""
        # Should not raise
        validate_kueue_constraints(
            worker_groups_count=3,
            shutdown_after_finish=True,
            is_rayjob=True,
        )

    def test_rayjob_without_shutdown_raises(self):
        """RayJob with Kueue queue but shutdown_after_finish=False should raise ValidationError."""
        with pytest.raises(ValidationError, match="shutdownAfterJobFinishes"):
            validate_kueue_constraints(
                worker_groups_count=1,
                shutdown_after_finish=False,
                is_rayjob=True,
            )

    def test_raycluster_without_shutdown_allowed(self):
        """RayCluster (not RayJob) should not require shutdown_after_finish."""
        # Should not raise -- is_rayjob=False means the shutdown constraint doesn't apply
        validate_kueue_constraints(
            worker_groups_count=3,
            shutdown_after_finish=False,
            is_rayjob=False,
        )

    def test_too_many_worker_groups_raises(self):
        """More than MAX_WORKER_GROUPS worker groups should raise ValidationError.

        Kueue limit: 8 PodSets total (1 head + up to 7 worker groups).
        """
        with pytest.raises(ValidationError, match="Too many worker groups"):
            validate_kueue_constraints(
                worker_groups_count=MAX_WORKER_GROUPS + 1,  # 8 groups + 1 head = 9 > 8
                shutdown_after_finish=True,
                is_rayjob=True,
            )

    def test_exactly_max_worker_groups_passes(self):
        """Exactly MAX_WORKER_GROUPS worker groups should pass (7 + 1 head = 8)."""
        # Should not raise
        validate_kueue_constraints(
            worker_groups_count=MAX_WORKER_GROUPS,  # 7 groups + 1 head = 8 = limit
            shutdown_after_finish=True,
            is_rayjob=True,
        )

    def test_single_worker_group_passes(self):
        """A single worker group should always pass PodSet validation."""
        validate_kueue_constraints(
            worker_groups_count=1,
            shutdown_after_finish=True,
            is_rayjob=True,
        )

    def test_zero_worker_groups_passes(self):
        """Zero worker groups (head only) should pass PodSet validation."""
        validate_kueue_constraints(
            worker_groups_count=0,
            shutdown_after_finish=True,
            is_rayjob=True,
        )

    def test_both_constraints_violated(self):
        """When both constraints are violated, the first check (shutdown) should raise."""
        with pytest.raises(ValidationError, match="shutdownAfterJobFinishes"):
            validate_kueue_constraints(
                worker_groups_count=MAX_WORKER_GROUPS + 1,
                shutdown_after_finish=False,
                is_rayjob=True,
            )
