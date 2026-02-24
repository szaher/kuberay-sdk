"""Unit tests for config file and environment variable support (T017).

Tests for load_config_file, load_env_vars, and resolve_config functions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kuberay_sdk.config import SDKConfig, load_config_file, load_env_vars, resolve_config

# ── load_config_file tests ──


class TestLoadConfigFile:
    """Tests for load_config_file()."""

    def test_load_config_file_returns_dict(self, tmp_path: Path) -> None:
        """Create a temp YAML file, load it, verify dict returned."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "namespace: ml-team\n"
            "timeout: 120\n"
            "retry:\n"
            "  max_attempts: 5\n"
            "  backoff_factor: 1.0\n"
        )

        result = load_config_file(config_file)

        assert isinstance(result, dict)
        assert result["namespace"] == "ml-team"
        assert result["timeout"] == 120
        assert result["retry"]["max_attempts"] == 5
        assert result["retry"]["backoff_factor"] == 1.0

    def test_load_config_file_missing_returns_empty(self, tmp_path: Path) -> None:
        """No file = empty dict, no error."""
        missing_path = tmp_path / "nonexistent" / "config.yaml"

        result = load_config_file(missing_path)

        assert result == {}

    def test_load_config_file_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Invalid YAML content raises an error."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(":\n  :\n  - [invalid{yaml")

        with pytest.raises(Exception):
            load_config_file(config_file)

    def test_load_config_file_custom_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """KUBERAY_CONFIG env var overrides default path."""
        custom_config = tmp_path / "custom" / "my-config.yaml"
        custom_config.parent.mkdir(parents=True, exist_ok=True)
        custom_config.write_text("namespace: custom-ns\n")

        monkeypatch.setenv("KUBERAY_CONFIG", str(custom_config))

        # Call without explicit path; should use KUBERAY_CONFIG env var
        result = load_config_file()

        assert result["namespace"] == "custom-ns"

    def test_load_config_file_empty_yaml_returns_empty(self, tmp_path: Path) -> None:
        """Empty YAML file returns empty dict."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")

        result = load_config_file(config_file)

        assert result == {}

    def test_load_config_file_non_mapping_raises(self, tmp_path: Path) -> None:
        """YAML file with a list (not mapping) raises ValueError."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("- item1\n- item2\n")

        with pytest.raises(ValueError, match="expected YAML mapping"):
            load_config_file(config_file)

    def test_load_config_file_explicit_path_ignores_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit path parameter takes precedence over KUBERAY_CONFIG env var."""
        env_config = tmp_path / "env-config.yaml"
        env_config.write_text("namespace: from-env\n")

        explicit_config = tmp_path / "explicit-config.yaml"
        explicit_config.write_text("namespace: from-explicit\n")

        monkeypatch.setenv("KUBERAY_CONFIG", str(env_config))

        result = load_config_file(explicit_config)

        assert result["namespace"] == "from-explicit"

    def test_load_config_file_default_path_when_no_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When no path and no env var, uses default ~/.kuberay/config.yaml (which likely doesn't exist)."""
        monkeypatch.delenv("KUBERAY_CONFIG", raising=False)

        # Default path (~/.kuberay/config.yaml) likely doesn't exist in test environment
        result = load_config_file()

        assert isinstance(result, dict)


# ── load_env_vars tests ──


class TestLoadEnvVars:
    """Tests for load_env_vars()."""

    def test_load_env_vars_namespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set KUBERAY_NAMESPACE, verify loaded."""
        monkeypatch.setenv("KUBERAY_NAMESPACE", "test-ns")

        result = load_env_vars()

        assert result["namespace"] == "test-ns"

    def test_load_env_vars_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set KUBERAY_TIMEOUT, verify parsed as float."""
        monkeypatch.setenv("KUBERAY_TIMEOUT", "90.5")

        result = load_env_vars()

        assert result["retry_timeout"] == 90.5
        assert isinstance(result["retry_timeout"], float)

    def test_load_env_vars_retry_max(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set KUBERAY_RETRY_MAX_ATTEMPTS, verify parsed as int."""
        monkeypatch.setenv("KUBERAY_RETRY_MAX_ATTEMPTS", "7")

        result = load_env_vars()

        assert result["retry_max_attempts"] == 7
        assert isinstance(result["retry_max_attempts"], int)

    def test_load_env_vars_retry_backoff(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set KUBERAY_RETRY_BACKOFF_FACTOR, verify parsed as float."""
        monkeypatch.setenv("KUBERAY_RETRY_BACKOFF_FACTOR", "2.5")

        result = load_env_vars()

        assert result["retry_backoff_factor"] == 2.5
        assert isinstance(result["retry_backoff_factor"], float)

    def test_load_env_vars_no_env_returns_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No env vars = empty dict."""
        monkeypatch.delenv("KUBERAY_NAMESPACE", raising=False)
        monkeypatch.delenv("KUBERAY_TIMEOUT", raising=False)
        monkeypatch.delenv("KUBERAY_RETRY_MAX_ATTEMPTS", raising=False)
        monkeypatch.delenv("KUBERAY_RETRY_BACKOFF_FACTOR", raising=False)

        result = load_env_vars()

        assert result == {}

    def test_load_env_vars_invalid_timeout_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """KUBERAY_TIMEOUT=abc raises ValueError."""
        monkeypatch.setenv("KUBERAY_TIMEOUT", "abc")

        with pytest.raises(ValueError, match="KUBERAY_TIMEOUT"):
            load_env_vars()

    def test_load_env_vars_invalid_max_attempts_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """KUBERAY_RETRY_MAX_ATTEMPTS=xyz raises ValueError."""
        monkeypatch.setenv("KUBERAY_RETRY_MAX_ATTEMPTS", "xyz")

        with pytest.raises(ValueError, match="KUBERAY_RETRY_MAX_ATTEMPTS"):
            load_env_vars()

    def test_load_env_vars_invalid_backoff_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """KUBERAY_RETRY_BACKOFF_FACTOR=bad raises ValueError."""
        monkeypatch.setenv("KUBERAY_RETRY_BACKOFF_FACTOR", "bad")

        with pytest.raises(ValueError, match="KUBERAY_RETRY_BACKOFF_FACTOR"):
            load_env_vars()

    def test_load_env_vars_all_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """All KUBERAY_* env vars set, all loaded correctly."""
        monkeypatch.setenv("KUBERAY_NAMESPACE", "all-ns")
        monkeypatch.setenv("KUBERAY_TIMEOUT", "200")
        monkeypatch.setenv("KUBERAY_RETRY_MAX_ATTEMPTS", "10")
        monkeypatch.setenv("KUBERAY_RETRY_BACKOFF_FACTOR", "3.0")

        result = load_env_vars()

        assert result["namespace"] == "all-ns"
        assert result["retry_timeout"] == 200.0
        assert result["retry_max_attempts"] == 10
        assert result["retry_backoff_factor"] == 3.0


# ── resolve_config tests ──


class TestResolveConfig:
    """Tests for resolve_config()."""

    def test_resolve_config_explicit_wins(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit SDKConfig values beat env/file."""
        # Set up file config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("namespace: from-file\ntimeout: 100\n")
        monkeypatch.setenv("KUBERAY_CONFIG", str(config_file))

        # Set up env vars
        monkeypatch.setenv("KUBERAY_NAMESPACE", "from-env")

        # Explicit config should win
        explicit = SDKConfig(namespace="from-explicit", retry_timeout=42.0)
        result = resolve_config(explicit)

        assert result.namespace == "from-explicit"
        assert result.retry_timeout == 42.0
        assert result is explicit

    def test_resolve_config_env_over_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Env var overrides file value."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("namespace: from-file\ntimeout: 100\n")
        monkeypatch.setenv("KUBERAY_CONFIG", str(config_file))

        # Env var should override file
        monkeypatch.setenv("KUBERAY_NAMESPACE", "from-env")

        result = resolve_config(None)

        assert result.namespace == "from-env"
        # timeout from file should still apply
        assert result.retry_timeout == 100.0

    def test_resolve_config_file_over_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """File value overrides SDKConfig defaults."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "namespace: from-file\n"
            "timeout: 200\n"
            "retry:\n"
            "  max_attempts: 8\n"
            "  backoff_factor: 2.0\n"
        )
        monkeypatch.setenv("KUBERAY_CONFIG", str(config_file))

        # Clear env vars
        monkeypatch.delenv("KUBERAY_NAMESPACE", raising=False)
        monkeypatch.delenv("KUBERAY_TIMEOUT", raising=False)
        monkeypatch.delenv("KUBERAY_RETRY_MAX_ATTEMPTS", raising=False)
        monkeypatch.delenv("KUBERAY_RETRY_BACKOFF_FACTOR", raising=False)

        result = resolve_config(None)

        assert result.namespace == "from-file"
        assert result.retry_timeout == 200.0
        assert result.retry_max_attempts == 8
        assert result.retry_backoff_factor == 2.0

    def test_resolve_config_defaults_when_nothing_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Defaults from SDKConfig when no file or env vars."""
        # Point to a non-existent config file
        monkeypatch.setenv("KUBERAY_CONFIG", "/tmp/nonexistent/config.yaml")
        monkeypatch.delenv("KUBERAY_NAMESPACE", raising=False)
        monkeypatch.delenv("KUBERAY_TIMEOUT", raising=False)
        monkeypatch.delenv("KUBERAY_RETRY_MAX_ATTEMPTS", raising=False)
        monkeypatch.delenv("KUBERAY_RETRY_BACKOFF_FACTOR", raising=False)

        result = resolve_config(None)

        # Should match SDKConfig defaults
        defaults = SDKConfig()
        assert result.namespace == defaults.namespace
        assert result.retry_timeout == defaults.retry_timeout
        assert result.retry_max_attempts == defaults.retry_max_attempts
        assert result.retry_backoff_factor == defaults.retry_backoff_factor

    def test_resolve_config_none_returns_resolved(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """resolve_config(None) returns SDKConfig with file+env merged."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("namespace: file-ns\ntimeout: 30\n")
        monkeypatch.setenv("KUBERAY_CONFIG", str(config_file))
        monkeypatch.setenv("KUBERAY_RETRY_MAX_ATTEMPTS", "12")
        monkeypatch.delenv("KUBERAY_NAMESPACE", raising=False)
        monkeypatch.delenv("KUBERAY_TIMEOUT", raising=False)
        monkeypatch.delenv("KUBERAY_RETRY_BACKOFF_FACTOR", raising=False)

        result = resolve_config(None)

        assert isinstance(result, SDKConfig)
        assert result.namespace == "file-ns"  # from file
        assert result.retry_timeout == 30.0  # from file
        assert result.retry_max_attempts == 12  # from env (overrides default)

    def test_resolve_config_partial_file_uses_defaults_for_rest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Partial file config fills in what it has; rest uses defaults."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("namespace: partial-ns\n")
        monkeypatch.setenv("KUBERAY_CONFIG", str(config_file))
        monkeypatch.delenv("KUBERAY_NAMESPACE", raising=False)
        monkeypatch.delenv("KUBERAY_TIMEOUT", raising=False)
        monkeypatch.delenv("KUBERAY_RETRY_MAX_ATTEMPTS", raising=False)
        monkeypatch.delenv("KUBERAY_RETRY_BACKOFF_FACTOR", raising=False)

        result = resolve_config(None)

        assert result.namespace == "partial-ns"
        # Rest should be defaults
        defaults = SDKConfig()
        assert result.retry_timeout == defaults.retry_timeout
        assert result.retry_max_attempts == defaults.retry_max_attempts
        assert result.retry_backoff_factor == defaults.retry_backoff_factor

    def test_resolve_config_env_only_no_file(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Only env vars set, no config file."""
        monkeypatch.setenv("KUBERAY_CONFIG", "/tmp/nonexistent/config.yaml")
        monkeypatch.setenv("KUBERAY_NAMESPACE", "env-only-ns")
        monkeypatch.setenv("KUBERAY_TIMEOUT", "55.5")

        result = resolve_config(None)

        assert result.namespace == "env-only-ns"
        assert result.retry_timeout == 55.5
