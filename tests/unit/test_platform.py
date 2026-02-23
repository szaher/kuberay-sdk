"""Unit tests for platform detection and OpenShift/Kueue features (T059, T060, T061).

Tests cover:
- Platform detection: is_openshift, is_kueue_available, has_hardware_profiles
- HardwareProfile resolution: identifiers to resource requests, scheduling config
- Kueue label injection and constraint validation
- OpenShift Route creation
- 7-worker-group limit enforcement for Kueue (8 PodSet limit)
- shutdownAfterJobFinishes constraint for RayJobs with queue

TDD: these tests are written BEFORE the platform module implementation.
They will fail on import until the implementation is created.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from kuberay_sdk.errors import ValidationError
from kuberay_sdk.platform.detection import (
    has_hardware_profiles,
    is_kueue_available,
    is_openshift,
)
from kuberay_sdk.platform.kueue import (
    inject_queue_labels,
    list_queues,
    validate_kueue_constraints,
)
from kuberay_sdk.platform.openshift import (
    create_route,
    resolve_hardware_profile,
)

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _make_api_group(name: str) -> MagicMock:
    """Create a mock V1APIGroup with the given name."""
    group = MagicMock()
    group.name = name
    return group


def _make_api_group_list(*group_names: str) -> MagicMock:
    """Create a mock V1APIGroupList with the given group names."""
    group_list = MagicMock()
    group_list.groups = [_make_api_group(n) for n in group_names]
    return group_list


def _make_hardware_profile_cr(
    name: str = "gpu-large",
    namespace: str = "redhat-ods-applications",
    identifiers: list[dict[str, str]] | None = None,
    scheduling: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a mock HardwareProfile CR."""
    if identifiers is None:
        identifiers = [
            {
                "displayName": "CPU",
                "identifier": "cpu",
                "resourceType": "CPU",
                "defaultCount": "4",
                "minCount": "1",
                "maxCount": "16",
            },
            {
                "displayName": "Memory",
                "identifier": "memory",
                "resourceType": "Memory",
                "defaultCount": "8Gi",
                "minCount": "2Gi",
                "maxCount": "64Gi",
            },
            {
                "displayName": "NVIDIA GPU",
                "identifier": "nvidia.com/gpu",
                "resourceType": "Accelerator",
                "defaultCount": "1",
                "minCount": "0",
                "maxCount": "8",
            },
        ]
    if scheduling is None:
        scheduling = {
            "schedulingType": "Node",
            "node": {
                "nodeSelector": {"nvidia.com/gpu.present": "true"},
                "tolerations": [
                    {
                        "key": "nvidia.com/gpu",
                        "operator": "Exists",
                        "effect": "NoSchedule",
                    }
                ],
            },
        }
    return {
        "apiVersion": "infrastructure.opendatahub.io/v1",
        "kind": "HardwareProfile",
        "metadata": {"name": name, "namespace": namespace},
        "spec": {
            "identifiers": identifiers,
            "scheduling": scheduling,
        },
    }


# ──────────────────────────────────────────────
# T059: Platform detection
# ──────────────────────────────────────────────


class TestIsOpenShift:
    """Test is_openshift() detection via API group discovery."""

    def test_returns_true_when_route_api_exists(self):
        mock_client = MagicMock()
        mock_apis_api = MagicMock()
        mock_apis_api.get_api_versions.return_value = _make_api_group_list(
            "apps",
            "route.openshift.io",
            "config.openshift.io",
            "batch",
        )
        with patch("kuberay_sdk.platform.detection.ApisApi", return_value=mock_apis_api):
            assert is_openshift(mock_client) is True

    def test_returns_false_when_route_api_missing(self):
        mock_client = MagicMock()
        mock_apis_api = MagicMock()
        mock_apis_api.get_api_versions.return_value = _make_api_group_list(
            "apps",
            "batch",
            "networking.k8s.io",
        )
        with patch("kuberay_sdk.platform.detection.ApisApi", return_value=mock_apis_api):
            assert is_openshift(mock_client) is False

    def test_returns_false_on_api_error(self):
        mock_client = MagicMock()
        mock_apis_api = MagicMock()
        mock_apis_api.get_api_versions.side_effect = Exception("connection refused")
        with patch("kuberay_sdk.platform.detection.ApisApi", return_value=mock_apis_api):
            assert is_openshift(mock_client) is False


