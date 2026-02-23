# Contributing to kuberay-sdk

Thank you for your interest in contributing to kuberay-sdk. This guide covers
everything you need to get started.

## Prerequisites

- **Python 3.10+**
- **Make**
- **uv** — fast Python package manager
  ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))

## Quick Start

```bash
git clone https://github.com/szaher/kuberay-sdk.git
cd kuberay-sdk
make install
make check
```

## Development Setup

`make install` runs `uv sync --all-extras`, which installs all project
dependencies including optional extras. The virtual environment is fully managed
by uv — you do not need to create or activate one manually.

## Running Checks

| Command                   | Description                                              |
| ------------------------- | -------------------------------------------------------- |
| `make lint`               | Run linter (ruff)                                        |
| `make typecheck`          | Run type checker (mypy in strict mode)                   |
| `make test`               | Run unit, contract, and integration tests                |
| `make check`              | Run all checks (lint + typecheck + test) — mirrors CI    |
| `make test-unit`          | Run unit tests only                                      |
| `make test-contract`      | Run contract tests only                                  |
| `make test-integration`   | Run integration tests only                               |
| `make coverage`           | Run tests with coverage report                           |
| `make format`             | Auto-fix formatting issues                               |

Always run `make check` before pushing to make sure everything passes locally.

## Branch Naming

Use descriptive branch names with a category prefix:

- `feature/add-gpu-scheduling`
- `fix/cluster-timeout`
- `docs/update-api-reference`
- `refactor/simplify-client-init`

## Commit Messages

All commits must follow the
[Conventional Commits](https://www.conventionalcommits.org/) format:

```
type(scope): description
```

### Types

| Type       | Purpose                                      |
| ---------- | -------------------------------------------- |
| `feat`     | New feature                                  |
| `fix`      | Bug fix                                      |
| `docs`     | Documentation only                           |
| `test`     | Adding or updating tests                     |
| `refactor` | Code change that neither fixes nor adds      |
| `chore`    | Maintenance tasks (deps, config, tooling)    |
| `ci`       | CI/CD configuration changes                  |

### Examples

```
feat(cluster): add GPU scheduling support
fix(client): handle timeout on cluster creation
docs(readme): add quickstart section
test(cluster): add contract tests for scaling API
refactor(auth): simplify token refresh logic
chore(deps): bump pydantic to 2.6
ci(actions): add Python 3.13 to test matrix
```

## Pull Request Process

1. Create a feature branch from `main`.
2. Make your changes.
3. Run `make check` locally and ensure all checks pass.
4. Push your branch and open a PR against `main`.
5. All CI checks must pass — this includes lint, typecheck, and tests across
   Python 3.10, 3.11, 3.12, and 3.13.
6. Request review from a maintainer.

Keep PRs focused. One logical change per PR is preferred over large, sweeping
changes.

## Code Style

- **Linting and formatting**: ruff (configuration lives in `pyproject.toml`).
- **Type checking**: mypy in strict mode.
- **Docstrings**: Google-style docstrings for all public modules, classes, and
  functions.
- **Import ordering**: Managed by ruff's isort rules. Run `make format` to
  auto-sort imports.

## Adding Tests

Tests are organized by category:

| Directory              | Purpose                                               |
| ---------------------- | ----------------------------------------------------- |
| `tests/unit/`          | Unit tests — fast, no external dependencies           |
| `tests/contract/`     | Contract tests — verify API contracts with mocks      |
| `tests/integration/`  | Integration tests — require a running cluster or API  |
| `tests/e2e/`          | End-to-end tests — full workflow validation           |

Place new tests in the appropriate directory. Follow the existing naming
conventions (`test_<module>.py`).

## Project Structure

See [DEVELOPMENT.md](DEVELOPMENT.md) for a detailed breakdown of the project
layout and architecture.

## License

All contributions to this project are made under the
[Apache License 2.0](LICENSE). By submitting a pull request you agree that your
contributions will be licensed under the same terms.
