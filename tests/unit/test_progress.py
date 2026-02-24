"""Unit tests for ProgressStatus model (US2 - T009)."""

from __future__ import annotations

import pytest


class TestProgressStatus:
    def test_creation(self) -> None:
        from kuberay_sdk.models.progress import ProgressStatus

        status = ProgressStatus(
            state="creating", elapsed_seconds=5.0, message="Waiting for head pod"
        )
        assert status.state == "creating"
        assert status.elapsed_seconds == 5.0
        assert status.message == "Waiting for head pod"

    def test_defaults(self) -> None:
        from kuberay_sdk.models.progress import ProgressStatus

        status = ProgressStatus(state="ready", elapsed_seconds=0.0)
        assert status.message == ""
        assert status.metadata == {}

    def test_negative_elapsed_raises(self) -> None:
        from kuberay_sdk.models.progress import ProgressStatus

        with pytest.raises(Exception):  # pydantic validation
            ProgressStatus(state="test", elapsed_seconds=-1.0)

    def test_metadata_preserved(self) -> None:
        from kuberay_sdk.models.progress import ProgressStatus

        status = ProgressStatus(
            state="ready", elapsed_seconds=10.0, metadata={"workers": 4}
        )
        assert status.metadata == {"workers": 4}

    def test_reexported_from_models_package(self) -> None:
        from kuberay_sdk.models import ProgressStatus

        status = ProgressStatus(state="running", elapsed_seconds=1.0)
        assert status.state == "running"