class TestIsKueueAvailable:
    """Test is_kueue_available() detection via API group discovery."""

    def test_returns_true_when_kueue_api_exists(self):
        mock_client = MagicMock()
        mock_apis_api = MagicMock()
        mock_apis_api.get_api_versions.return_value = _make_api_group_list(
            "apps",
            "kueue.x-k8s.io",
            "batch",
        )
        with patch("kuberay_sdk.platform.detection.ApisApi", return_value=mock_apis_api):
            assert is_kueue_available(mock_client) is True

    def test_returns_false_when_kueue_api_missing(self):
        mock_client = MagicMock()
        mock_apis_api = MagicMock()
        mock_apis_api.get_api_versions.return_value = _make_api_group_list(
            "apps",
            "batch",
        )
        with patch("kuberay_sdk.platform.detection.ApisApi", return_value=mock_apis_api):
            assert is_kueue_available(mock_client) is False

    def test_returns_false_on_api_error(self):
        mock_client = MagicMock()
        mock_apis_api = MagicMock()
        mock_apis_api.get_api_versions.side_effect = Exception("timeout")
        with patch("kuberay_sdk.platform.detection.ApisApi", return_value=mock_apis_api):
            assert is_kueue_available(mock_client) is False


class TestHasHardwareProfiles:
    """Test has_hardware_profiles() detection via CRD existence."""

    def test_returns_true_when_crd_exists(self):
        mock_client = MagicMock()
        mock_apis_api = MagicMock()
        mock_apis_api.get_api_versions.return_value = _make_api_group_list(
            "apps",
            "infrastructure.opendatahub.io",
            "route.openshift.io",
        )
        with patch("kuberay_sdk.platform.detection.ApisApi", return_value=mock_apis_api):
            assert has_hardware_profiles(mock_client) is True

    def test_returns_false_when_crd_missing(self):
        mock_client = MagicMock()
        mock_apis_api = MagicMock()
        mock_apis_api.get_api_versions.return_value = _make_api_group_list(
            "apps",
            "route.openshift.io",
        )
        with patch("kuberay_sdk.platform.detection.ApisApi", return_value=mock_apis_api):
            assert has_hardware_profiles(mock_client) is False

    def test_returns_false_on_api_error(self):
        mock_client = MagicMock()
        mock_apis_api = MagicMock()
        mock_apis_api.get_api_versions.side_effect = Exception("forbidden")
        with patch("kuberay_sdk.platform.detection.ApisApi", return_value=mock_apis_api):
            assert has_hardware_profiles(mock_client) is False


# ──────────────────────────────────────────────
# T060: HardwareProfile resolution
# ──────────────────────────────────────────────


