"""Validate migration guide exists and covers required mappings (US13)."""

from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs" / "user-guide"


class TestMigrationGuide:
    def test_migration_file_exists(self) -> None:
        assert (DOCS_DIR / "migration.md").exists()

    def test_covers_kubectl_mappings(self) -> None:
        content = (DOCS_DIR / "migration.md").read_text()
        assert "kubectl" in content
        assert "client." in content or "KubeRayClient" in content

    def test_has_at_least_ten_mappings(self) -> None:
        content = (DOCS_DIR / "migration.md").read_text()
        # Count kubectl command occurrences as proxy for mappings
        kubectl_count = content.lower().count("kubectl")
        assert kubectl_count >= 10, f"Only {kubectl_count} kubectl references, need at least 10"

    def test_covers_crud_operations(self) -> None:
        content = (DOCS_DIR / "migration.md").read_text().lower()
        for op in ["create", "get", "list", "delete"]:
            assert op in content, f"Missing operation: {op}"
        for resource in ["cluster", "job", "service"]:
            assert resource in content, f"Missing resource type: {resource}"
