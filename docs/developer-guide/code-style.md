# Code Style

kuberay-sdk enforces consistent code style through automated tooling. All code must pass ruff linting, ruff formatting, and mypy type checking.

## Linting with ruff

[Ruff](https://docs.astral.sh/ruff/) handles both linting and formatting:

```bash
# Lint
ruff check src/ tests/

# Auto-fix lint issues
ruff check --fix src/ tests/

# Format check
ruff format --check src/ tests/

# Auto-format
ruff format src/ tests/
```

### Enabled rule sets

The project enables these ruff rule sets (configured in `pyproject.toml`):

| Rule Set | Description |
|---|---|
| `E`, `W` | pycodestyle errors and warnings |
| `F` | pyflakes |
| `I` | isort (import sorting) |
| `N` | PEP 8 naming |
| `UP` | pyupgrade (modernize syntax for Python 3.10+) |
| `B` | flake8-bugbear |
| `SIM` | flake8-simplify |
| `TCH` | flake8-type-checking |
| `RUF` | ruff-specific rules |

### Configuration

- **Target**: Python 3.10 (`target-version = "py310"`)
- **Line length**: 120 characters
- **Import sorting**: `kuberay_sdk` is classified as first-party

## Type checking with mypy

[mypy](https://mypy-lang.org/) runs in strict mode:

```bash
mypy src/
```

### Configuration

From `pyproject.toml`:

- `strict = true` — all strict checks enabled
- `disallow_untyped_defs = true` — every function must have type annotations
- `warn_return_any = false` — relaxed for K8s API interactions that return `Any`
- External packages (`kubernetes`, `kube_authkit`) have `ignore_missing_imports = true`

## Docstring conventions

All public classes, methods, and functions must have Google-style docstrings:

```python
def create_cluster(
    self,
    name: str,
    *,
    workers: int = 1,
) -> ClusterHandle:
    """Create a RayCluster.

    Args:
        name: Cluster name. Must be lowercase alphanumeric with hyphens.
        workers: Number of worker replicas.

    Returns:
        A ClusterHandle bound to the created cluster.

    Raises:
        ValidationError: If the name is invalid.
        ClusterAlreadyExistsError: If a cluster with this name already exists.

    Example:
        >>> cluster = client.create_cluster("my-cluster", workers=4)
    """
```

### Docstring requirements

- Every public class and method must have a docstring
- Docstrings must include at least one `Example` block
- Complex methods should include `Args`, `Returns`, and `Raises` sections
- Keep the first line concise (summary line)

## Import ordering

Imports follow the isort convention enforced by ruff:

1. Standard library imports
2. Third-party imports
3. First-party imports (`kuberay_sdk`)

```python
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from kuberay_sdk.errors import ValidationError
```