class TestResolveHardwareProfile:
    """Test HardwareProfile CR reading and extraction."""

    def test_extracts_resource_requirements(self):
        """Identifiers are mapped to cpu, memory, and gpu resource requests."""
        mock_client = MagicMock()
        mock_custom_api = MagicMock()
        mock_custom_api.get_namespaced_custom_object.return_value = _make_hardware_profile_cr()

        with patch("kuberay_sdk.platform.openshift.CustomObjectsApi", return_value=mock_custom_api):
            result = resolve_hardware_profile(mock_client, "gpu-large", "redhat-ods-applications")

        assert result["resources"]["cpu"] == "4"
        assert result["resources"]["memory"] == "8Gi"
        assert result["resources"]["nvidia.com/gpu"] == "1"

    def test_extracts_node_scheduling(self):
        """Node scheduling type extracts nodeSelector and tolerations."""
        mock_client = MagicMock()
        mock_custom_api = MagicMock()
        mock_custom_api.get_namespaced_custom_object.return_value = _make_hardware_profile_cr()

        with patch("kuberay_sdk.platform.openshift.CustomObjectsApi", return_value=mock_custom_api):
            result = resolve_hardware_profile(mock_client, "gpu-large", "redhat-ods-applications")

        assert result["node_selector"] == {"nvidia.com/gpu.present": "true"}
        assert len(result["tolerations"]) == 1
        assert result["tolerations"][0]["key"] == "nvidia.com/gpu"
        assert result["queue"] is None
        assert result["priority_class"] is None

    def test_extracts_kueue_scheduling(self):
        """Queue scheduling type extracts queue and priority_class."""
        mock_client = MagicMock()
        mock_custom_api = MagicMock()
        scheduling = {
            "schedulingType": "Queue",
            "kueue": {
                "localQueueName": "gpu-queue",
                "priorityClass": "high-priority",
            },
        }
        mock_custom_api.get_namespaced_custom_object.return_value = _make_hardware_profile_cr(
            scheduling=scheduling,
        )

        with patch("kuberay_sdk.platform.openshift.CustomObjectsApi", return_value=mock_custom_api):
            result = resolve_hardware_profile(mock_client, "gpu-large", "redhat-ods-applications")

        assert result["queue"] == "gpu-queue"
        assert result["priority_class"] == "high-priority"
        assert result["node_selector"] == {}
        assert result["tolerations"] == []

    def test_kueue_scheduling_without_priority_class(self):
        """Queue scheduling without priorityClass sets priority_class to None."""
        mock_client = MagicMock()
        mock_custom_api = MagicMock()
        scheduling = {
            "schedulingType": "Queue",
            "kueue": {
                "localQueueName": "default-queue",
            },
        }
        mock_custom_api.get_namespaced_custom_object.return_value = _make_hardware_profile_cr(
            scheduling=scheduling,
        )

        with patch("kuberay_sdk.platform.openshift.CustomObjectsApi", return_value=mock_custom_api):
            result = resolve_hardware_profile(mock_client, "gpu-large", "redhat-ods-applications")

        assert result["queue"] == "default-queue"
        assert result["priority_class"] is None

    def test_cpu_only_profile(self):
        """Profile with only CPU and memory, no GPU."""
        mock_client = MagicMock()
        mock_custom_api = MagicMock()
        identifiers = [
            {
                "displayName": "CPU",
                "identifier": "cpu",
                "resourceType": "CPU",
                "defaultCount": "2",
                "minCount": "1",
                "maxCount": "8",
            },
            {
                "displayName": "Memory",
                "identifier": "memory",
                "resourceType": "Memory",
                "defaultCount": "4Gi",
                "minCount": "1Gi",
                "maxCount": "16Gi",
            },
        ]
        mock_custom_api.get_namespaced_custom_object.return_value = _make_hardware_profile_cr(
            name="cpu-small",
            identifiers=identifiers,
            scheduling={
                "schedulingType": "Node",
                "node": {"nodeSelector": {}, "tolerations": []},
            },
        )

        with patch("kuberay_sdk.platform.openshift.CustomObjectsApi", return_value=mock_custom_api):
            result = resolve_hardware_profile(mock_client, "cpu-small", "redhat-ods-applications")

        assert result["resources"]["cpu"] == "2"
        assert result["resources"]["memory"] == "4Gi"
        assert "nvidia.com/gpu" not in result["resources"]

    def test_profile_not_found_raises_error(self):
        """Non-existent profile raises KubeRayError."""
        from kubernetes.client import ApiException

        mock_client = MagicMock()
        mock_custom_api = MagicMock()
        mock_custom_api.get_namespaced_custom_object.side_effect = ApiException(status=404, reason="Not Found")

        with patch("kuberay_sdk.platform.openshift.CustomObjectsApi", return_value=mock_custom_api), pytest.raises(Exception, match="[Hh]ardware[Pp]rofile|not found"):
                resolve_hardware_profile(mock_client, "nonexistent", "redhat-ods-applications")

    def test_calls_correct_api_group_and_version(self):
        """Verifies the correct API group and version are used."""
        mock_client = MagicMock()
        mock_custom_api = MagicMock()
        mock_custom_api.get_namespaced_custom_object.return_value = _make_hardware_profile_cr()

        with patch("kuberay_sdk.platform.openshift.CustomObjectsApi", return_value=mock_custom_api):
            resolve_hardware_profile(mock_client, "gpu-large", "redhat-ods-applications")

        mock_custom_api.get_namespaced_custom_object.assert_called_once_with(
            group="infrastructure.opendatahub.io",
            version="v1",
            namespace="redhat-ods-applications",
            plural="hardwareprofiles",
            name="gpu-large",
        )


# ──────────────────────────────────────────────
# T061: Kueue label injection and constraints
# ──────────────────────────────────────────────


