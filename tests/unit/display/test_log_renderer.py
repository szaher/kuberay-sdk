"""Unit tests for log rendering (T033)."""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest

from kuberay_sdk.display._log_renderer import parse_log_level


class TestParseLogLevel:
    """Tests for log level detection."""

    def test_detects_info(self) -> None:
        assert parse_log_level("2024-01-01 INFO Starting server") == "INFO"

    def test_detects_warning(self) -> None:
        assert parse_log_level("WARNING: Disk space low") == "WARNING"

    def test_detects_warn_as_warning(self) -> None:
        assert parse_log_level("WARN: Something happened") == "WARNING"

    def test_detects_error(self) -> None:
        assert parse_log_level("ERROR: Connection failed") == "ERROR"

    def test_detects_critical(self) -> None:
        assert parse_log_level("CRITICAL: System crash") == "CRITICAL"

    def test_detects_debug(self) -> None:
        assert parse_log_level("DEBUG: Variable x = 5") == "DEBUG"

    def test_defaults_to_info(self) -> None:
        assert parse_log_level("Just some output") == "INFO"

    def test_case_insensitive(self) -> None:
        assert parse_log_level("error: something broke") == "ERROR"


class TestSourceLabel:
    """Tests for source label formatting."""

    def test_format_source_label(self) -> None:
        from kuberay_sdk.display._log_renderer import format_source_label

        assert format_source_label("head") == "[head]"
        assert format_source_label("worker-0") == "[worker-0]"


class TestRichBackendLogRendering:
    """Tests for RichBackend.render_log_line()."""

    def test_colorizes_by_level(self) -> None:
        from rich.console import Console

        from kuberay_sdk.display._rich_backend import RichBackend

        backend = RichBackend()
        buf = io.StringIO()
        backend._console = Console(file=buf, force_terminal=True, width=120)

        backend.render_log_line("ERROR: Something failed")
        output = buf.getvalue()
        assert "ERROR" in output

    def test_source_label_prefix(self) -> None:
        from rich.console import Console

        from kuberay_sdk.display._rich_backend import RichBackend

        backend = RichBackend()
        buf = io.StringIO()
        backend._console = Console(file=buf, force_terminal=False, width=120)

        backend.render_log_line("INFO: Ready", source="head")
        output = buf.getvalue()
        assert "[head]" in output

    def test_non_tty_strips_ansi(self) -> None:
        from rich.console import Console

        from kuberay_sdk.display._rich_backend import RichBackend

        backend = RichBackend()
        buf = io.StringIO()
        backend._console = Console(file=buf, force_terminal=False, width=120)

        backend.render_log_line("ERROR: test")
        output = buf.getvalue()
        assert "\x1b[" not in output


class TestNotebookBackendLogRendering:
    """Tests for NotebookBackend.render_log_line()."""

    def test_produces_html_with_color(self) -> None:
        from kuberay_sdk.display._notebook_backend import NotebookBackend

        backend = NotebookBackend()
        with patch("kuberay_sdk.display._notebook_backend._ipython_display") as mock_display:
            backend.render_log_line("ERROR: test failure")
            html = mock_display.call_args[0][0].data
            assert "ERROR" in html
            assert "#dc3545" in html  # red

    def test_source_label_in_html(self) -> None:
        from kuberay_sdk.display._notebook_backend import NotebookBackend

        backend = NotebookBackend()
        with patch("kuberay_sdk.display._notebook_backend._ipython_display") as mock_display:
            backend.render_log_line("INFO: Ready", source="worker-0")
            html = mock_display.call_args[0][0].data
            assert "[worker-0]" in html


class TestPlainBackendLogRendering:
    """Tests for PlainBackend.render_log_line()."""

    def test_prints_plain_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        from kuberay_sdk.display._backend import PlainBackend

        backend = PlainBackend()
        backend.render_log_line("INFO: Hello world")
        output = capsys.readouterr().out
        assert "INFO: Hello world" in output
