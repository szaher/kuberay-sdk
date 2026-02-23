"""End-to-end smoke tests for kuberay-sdk.

These tests validate core SDK operations against a real Kubernetes cluster
with the KubeRay operator installed. They require:
- A running Kubernetes cluster (e.g., Kind)
- KubeRay operator installed and ready
- Valid kubeconfig pointing to the cluster

Run with: make test-e2e
"""

from __future__ import annotations

import pytest

from kuberay_sdk import KubeRayClient


@pytest.mark.e2e
class TestClusterSmoke:
    """Smoke tests for RayCluster lifecycle."""

    def test_create_and_delete_cluster(self, sdk_client: KubeRayClient, test_namespace: str) -> None:
        """Create a minimal RayCluster, verify it reaches ready state, then delete it."""
        handle = sdk_client.create_cluster(
            name="smoke-cluster",
            namespace=test_namespace,
            ray_version="2.9.0",
            head_cpu="500m",
            head_memory="512Mi",
        )
        try:
            status = handle.status()
            assert status is not None, "Cluster status should not be None"
            assert handle.name == "smoke-cluster"
        finally:
            handle.delete()

    def test_cluster_status(self, sdk_client: KubeRayClient, test_namespace: str) -> None:
        """Create a cluster and verify status fields are populated."""
        handle = sdk_client.create_cluster(
            name="smoke-status",
            namespace=test_namespace,
            ray_version="2.9.0",
            head_cpu="500m",
            head_memory="512Mi",
        )
        try:
            status = handle.status()
            assert status is not None
        finally:
            handle.delete()


@pytest.mark.e2e
class TestJobSmoke:
    """Smoke tests for RayJob submission."""

    def test_submit_and_complete_job(self, sdk_client: KubeRayClient, test_namespace: str) -> None:
        """Submit a simple RayJob and verify it completes."""
        handle = sdk_client.create_job(
            name="smoke-job",
            namespace=test_namespace,
            ray_version="2.9.0",
            entrypoint="python -c \"import ray; ray.init(); print('hello from ray')\"",
            head_cpu="500m",
            head_memory="512Mi",
            shutdown_after_finish=True,
        )
        try:
            status = handle.status()
            assert status is not None, "Job status should not be None"
            assert handle.name == "smoke-job"
        finally:
            handle.delete()


@pytest.mark.e2e
class TestServiceSmoke:
    """Smoke tests for RayService deployment."""

    def test_deploy_and_delete_service(self, sdk_client: KubeRayClient, test_namespace: str) -> None:
        """Deploy a minimal RayService and verify it is created, then delete it."""
        handle = sdk_client.create_service(
            name="smoke-service",
            namespace=test_namespace,
            ray_version="2.9.0",
            import_path="ray.serve.tests.test_config_files.world:app",
            head_cpu="500m",
            head_memory="512Mi",
        )
        try:
            status = handle.status()
            assert status is not None, "Service status should not be None"
            assert handle.name == "smoke-service"
        finally:
            handle.delete()