class TestInjectQueueLabels:
    """Test Kueue label injection into metadata labels."""

    def test_adds_queue_name_label(self):
        labels: dict[str, str] = {"app": "ray"}
        result = inject_queue_labels(labels, "my-queue")
        assert result["kueue.x-k8s.io/queue-name"] == "my-queue"
        # Original labels preserved
        assert result["app"] == "ray"

    def test_adds_priority_class_label(self):
        labels: dict[str, str] = {}
        result = inject_queue_labels(labels, "my-queue", priority_class="high")
        assert result["kueue.x-k8s.io/queue-name"] == "my-queue"
        assert result["kueue.x-k8s.io/priority-class"] == "high"

    def test_no_priority_class_when_none(self):
        labels: dict[str, str] = {}
        result = inject_queue_labels(labels, "my-queue")
        assert "kueue.x-k8s.io/priority-class" not in result

    def test_does_not_mutate_input_dict(self):
        labels: dict[str, str] = {"existing": "label"}
        result = inject_queue_labels(labels, "test-queue")
        # Original should not be mutated
        assert "kueue.x-k8s.io/queue-name" not in labels
        assert "kueue.x-k8s.io/queue-name" in result

    def test_overwrites_existing_queue_label(self):
        labels: dict[str, str] = {"kueue.x-k8s.io/queue-name": "old-queue"}
        result = inject_queue_labels(labels, "new-queue")
        assert result["kueue.x-k8s.io/queue-name"] == "new-queue"


class TestValidateKueueConstraints:
    """Test Kueue constraint validation."""

    def test_valid_rayjob_with_shutdown(self):
        """RayJob with shutdownAfterJobFinishes=True is valid."""
        # Should not raise
        validate_kueue_constraints(
            worker_groups_count=1,
            shutdown_after_finish=True,
            is_rayjob=True,
        )

    def test_rayjob_without_shutdown_raises(self):
        """RayJob with shutdownAfterJobFinishes=False raises ValidationError."""
        with pytest.raises(ValidationError, match="shutdownAfterJobFinishes"):
            validate_kueue_constraints(
                worker_groups_count=1,
                shutdown_after_finish=False,
                is_rayjob=True,
            )

    def test_non_rayjob_ignores_shutdown_constraint(self):
        """RayCluster does not need shutdownAfterJobFinishes."""
        # Should not raise even with shutdown_after_finish=False
        validate_kueue_constraints(
            worker_groups_count=1,
            shutdown_after_finish=False,
            is_rayjob=False,
        )

    def test_seven_worker_groups_is_valid(self):
        """7 worker groups (+ 1 head = 8 PodSets) is the max for Kueue."""
        # Should not raise
        validate_kueue_constraints(
            worker_groups_count=7,
            shutdown_after_finish=True,
            is_rayjob=True,
        )

    def test_eight_worker_groups_raises(self):
        """8 worker groups (+ 1 head = 9 PodSets) exceeds Kueue limit."""
        with pytest.raises(ValidationError, match="worker group|PodSet|[Kk]ueue"):
            validate_kueue_constraints(
                worker_groups_count=8,
                shutdown_after_finish=True,
                is_rayjob=True,
            )

    def test_zero_worker_groups_is_valid(self):
        """Edge case: zero worker groups is valid (head-only cluster)."""
        validate_kueue_constraints(
            worker_groups_count=0,
            shutdown_after_finish=True,
            is_rayjob=True,
        )

    def test_cluster_with_too_many_workers_raises(self):
        """RayCluster with 8+ worker groups also raises."""
        with pytest.raises(ValidationError, match="worker group|PodSet|[Kk]ueue"):
            validate_kueue_constraints(
                worker_groups_count=8,
                shutdown_after_finish=False,
                is_rayjob=False,
            )


class TestListQueues:
    """Test listing available Kueue LocalQueues."""

    def test_lists_queues_in_namespace(self):
        mock_client = MagicMock()
        mock_custom_api = MagicMock()
        mock_custom_api.list_namespaced_custom_object.return_value = {
            "items": [
                {
                    "metadata": {"name": "default-queue", "namespace": "my-ns"},
                    "spec": {"clusterQueue": "cluster-queue-1"},
                },
                {
                    "metadata": {"name": "gpu-queue", "namespace": "my-ns"},
                    "spec": {"clusterQueue": "cluster-queue-gpu"},
                },
            ]
        }

        with patch("kuberay_sdk.platform.kueue.CustomObjectsApi", return_value=mock_custom_api):
            queues = list_queues(mock_client, "my-ns")

        assert len(queues) == 2
        assert queues[0]["metadata"]["name"] == "default-queue"
        assert queues[1]["metadata"]["name"] == "gpu-queue"

    def test_lists_empty_queues(self):
        mock_client = MagicMock()
        mock_custom_api = MagicMock()
        mock_custom_api.list_namespaced_custom_object.return_value = {"items": []}

        with patch("kuberay_sdk.platform.kueue.CustomObjectsApi", return_value=mock_custom_api):
            queues = list_queues(mock_client, "my-ns")

        assert queues == []

    def test_calls_correct_api_group(self):
        mock_client = MagicMock()
        mock_custom_api = MagicMock()
        mock_custom_api.list_namespaced_custom_object.return_value = {"items": []}

        with patch("kuberay_sdk.platform.kueue.CustomObjectsApi", return_value=mock_custom_api):
            list_queues(mock_client, "my-ns")

        mock_custom_api.list_namespaced_custom_object.assert_called_once_with(
            group="kueue.x-k8s.io",
            version="v1beta1",
            namespace="my-ns",
            plural="localqueues",
        )


