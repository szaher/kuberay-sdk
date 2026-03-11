"""Unit tests for PlainBackend (T008)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kuberay_sdk.display._backend import PlainBackend, PlainProgressContext

if TYPE_CHECKING:
    import pytest
from kuberay_sdk.models.progress import ProgressStatus


class TestPlainBackend:
    """Tests for PlainBackend implementation."""

    def test_render_table_produces_aligned_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        backend = PlainBackend()
        backend.render_table(
            ["NAME", "STATE"],
            [["my-cluster", "RUNNING"], ["old-cluster", "FAILED"]],
        )
        output = capsys.readouterr().out
        assert "NAME" in output
        assert "STATE" in output
        assert "my-cluster" in output
        assert "RUNNING" in output

    def test_render_table_matches_format_table_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        from kuberay_sdk.cli.formatters import format_table

        headers = ["NAME", "NAMESPACE", "STATE"]
        rows = [["c1", "default", "RUNNING"]]

        expected = format_table(headers, rows)
        backend = PlainBackend()
        backend.render_table(headers, rows)
        output = capsys.readouterr().out.rstrip("\n")
        assert output == expected

    def test_render_table_with_title(self, capsys: pytest.CaptureFixture[str]) -> None:
        backend = PlainBackend()
        backend.render_table(["NAME"], [["test"]], title="My Title")
        output = capsys.readouterr().out
        assert "My Title" in output
        assert "test" in output

    def test_render_progress_returns_noop_context_manager(self) -> None:
        backend = PlainBackend()
        ctx = backend.render_progress(timeout=60.0)
        assert isinstance(ctx, PlainProgressContext)
        with ctx as p:
            p.update(ProgressStatus(state="CREATING", elapsed_seconds=1.0))
            p.complete("Done")

    def test_render_progress_fail_is_noop(self) -> None:
        ctx = PlainProgressContext()
        with ctx:
            ctx.fail("Something went wrong")
        # No exception, no output

    def test_render_log_line_prints_plain_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        backend = PlainBackend()
        backend.render_log_line("INFO: Hello world")
        output = capsys.readouterr().out
        assert "INFO: Hello world" in output

    def test_render_log_line_with_source(self, capsys: pytest.CaptureFixture[str]) -> None:
        backend = PlainBackend()
        backend.render_log_line("ERROR: oops", source="worker-0")
        output = capsys.readouterr().out
        assert "[worker-0]" in output
        assert "ERROR: oops" in output

    def test_render_html_card_returns_none(self) -> None:
        backend = PlainBackend()
        result = backend.render_html_card({"Name": "test", "State": "RUNNING"})
        assert result is None

    def test_progress_context_exit_returns_false(self) -> None:
        """ProgressContext.__exit__ should return False (never swallow exceptions)."""
        ctx = PlainProgressContext()
        assert ctx.__exit__(None, None, None) is False
