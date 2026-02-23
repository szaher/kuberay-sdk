"""Shared test fixtures for kuberay_sdk tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def mock_api_client() -> MagicMock:
    """Mock kubernetes.client.ApiClient."""
    client = MagicMock()
    client.configuration = MagicMock()
    return client


@pytest.fixture()
def mock_custom_objects_api(mock_api_client: MagicMock) -> MagicMock:
    """Mock kubernetes.client.CustomObjectsApi with common response patterns."""
    api = MagicMock()

    # Default: successful create returns the created object
    api.create_namespaced_custom_object.return_value = {
        "apiVersion": "ray.io/v1",
        "kind": "RayCluster",
        "metadata": {"name": "test-cluster", "namespace": "default"},
        "spec": {},
        "status": {},
    }

    # Default: list returns empty
    api.list_namespaced_custom_object.return_value = {"items": []}

    # Default: get returns a basic object
    api.get_namespaced_custom_object.return_value = {
        "apiVersion": "ray.io/v1",
        "kind": "RayCluster",
        "metadata": {"name": "test-cluster", "namespace": "default"},
        "spec": {},
        "status": {},
    }

    return api


@pytest.fixture()
def mock_k8s_client(mock_api_client: MagicMock, mock_custom_objects_api: MagicMock) -> MagicMock:
    """Patch kubernetes client creation to return mocks."""
    with (
        patch("kuberay_sdk.config.get_k8s_client", return_value=mock_api_client),
        patch("kubernetes.client.CustomObjectsApi", return_value=mock_custom_objects_api),
    ):
        yield mock_custom_objects_api


def make_raycluster_cr(
    name: str = "test-cluster",
    namespace: str = "default",
    workers: int = 1,
    ray_version: str = "2.41.0",
    state: str = "ready",
    head_ready: bool = True,
) -> dict[str, Any]:
    """Create a mock RayCluster CR response."""
    return {
        "apiVersion": "ray.io/v1",
        "kind": "RayCluster",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "creationTimestamp": "2026-01-01T00:00:00Z",
            "labels": {},
            "annotations": {},
        },
        "spec": {
            "rayVersion": ray_version,
            "headGroupSpec": {
                "rayStartParams": {"dashboard-host": "0.0.0.0"},
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": "ray-head",
                                "image": f"rayproject/ray:{ray_version}",
                                "resources": {
                                    "requests": {"cpu": "1", "memory": "2Gi"},
                                    "limits": {"cpu": "1", "memory": "2Gi"},
                                },
                            }
                        ]
                    }
                },
            },
            "workerGroupSpecs": [
                {
                    "groupName": "default-workers",
                    "replicas": workers,
                    "minReplicas": workers,
                    "maxReplicas": workers,
                    "rayStartParams": {},
                    "template": {
                        "spec": {
                            "containers": [
                                {
                                    "name": "ray-worker",
                                    "image": f"rayproject/ray:{ray_version}",
                                    "resources": {
                                        "requests": {"cpu": "1", "memory": "2Gi"},
                                        "limits": {"cpu": "1", "memory": "2Gi"},
                                    },
                                }
                            ]
                        }
                    },
                }
            ],
        },
        "status": {
            "state": state,
            "head": {"podIP": "10.0.0.1", "serviceIP": "10.0.1.1"},
            "readyWorkerReplicas": workers if head_ready else 0,
            "desiredWorkerReplicas": workers,
            "conditions": [
                {
                    "type": "HeadPodReady",
                    "status": "True" if head_ready else "False",
                },
                {
                    "type": "RayClusterProvisioned",
                    "status": "True" if state == "ready" else "False",
                },
            ],
        },
    }


def make_rayjob_cr(
    name: str = "test-job",
    namespace: str = "default",
    entrypoint: str = "python train.py",
    state: str = "Running",
) -> dict[str, Any]:
    """Create a mock RayJob CR response."""
    return {
        "apiVersion": "ray.io/v1",
        "kind": "RayJob",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "creationTimestamp": "2026-01-01T00:00:00Z",
            "labels": {},
            "annotations": {},
        },
        "spec": {
            "entrypoint": entrypoint,
            "shutdownAfterJobFinishes": True,
            "rayClusterSpec": {},
        },
        "status": {
            "jobStatus": state,
            "jobDeploymentStatus": "Running",
            "startTime": "2026-01-01T00:00:00Z",
        },
    }


def make_rayservice_cr(
    name: str = "test-service",
    namespace: str = "default",
    state: str = "Running",
) -> dict[str, Any]:
    """Create a mock RayService CR response."""
    return {
        "apiVersion": "ray.io/v1",
        "kind": "RayService",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "creationTimestamp": "2026-01-01T00:00:00Z",
            "labels": {},
            "annotations": {},
        },
        "spec": {
            "serveConfigV2": "applications:\n  - name: default\n    import_path: serve_app:deployment\n",
            "rayClusterConfig": {},
        },
        "status": {
            "serviceStatus": state,
            "activeServiceStatus": {
                "applicationStatuses": {
                    "default": {"status": "RUNNING", "serveDeploymentStatuses": []},
                },
            },
        },
    }


def make_dashboard_job_response(
    job_id: str = "job-001",
    status: str = "RUNNING",
    entrypoint: str = "python train.py",
) -> dict[str, Any]:
    """Create a mock Dashboard job status response."""
    return {
        "job_id": job_id,
        "submission_id": f"raysubmit_{job_id}",
        "status": status,
        "entrypoint": entrypoint,
        "message": "" if status != "FAILED" else "Job failed",
        "start_time": 1704067200000,
        "end_time": 0 if status == "RUNNING" else 1704070800000,
        "metadata": {},
        "runtime_env": {},
    }