# ──────────────────────────────────────────────
# T063: OpenShift Route creation
# ──────────────────────────────────────────────


class TestCreateRoute:
    """Test OpenShift Route creation for Ray Dashboard."""

    def test_creates_route_with_edge_tls(self):
        mock_client = MagicMock()
        mock_custom_api = MagicMock()
        mock_custom_api.create_namespaced_custom_object.return_value = {
            "apiVersion": "route.openshift.io/v1",
            "kind": "Route",
            "metadata": {"name": "my-cluster-dashboard", "namespace": "default"},
            "spec": {
                "to": {"kind": "Service", "name": "my-cluster-head-svc", "weight": 100},
                "port": {"targetPort": 8265},
                "tls": {"termination": "edge", "insecureEdgeTerminationPolicy": "Redirect"},
            },
        }

        with patch("kuberay_sdk.platform.openshift.CustomObjectsApi", return_value=mock_custom_api):
            create_route(mock_client, "my-cluster-dashboard", "default", "my-cluster-head-svc")

        # Verify the route was created with correct spec
        call_args = mock_custom_api.create_namespaced_custom_object.call_args
        body = call_args[1].get("body") or call_args[0][4] if len(call_args[0]) > 4 else call_args[1]["body"]
        assert body["apiVersion"] == "route.openshift.io/v1"
        assert body["kind"] == "Route"
        assert body["metadata"]["name"] == "my-cluster-dashboard"
        assert body["metadata"]["namespace"] == "default"
        assert body["spec"]["to"]["kind"] == "Service"
        assert body["spec"]["to"]["name"] == "my-cluster-head-svc"
        assert body["spec"]["to"]["weight"] == 100
        assert body["spec"]["port"]["targetPort"] == 8265
        assert body["spec"]["tls"]["termination"] == "edge"
        assert body["spec"]["tls"]["insecureEdgeTerminationPolicy"] == "Redirect"

    def test_creates_route_with_custom_port(self):
        mock_client = MagicMock()
        mock_custom_api = MagicMock()
        mock_custom_api.create_namespaced_custom_object.return_value = {}

        with patch("kuberay_sdk.platform.openshift.CustomObjectsApi", return_value=mock_custom_api):
            create_route(mock_client, "my-route", "my-ns", "my-svc", port=9090)

        call_args = mock_custom_api.create_namespaced_custom_object.call_args
        body = call_args[1].get("body") or call_args[0][4] if len(call_args[0]) > 4 else call_args[1]["body"]
        assert body["spec"]["port"]["targetPort"] == 9090

    def test_calls_correct_api_group(self):
        mock_client = MagicMock()
        mock_custom_api = MagicMock()
        mock_custom_api.create_namespaced_custom_object.return_value = {}

        with patch("kuberay_sdk.platform.openshift.CustomObjectsApi", return_value=mock_custom_api):
            create_route(mock_client, "test", "default", "svc")

        mock_custom_api.create_namespaced_custom_object.assert_called_once()
        call_args = mock_custom_api.create_namespaced_custom_object.call_args
        # Verify API group and version in the call
        assert call_args[1].get("group") or call_args[0][0] == "route.openshift.io"
        assert call_args[1].get("version") or call_args[0][1] == "v1"

    def test_returns_created_route(self):
        mock_client = MagicMock()
        mock_custom_api = MagicMock()
        expected_route = {
            "apiVersion": "route.openshift.io/v1",
            "kind": "Route",
            "metadata": {"name": "my-route", "namespace": "default"},
            "spec": {},
            "status": {"ingress": [{"host": "my-route-default.apps.cluster.example.com"}]},
        }
        mock_custom_api.create_namespaced_custom_object.return_value = expected_route

        with patch("kuberay_sdk.platform.openshift.CustomObjectsApi", return_value=mock_custom_api):
            result = create_route(mock_client, "my-route", "default", "my-svc")

        assert result == expected_route
