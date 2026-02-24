# Configuration File & Environment Variables

*Added in v0.2.0*

Load SDK settings from a YAML config file and environment variables, eliminating repeated `SDKConfig` boilerplate.

**What this example covers:**

1. Show built-in defaults from `SDKConfig()`
2. Create and load a temporary YAML config file
3. Override config values with `KUBERAY_*` environment variables
4. Demonstrate the full precedence chain (explicit > env > file > defaults)

[:material-download: Download config_and_env_vars.py](https://github.com/szaher/kuberay-sdk/blob/main/examples/config_and_env_vars.py){ .md-button }

## Source Code

```python title="examples/config_and_env_vars.py"
--8<-- "examples/config_and_env_vars.py"
```
