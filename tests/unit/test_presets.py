"""Unit tests for presets (US7: T030-T031)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ── T030: Preset model tests ──


class TestPresetModel:
    """Test preset model and lookup functions."""

    def test_list_presets_returns_at_least_three(self) -> None:
        from kuberay_sdk.presets import list_presets

        presets = list_presets()
        assert len(presets) >= 3

    def test_get_preset_dev(self) -> None:
        from kuberay_sdk.presets import get_preset

        preset = get_preset("dev")
        assert preset.name == "dev"
        assert preset.workers == 1
        assert preset.worker_cpu == "1"
        assert preset.worker_memory == "2Gi"

    def test_get_preset_gpu_single(self) -> None:
        from kuberay_sdk.presets import get_preset

        preset = get_preset("gpu-single")
        assert preset.name == "gpu-single"
        assert preset.workers == 1
        assert preset.worker_gpu == 1
        assert preset.worker_cpu == "4"
        assert preset.worker_memory == "8Gi"

    def test_get_preset_data_processing(self) -> None:
        from kuberay_sdk.presets import get_preset

        preset = get_preset("data-processing")
        assert preset.name == "data-processing"
        assert preset.workers == 4
        assert preset.worker_cpu == "2"
        assert preset.worker_memory == "4Gi"

    def test_get_preset_nonexistent_raises(self) -> None:
        from kuberay_sdk.presets import get_preset

        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset("nonexistent")


# ── T031: Preset integration tests (using dry_run=True) ──


class TestPresetIntegration:
    """Test presets applied via create_cluster with dry_run=True."""

    def test_preset_dev_applies_defaults(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient
            from kuberay_sdk.models.common import DryRunResult

            client = KubeRayClient()
            result = client.create_cluster("test", preset="dev", dry_run=True)
            assert isinstance(result, DryRunResult)
            manifest = result.to_dict()
            # Dev preset: workers=1, worker_cpu=1, worker_memory=2Gi
            worker_specs = manifest["spec"]["workerGroupSpecs"]
            assert len(worker_specs) == 1
            assert worker_specs[0]["replicas"] == 1

    def test_explicit_params_override_preset(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient

            client = KubeRayClient()
            result = client.create_cluster(
                "test", preset="dev", workers=8, dry_run=True
            )
            manifest = result.to_dict()
            worker_specs = manifest["spec"]["workerGroupSpecs"]
            assert worker_specs[0]["replicas"] == 8

    def test_preset_as_string_works(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient

            client = KubeRayClient()
            result = client.create_cluster("test", preset="data-processing", dry_run=True)
            manifest = result.to_dict()
            worker_specs = manifest["spec"]["workerGroupSpecs"]
            assert worker_specs[0]["replicas"] == 4

    def test_preset_as_object_works(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient
            from kuberay_sdk.presets import Preset

            custom_preset = Preset(
                name="custom",
                workers=3,
                worker_cpu="2",
                worker_memory="4Gi",
            )
            client = KubeRayClient()
            result = client.create_cluster("test", preset=custom_preset, dry_run=True)
            manifest = result.to_dict()
            worker_specs = manifest["spec"]["workerGroupSpecs"]
            assert worker_specs[0]["replicas"] == 3

    def test_preset_gpu_single_applies_gpu(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient

            client = KubeRayClient()
            result = client.create_cluster("test", preset="gpu-single", dry_run=True)
            manifest = result.to_dict()
            worker_specs = manifest["spec"]["workerGroupSpecs"]
            worker_resources = worker_specs[0]["template"]["spec"]["containers"][0][
                "resources"
            ]
            assert "nvidia.com/gpu" in worker_resources["requests"]
            assert worker_resources["requests"]["nvidia.com/gpu"] == "1"

    def test_preset_head_config_applied(self, mock_k8s_client: MagicMock) -> None:
        with patch("kuberay_sdk.client.check_kuberay_crds"):
            from kuberay_sdk.client import KubeRayClient

            client = KubeRayClient()
            result = client.create_cluster("test", preset="gpu-single", dry_run=True)
            manifest = result.to_dict()
            head_resources = manifest["spec"]["headGroupSpec"]["template"]["spec"][
                "containers"
            ][0]["resources"]
            # gpu-single preset has head_cpu="2", head_memory="4Gi"
            assert head_resources["requests"]["cpu"] == "2"
            assert head_resources["requests"]["memory"] == "4Gi"
