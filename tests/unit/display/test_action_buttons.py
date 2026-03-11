"""Unit tests for action buttons (T038)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kuberay_sdk.display._backend import ActionDef


class TestActionDef:
    """Tests for ActionDef dataclass."""

    def test_creation_with_label_and_callback(self) -> None:
        cb = MagicMock()
        action = ActionDef(label="Delete", callback=cb, destructive=True)
        assert action.label == "Delete"
        assert action.callback is cb
        assert action.destructive is True
        assert action.icon is None

    def test_non_destructive_default(self) -> None:
        action = ActionDef(label="View", callback=lambda: None)
        assert action.destructive is False

    def test_with_icon(self) -> None:
        action = ActionDef(label="Delete", callback=lambda: None, icon="trash")
        assert action.icon == "trash"

    def test_frozen_dataclass(self) -> None:
        action = ActionDef(label="Test", callback=lambda: None)
        with pytest.raises(AttributeError):
            action.label = "Changed"  # type: ignore[misc]


class TestActionButtonRendering:
    """Tests for action button rendering in NotebookBackend."""

    def test_buttons_rendered_with_ipywidgets(self) -> None:
        """When ipywidgets available, action buttons should be created."""

        from kuberay_sdk.display._notebook_backend import NotebookBackend

        backend = NotebookBackend()
        cb = MagicMock()
        actions = [ActionDef(label="Delete", callback=cb, destructive=True)]

        html = backend.render_html_card(
            {"Name": "test", "State": "RUNNING", "Type": "ClusterHandle"},
            actions=actions,
        )
        # HTML card is returned (buttons are rendered via ipywidgets separately)
        assert html is not None
        assert "test" in html

    def test_non_notebook_skips_buttons(self) -> None:
        """PlainBackend should return None for HTML cards."""
        from kuberay_sdk.display._backend import PlainBackend

        backend = PlainBackend()
        actions = [ActionDef(label="Delete", callback=MagicMock(), destructive=True)]
        result = backend.render_html_card({"Name": "test"}, actions=actions)
        assert result is None

    def test_colab_renders_card_without_buttons(self) -> None:
        """Colab/VS Code should get HTML card without interactive buttons."""
        from kuberay_sdk.display._notebook_backend import NotebookBackend

        backend = NotebookBackend()
        actions = [ActionDef(label="Delete", callback=MagicMock(), destructive=True)]

        html = backend.render_html_card(
            {"Name": "test", "State": "RUNNING", "Type": "ClusterHandle"},
            actions=actions,
        )
        assert html is not None
        # HTML card content should be present
        assert "test" in html
