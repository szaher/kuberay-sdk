"""Validate troubleshooting documentation exists and covers required issues (US12)."""

from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs" / "user-guide"


class TestTroubleshootingDoc:
    def test_troubleshooting_file_exists(self) -> None:
        assert (DOCS_DIR / "troubleshooting.md").exists()

    def test_covers_minimum_issues(self) -> None:
        content = (DOCS_DIR / "troubleshooting.md").read_text()
        issues = [
            "cluster stuck",
            "dashboard unreachable",
            "authentication",
            "operator not found",
            "job timeout",
        ]
        for issue in issues:
            assert issue.lower() in content.lower(), f"Missing coverage for: {issue}"

    def test_has_at_least_five_sections(self) -> None:
        content = (DOCS_DIR / "troubleshooting.md").read_text()
        headings = [line for line in content.split("\n") if line.startswith("## ") or line.startswith("### ")]
        # At least title + 5 issue sections
        assert len(headings) >= 5
