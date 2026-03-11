"""Unit tests for CLI formatter integration (T021)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from kuberay_sdk.cli.formatters import format_table

if TYPE_CHECKING:
    import pytest


class TestCLIFormatterIntegration:
    """Tests for CLI formatter rich backend integration."""

    def test_format_table_still_works_without_rich(self) -> None:
        """format_table() should work as before (plain text)."""
        result = format_table(["NAME", "STATE"], [["c1", "RUNNING"]])
        assert "NAME" in result
        assert "c1" in result

    def test_format_rich_table_uses_backend_when_available(self, capsys: pytest.CaptureFixture[str]) -> None:
        """format_rich_table should use RichBackend when available."""
        from kuberay_sdk.cli.formatters import format_rich_table

        with patch.dict("os.environ", {"KUBERAY_DISPLAY": "plain"}):
            import kuberay_sdk.display as display_mod

            display_mod._cached_backend = None
            format_rich_table(["NAME", "STATE"], [["c1", "RUNNING"]], state_column=1)

        output = capsys.readouterr().out
        assert "NAME" in output
        assert "c1" in output

    def test_json_output_bypasses_rich(self) -> None:
        """--output json should always produce plain JSON."""
        from kuberay_sdk.cli.formatters import format_json

        result = format_json({"name": "c1"})
        assert '"name"' in result
        assert "\x1b[" not in result  # No ANSI codes

    def test_piped_output_has_no_ansi(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Non-TTY output should strip ANSI codes."""
        from kuberay_sdk.cli.formatters import format_rich_table

        with patch.dict("os.environ", {"KUBERAY_DISPLAY": "plain"}):
            import kuberay_sdk.display as display_mod

            display_mod._cached_backend = None
            format_rich_table(["NAME"], [["c1"]])

        output = capsys.readouterr().out
        assert "\x1b[" not in output
