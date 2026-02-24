"""T023: Verify convenience re-exports from the top-level ``kuberay_sdk`` package.

Every public model listed in US5 must be importable via
``from kuberay_sdk import <Name>`` **and** must resolve to the exact same
class object as the canonical deep import.
"""

from __future__ import annotations

import kuberay_sdk

# ── helpers ──────────────────────────────────────────────────────────


def _top_level(name: str) -> object:
    """Import *name* from the top-level ``kuberay_sdk`` package."""
    return getattr(kuberay_sdk, name)


# ── individual re-export tests ───────────────────────────────────────


class TestWorkerGroupReexport:
    def test_importable(self) -> None:
        from kuberay_sdk import WorkerGroup  # noqa: F401

    def test_identity(self) -> None:
        from kuberay_sdk import WorkerGroup
        from kuberay_sdk.models.cluster import WorkerGroup as Deep

        assert WorkerGroup is Deep


class TestRuntimeEnvReexport:
    def test_importable(self) -> None:
        from kuberay_sdk import RuntimeEnv  # noqa: F401

    def test_identity(self) -> None:
        from kuberay_sdk import RuntimeEnv
        from kuberay_sdk.models.runtime_env import RuntimeEnv as Deep

        assert RuntimeEnv is Deep


class TestStorageVolumeReexport:
    def test_importable(self) -> None:
        from kuberay_sdk import StorageVolume  # noqa: F401

    def test_identity(self) -> None:
        from kuberay_sdk import StorageVolume
        from kuberay_sdk.models.storage import StorageVolume as Deep

        assert StorageVolume is Deep


class TestClusterConfigReexport:
    def test_importable(self) -> None:
        from kuberay_sdk import ClusterConfig  # noqa: F401

    def test_identity(self) -> None:
        from kuberay_sdk import ClusterConfig
        from kuberay_sdk.models.cluster import ClusterConfig as Deep

        assert ClusterConfig is Deep


class TestJobConfigReexport:
    def test_importable(self) -> None:
        from kuberay_sdk import JobConfig  # noqa: F401

    def test_identity(self) -> None:
        from kuberay_sdk import JobConfig
        from kuberay_sdk.models.job import JobConfig as Deep

        assert JobConfig is Deep


class TestServiceConfigReexport:
    def test_importable(self) -> None:
        from kuberay_sdk import ServiceConfig  # noqa: F401

    def test_identity(self) -> None:
        from kuberay_sdk import ServiceConfig
        from kuberay_sdk.models.service import ServiceConfig as Deep

        assert ServiceConfig is Deep


class TestHeadNodeConfigReexport:
    def test_importable(self) -> None:
        from kuberay_sdk import HeadNodeConfig  # noqa: F401

    def test_identity(self) -> None:
        from kuberay_sdk import HeadNodeConfig
        from kuberay_sdk.models.cluster import HeadNodeConfig as Deep

        assert HeadNodeConfig is Deep


class TestExperimentTrackingReexport:
    def test_importable(self) -> None:
        from kuberay_sdk import ExperimentTracking  # noqa: F401

    def test_identity(self) -> None:
        from kuberay_sdk import ExperimentTracking
        from kuberay_sdk.models.runtime_env import ExperimentTracking as Deep

        assert ExperimentTracking is Deep


# ── __all__ completeness ─────────────────────────────────────────────


_EXPECTED_REEXPORTS = {
    "AsyncKubeRayClient",
    "ClusterConfig",
    "ExperimentTracking",
    "HeadNodeConfig",
    "JobConfig",
    "KubeRayClient",
    "RuntimeEnv",
    "SDKConfig",
    "ServiceConfig",
    "StorageVolume",
    "WorkerGroup",
}


class TestAllCompleteness:
    def test_all_includes_reexported_names(self) -> None:
        missing = _EXPECTED_REEXPORTS - set(kuberay_sdk.__all__)
        assert not missing, f"Missing from __all__: {missing}"

    def test_no_extra_names_in_all(self) -> None:
        extra = set(kuberay_sdk.__all__) - _EXPECTED_REEXPORTS
        assert not extra, f"Unexpected names in __all__: {extra}"
