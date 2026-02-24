"""Unit tests for dry-run mode (US6: T025-T026)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import yaml

# ── T025: DryRunResult model tests ──


class TestDryRunResult:
    """Test DryRunResult model behavior."""

    def test_to_dict_returns_manifest(self) -> None:
        from kuberay_sdk.models.common import DryRunResult

        manifest = {
            "apiVersion": "ray.io/v1",
            "kind": "RayCluster",
            "metadata": {"name": "test"},
            "spec": {"rayVersion": "2.41.0"},
        }
        result = DryRunResult(manifest, "RayCluster")
        d = result.to_dict()
        assert d == manifest
        # Ensure it returns a copy, not the same reference
        assert d is not result.manifest

    def test_to_yaml_produces_valid_yaml(self) -> None:
        from kuberay_sdk.models.common import DryRunResult

        manifest = {
            "apiVersion": "ray.io/v1",
            "kind": "RayCluster",
            "metadata": {"name": "test"},
            "spec": {"rayVersion": "2.41.0"},
        }
        result = DryRunResult(manifest, "RayCluster")
        yaml_str = result.to_yaml()
        parsed = yaml.safe_load(yaml_str)
        assert parsed["apiVersion"] == "ray.io/v1"
        assert parsed["kind"] == "RayCluster"

    def test_validation_rejects_missing_keys(self) -> None:
        from kuberay_sdk.models.common import DryRunResult

        # Missing 'spec'
        manifest = {
            "apiVersion": "ray.io/v1",
            "kind": "RayCluster",
            "metadata": {"name": "test"},
        }
        with pytest.raises(ValueError, match="Manifest missing required keys"):
            DryRunResult(manifest, "RayCluster")

    def test_validation_rejects_empty_manifest(self) -> None:
        from kuberay_sdk.models.common import DryRunResult

        with pytest.raises(ValueError, match="Manifest missing required keys"):
            DryRunResult({}, "RayCluster")

    def test_repr(self) -> None:
        from kuberay_sdk.models.common import DryRunResult

        manifest = {
            "apiVersion": "ray.io/v1",
            "kind": "RayCluster",
            "metadata": {"name": "my-cluster"},
            "spec": {},
        }
        result = DryRunResult(manifest, "RayCluster")
        assert repr(result) == "DryRunResult(kind='RayCluster', name='my-cluster')"

    def test_repr_missing_name(self) -> None:
        from kuberay_sdk.models.common import DryRunResult

        manifest = {
            "apiVersion": "ray.io/v1",
            "kind": "RayCluster",
            "metadata": {},
            "spec": {},
        }
        result = DryRunResult(manifest, "RayCluster")
        assert "name='?'" in repr(result)


# ── T026: Dry-run integration tests ──


class TestDryRunIntegration:
    """Test dry_run=True with client create methods."""

    def test_create_cluster_dry_run_returns_dry_run_result(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient
            from kuberay_sdk.models.common import DryRunResult

            client = KubeRayClient()
            result = client.create_cluster("test-cluster", dry_run=True)
            assert isinstance(result, DryRunResult)
            assert result.kind == "RayCluster"
            assert result.manifest["metadata"]["name"] == "test-cluster"

    def test_create_cluster_dry_run_no_api_call(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient

            client = KubeRayClient()
            client.create_cluster("test-cluster", dry_run=True)
            # The mock_k8s_client is the CustomObjectsApi mock
            mock_k8s_client.create_namespaced_custom_object.assert_not_called()

    def test_create_cluster_dry_run_invalid_name_raises(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient

            client = KubeRayClient()
            with pytest.raises(Exception):
                client.create_cluster("INVALID_NAME!", dry_run=True)

    def test_create_job_dry_run(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient
            from kuberay_sdk.models.common import DryRunResult

            client = KubeRayClient()
            result = client.create_job("test-job", entrypoint="python train.py", dry_run=True)
            assert isinstance(result, DryRunResult)
            assert result.kind == "RayJob"
            assert result.manifest["spec"]["entrypoint"] == "python train.py"
            mock_k8s_client.create_namespaced_custom_object.assert_not_called()

    def test_create_service_dry_run(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient
            from kuberay_sdk.models.common import DryRunResult

            client = KubeRayClient()
            result = client.create_service(
                "test-service",
                import_path="serve_app:deployment",
                dry_run=True,
            )
            assert isinstance(result, DryRunResult)
            assert result.kind == "RayService"
            mock_k8s_client.create_namespaced_custom_object.assert_not_called()

    def test_create_cluster_dry_run_manifest_has_required_keys(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient

            client = KubeRayClient()
            result = client.create_cluster("test-cluster", workers=4, gpus_per_worker=1, dry_run=True)
            manifest = result.to_dict()
            assert manifest["apiVersion"] == "ray.io/v1"
            assert manifest["kind"] == "RayCluster"
            assert "metadata" in manifest
            assert "spec" in manifest
