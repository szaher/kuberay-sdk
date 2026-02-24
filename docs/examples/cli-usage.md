# CLI Usage

*Added in v0.2.0*

Manage Ray resources from the terminal using the `kuberay` command-line tool.

**What this example covers:**

1. Run `kuberay --help` and `kuberay --version` for basic CLI usage
2. List clusters in table and JSON output formats
3. Check cluster capabilities
4. Demonstrate CLI commands via Python's `subprocess` module

!!! note
    Most CLI commands in this example require a running KubeRay cluster. The `--help` and `--version` commands work without a cluster.

[:material-download: Download cli_usage.py](https://github.com/szaher/kuberay-sdk/blob/main/examples/cli_usage.py){ .md-button }

## Source Code

```python title="examples/cli_usage.py"
--8<-- "examples/cli_usage.py"
```
