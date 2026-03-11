"""Unit tests for RichBackend table rendering (T020)."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    import pytest

from kuberay_sdk.display._rich_backend import RichBackend


class TestRichBackendTable:
    """Tests for RichBackend.render_table()."""

    def test_render_table_produces_styled_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        backend = RichBackend()
        backend.render_table(
            ["NAME", "STATE"],
            [["my-cluster", "RUNNING"]],
        )
        output = capsys.readouterr().out
        assert "NAME" in output
        assert "my-cluster" in output

    def test_state_column_values_are_color_coded(self) -> None:
        """State column should have color markup applied."""
        backend = RichBackend()
        # Capture rich output to a string buffer
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=True, width=80)
        backend._console = console

        backend.render_table(
            ["NAME", "STATE"],
            [["c1", "RUNNING"], ["c2", "FAILED"]],
            state_column=1,
        )
        output = buf.getvalue()
        # Rich terminal output should contain ANSI color codes
        assert "RUNNING" in output
        assert "FAILED" in output

    def test_non_tty_output_strips_ansi(self) -> None:
        """Non-TTY output should have no ANSI escape codes."""
        backend = RichBackend()
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=False, width=80)
        backend._console = console

        backend.render_table(
            ["NAME", "STATE"],
            [["c1", "RUNNING"]],
            state_column=1,
        )
        output = buf.getvalue()
        # Should not contain ANSI escape sequences
        assert "\x1b[" not in output
        assert "RUNNING" in output

    def test_render_table_with_title(self) -> None:
        backend = RichBackend()
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=False, width=80)
        backend._console = console

        backend.render_table(
            ["NAME"],
            [["test"]],
            title="My Table",
        )
        output = buf.getvalue()
        assert "My Table" in output

    def test_render_table_without_state_column(self) -> None:
        """No state_column should produce no color coding."""
        backend = RichBackend()
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=False, width=80)
        backend._console = console

        backend.render_table(
            ["NAME", "VALUE"],
            [["a", "b"]],
        )
        output = buf.getvalue()
        assert "NAME" in output
        assert "a" in output
