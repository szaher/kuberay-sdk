# Development Setup

This guide walks you through setting up a local development environment for contributing to kuberay-sdk.

## Prerequisites

- Python 3.10+
- Git
- A terminal with shell access

## Clone the repository

```bash
git clone https://github.com/szaher/kuberay-sdk.git
cd kuberay-sdk
```

## Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

## Install dev dependencies

```bash
pip install -e ".[dev]"
```

This installs the SDK in editable mode along with all development tools (pytest, ruff, mypy).

## Verify the setup

Run the test suite to confirm everything works:

```bash
pytest
```

You should see all tests pass. The test suite includes unit tests, contract tests, and mock-based integration tests.

## Install docs dependencies (optional)

If you're working on documentation:

```bash
pip install -e ".[docs]"
mkdocs serve  # Preview at http://127.0.0.1:8000
```

## Project layout

```
kuberay-sdk/
├── src/kuberay_sdk/     # SDK source code
├── tests/               # Test suite
│   ├── unit/            # Unit tests
│   ├── contract/        # CRD schema contract tests
│   └── integration/     # Integration tests (mocked K8s API)
├── examples/            # Example scripts and notebooks
├── docs/                # Documentation source (MkDocs)
├── pyproject.toml       # Project config (deps, ruff, mypy, pytest)
└── mkdocs.yml           # MkDocs configuration
```

## IDE setup

### VS Code

Recommended extensions:

- Python (ms-python.python)
- Ruff (charliermarsh.ruff)
- Mypy Type Checker (ms-python.mypy-type-checker)

### PyCharm

- Mark `src/` as Sources Root
- Mark `tests/` as Test Sources Root
- Enable mypy integration in Settings > Python Integrated Tools

## Next steps

- [Testing](testing.md) — how to run tests and write new ones
- [Code Style](code-style.md) — linting and formatting conventions
- [Contributing](contributing.md) — branch naming, commits, PR process
