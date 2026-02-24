# Contract: Configuration File & Environment Variables (US3)

## Public API

### Config file loading

```python
# New function in config.py
def load_config_file(path: str | None = None) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        path: Config file path. Defaults to ~/.kuberay/config.yaml.
              Overridable via KUBERAY_CONFIG env var.

    Returns empty dict if file does not exist.
    Raises ValidationError if file exists but contains invalid YAML or unknown fields.
    """

def load_env_vars() -> dict[str, Any]:
    """Load configuration from KUBERAY_* environment variables.

    Supported vars:
        KUBERAY_NAMESPACE, KUBERAY_TIMEOUT,
        KUBERAY_RETRY_MAX_ATTEMPTS, KUBERAY_RETRY_BACKOFF_FACTOR

    Returns dict with only the keys that have env vars set.
    Raises ValidationError if env var value cannot be parsed (e.g., non-numeric timeout).
    """

def resolve_config(
    explicit: SDKConfig | None = None,
    **overrides: Any,
) -> SDKConfig:
    """Build SDKConfig with full precedence chain.

    Priority: explicit SDKConfig fields > env vars > config file > defaults.
    """
```

### Config file schema

```yaml
# ~/.kuberay/config.yaml
namespace: my-namespace          # string
timeout: 120                     # float (seconds)
retry:
  max_attempts: 5                # int
  backoff_factor: 1.0            # float
```

### Environment variables

| Variable | Maps to | Type |
|----------|---------|------|
| `KUBERAY_CONFIG` | Config file path | `str` |
| `KUBERAY_NAMESPACE` | `SDKConfig.namespace` | `str` |
| `KUBERAY_TIMEOUT` | `SDKConfig.retry_timeout` | `float` |
| `KUBERAY_RETRY_MAX_ATTEMPTS` | `SDKConfig.retry_max_attempts` | `int` |
| `KUBERAY_RETRY_BACKOFF_FACTOR` | `SDKConfig.retry_backoff_factor` | `float` |

### KubeRayClient constructor change

```python
class KubeRayClient:
    def __init__(self, config: SDKConfig | None = None) -> None:
        # If config is None, load from env vars + config file
        self._config = resolve_config(config)
```

## Backward Compatibility

- `KubeRayClient()` with no args works exactly as before if no env vars or config file exist.
- `KubeRayClient(config=SDKConfig(...))` with explicit config ignores file/env for explicitly-set fields.

## Test Contract

```python
def test_env_var_namespace(monkeypatch):
    monkeypatch.setenv("KUBERAY_NAMESPACE", "test-ns")
    config = resolve_config()
    assert config.namespace == "test-ns"

def test_config_file_loading(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("namespace: file-ns\ntimeout: 120\n")
    config = resolve_config()  # with KUBERAY_CONFIG pointing to cfg
    assert config.namespace == "file-ns"

def test_env_overrides_file(monkeypatch, tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("namespace: file-ns\n")
    monkeypatch.setenv("KUBERAY_NAMESPACE", "env-ns")
    config = resolve_config()
    assert config.namespace == "env-ns"

def test_explicit_overrides_all(monkeypatch, tmp_path):
    monkeypatch.setenv("KUBERAY_NAMESPACE", "env-ns")
    config = resolve_config(SDKConfig(namespace="explicit-ns"))
    assert config.namespace == "explicit-ns"

def test_invalid_env_var_raises(monkeypatch):
    monkeypatch.setenv("KUBERAY_TIMEOUT", "not-a-number")
    with pytest.raises(ValidationError):
        resolve_config()
```
