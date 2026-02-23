"""E2E test fixtures.

This module provides pytest fixtures for end-to-end testing against a real
Kubernetes cluster with the KubeRay operator installed. Fixtures handle:
- Cluster readiness verification (KubeRay operator deployment check)
- Namespace creation and cleanup per test session
- SDK client initialization with in-cluster kubeconfig
"""

from __future__ import annotations

import subprocess
import time
import uuid

import pytest

from kuberay_sdk import KubeRayClient


def _kubectl(*args: str) -> str:
    """Run a kubectl command and return stdout."""
    result = subprocess.run(
        ["kubectl", *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return result.stdout.strip()


def _wait_for_operator(timeout: int = 120) -> None:
    """Wait for the KubeRay operator deployment to be available."""
    _kubectl(
        "wait",
        "--for=condition=available",
        "deployment/kuberay-operator",
        f"--timeout={timeout}s",
    )


@pytest.fixture(scope="session", autouse=True)
def ensure_operator_ready() -> None:
    """Verify the KubeRay operator is running before any e2e tests execute."""
    _wait_for_operator()


@pytest.fixture(scope="session")
def test_namespace() -> str:
    """Create a unique test namespace for the e2e test session and clean it up after."""
    ns = f"e2e-test-{uuid.uuid4().hex[:8]}"
    _kubectl("create", "namespace", ns)
    yield ns
    # Allow some time for resources to finalize before deleting the namespace
    time.sleep(2)
    _kubectl("delete", "namespace", ns, "--ignore-not-found", "--wait=false")


@pytest.fixture(scope="session")
def sdk_client(test_namespace: str) -> KubeRayClient:
    """Create a KubeRayClient configured for the test namespace."""
    return KubeRayClient(namespace=test_namespace)
