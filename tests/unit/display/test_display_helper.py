"""Unit tests for display() helper function (T010)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from kuberay_sdk.display import display

if TYPE_CHECKING:
    import pytest


class TestDisplayHelper:
    """Tests for the display() utility function."""

    def test_empty_list_prints_no_resources(self, capsys: pytest.CaptureFixture[str]) -> None:
        display([])
        output = capsys.readouterr().out
        assert "No resources found" in output

    def test_list_of_dicts_renders_table(self, capsys: pytest.CaptureFixture[str]) -> None:
        data = [
            {"name": "c1", "namespace": "default", "state": "RUNNING"},
            {"name": "c2", "namespace": "dev", "state": "FAILED"},
        ]
        # Force plain backend
        with patch.dict("os.environ", {"KUBERAY_DISPLAY": "plain"}):
            import kuberay_sdk.display as display_mod

            display_mod._cached_backend = None
            display(data)

        output = capsys.readouterr().out
        assert "NAME" in output
        assert "c1" in output
        assert "RUNNING" in output

    def test_format_json_delegates_to_format_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        data = [{"name": "test"}]
        display(data, format="json")
        output = capsys.readouterr().out
        assert '"name"' in output
        assert '"test"' in output

    def test_single_object_renders_repr_in_plain(self, capsys: pytest.CaptureFixture[str]) -> None:
        obj = MagicMock()
        obj.__repr__ = MagicMock(return_value="MockObject(name='test')")
        obj._name = "test"
        obj._namespace = "default"

        with patch.dict("os.environ", {"KUBERAY_DISPLAY": "plain"}):
            import kuberay_sdk.display as display_mod

            display_mod._cached_backend = None
            display(obj)

        output = capsys.readouterr().out
        assert "MockObject" in output

    def test_list_clusters_return_type_unchanged(self) -> None:
        """FR-024: client.list_clusters() return type must be raw data objects."""
        # The display function should NOT modify what list_clusters returns.
        # It's a side-effect-only function that reads data, not modifies it.
        mock_cluster = MagicMock()
        mock_cluster.name = "c1"
        mock_cluster.namespace = "default"
        mock_cluster.state = "RUNNING"
        mock_cluster.workers = 4

        data = [mock_cluster]
        # display() returns None — it's side-effect only
        result = display(data)
        assert result is None
        # Original data is unchanged
        assert data[0].name == "c1"
        assert data[0].state == "RUNNING"

    def test_display_with_title(self, capsys: pytest.CaptureFixture[str]) -> None:
        data = [{"name": "c1", "state": "RUNNING"}]
        with patch.dict("os.environ", {"KUBERAY_DISPLAY": "plain"}):
            import kuberay_sdk.display as display_mod

            display_mod._cached_backend = None
            display(data, title="Test Title")

        output = capsys.readouterr().out
        assert "Test Title" in output


class TestGetBackend:
    """Tests for get_backend()."""

    def test_plain_override(self) -> None:
        import kuberay_sdk.display as display_mod
        from kuberay_sdk.display import get_backend
        from kuberay_sdk.display._backend import PlainBackend

        display_mod._cached_backend = None
        backend = get_backend(override="plain")
        assert isinstance(backend, PlainBackend)

    def test_caches_backend(self) -> None:
        import kuberay_sdk.display as display_mod
        from kuberay_sdk.display import get_backend

        display_mod._cached_backend = None

        with patch.dict("os.environ", {"KUBERAY_DISPLAY": "plain"}):
            b1 = get_backend()
            b2 = get_backend()
            assert b1 is b2

    def test_override_bypasses_cache(self) -> None:
        import kuberay_sdk.display as display_mod
        from kuberay_sdk.display import get_backend
        from kuberay_sdk.display._backend import PlainBackend

        display_mod._cached_backend = None

        b1 = get_backend(override="plain")
        b2 = get_backend(override="plain")
        # Both should be PlainBackend, but override doesn't write to cache
        assert isinstance(b1, PlainBackend)
        assert isinstance(b2, PlainBackend)

    def test_fallback_to_plain_when_rich_not_installed(self) -> None:
        import kuberay_sdk.display as display_mod
        from kuberay_sdk.display import get_backend
        from kuberay_sdk.display._backend import PlainBackend

        display_mod._cached_backend = None

        with (
            patch.dict("os.environ", {"KUBERAY_DISPLAY": "rich"}),
            patch("kuberay_sdk.display._detect.detect_environment", return_value="terminal"),
            patch.dict("sys.modules", {"kuberay_sdk.display._rich_backend": None}),
        ):
            # When RichBackend import fails, should fall back to PlainBackend
            backend = get_backend(override="rich")
            assert isinstance(backend, PlainBackend)
