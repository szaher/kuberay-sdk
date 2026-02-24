# Contract: CLI Tool (US10)

## Entry Point

```
kuberay [OPTIONS] COMMAND [ARGS]
```

Registered as a console script in pyproject.toml:
```toml
[project.scripts]
kuberay = "kuberay_sdk.cli.main:cli"
```

## Command Structure

```
kuberay
├── cluster
│   ├── create NAME [--workers N] [--preset NAME] [--ray-version V] [--namespace NS]
│   ├── list [--namespace NS] [--output json|table]
│   ├── get NAME [--namespace NS] [--output json|table]
│   ├── delete NAME [--namespace NS] [--force]
│   └── scale NAME --workers N [--namespace NS]
├── job
│   ├── create NAME --entrypoint CMD [--cluster NAME] [--namespace NS]
│   ├── list [--namespace NS] [--output json|table]
│   ├── get NAME [--namespace NS] [--output json|table]
│   └── delete NAME [--namespace NS]
├── service
│   ├── create NAME --import-path PATH [--namespace NS]
│   ├── list [--namespace NS] [--output json|table]
│   ├── get NAME [--namespace NS] [--output json|table]
│   └── delete NAME [--namespace NS]
└── capabilities [--namespace NS] [--output json|table]
```

## Global Options

| Flag | Description | Default |
|------|-------------|---------|
| `--namespace`, `-n` | Kubernetes namespace | From config chain |
| `--output`, `-o` | Output format: `table` or `json` | `table` |
| `--config` | Config file path | `~/.kuberay/config.yaml` |
| `--help` | Show help | — |
| `--version` | Show SDK version | — |

## Output Formats

### Table (default)

```
NAME            STATE    WORKERS   AGE
my-cluster      ready    4/4       2h
dev-cluster     creating 0/2       5m
```

### JSON

```json
[
  {"name": "my-cluster", "state": "ready", "workers": "4/4", "age": "2h"},
  {"name": "dev-cluster", "state": "creating", "workers": "0/2", "age": "5m"}
]
```

## Configuration

The CLI reads configuration from the same sources as the SDK:
1. CLI flags (`--namespace`)
2. Environment variables (`KUBERAY_NAMESPACE`)
3. Config file (`~/.kuberay/config.yaml`)
4. Built-in defaults

## Error Output

Errors are printed to stderr with the remediation hint:

```
Error: Ray cluster 'my-cluster' not found in namespace 'default'.

To fix:
  Check cluster name: kubectl get rayclusters -n default
```

## Test Contract

```python
from click.testing import CliRunner
from kuberay_sdk.cli.main import cli

def test_cluster_list(mock_k8s):
    runner = CliRunner()
    result = runner.invoke(cli, ["cluster", "list"])
    assert result.exit_code == 0

def test_cluster_list_json(mock_k8s):
    runner = CliRunner()
    result = runner.invoke(cli, ["cluster", "list", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)

def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "cluster" in result.output
    assert "job" in result.output
```
