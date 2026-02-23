# Contributing

Thank you for your interest in contributing to kuberay-sdk. This guide covers the development workflow from branch creation to PR merge.

## Branch naming

Branches follow the convention: `<type>/<short-description>`

| Type | Usage |
|---|---|
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `docs/` | Documentation changes |
| `refactor/` | Code restructuring |
| `test/` | Test additions or changes |

Examples: `feature/add-cluster-suspend`, `fix/dashboard-timeout`, `docs/openshift-guide`

## Commit conventions

Commits follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <description>

[optional body]
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`

Examples:

- `feat(client): add cluster suspend/resume support`
- `fix(dashboard): handle timeout on metrics endpoint`
- `docs(guides): add OpenShift hardware profile examples`
- `test(contract): add RayJob CRD schema validation`

## Development workflow

1. **Fork and clone** the repository
2. **Create a branch** from `main`: `git checkout -b feature/my-feature`
3. **Install dev dependencies**: `pip install -e ".[dev]"`
4. **Write tests first** following TDD (see [Testing](testing.md))
5. **Implement the feature** to make tests pass
6. **Run all checks**:

    ```bash
    pytest                        # All tests pass
    ruff check src/ tests/        # No lint errors
    ruff format --check src/ tests/  # Formatting correct
    mypy src/                     # Type checking passes
    ```

7. **Commit** with a conventional commit message
8. **Push** to your fork and open a PR

## Pull request requirements

Every PR must:

- [ ] Pass all tests (`pytest`)
- [ ] Pass linting (`ruff check`)
- [ ] Pass type checking (`mypy src/`)
- [ ] Include tests for new functionality
- [ ] Include docstrings with examples for new public API
- [ ] Follow the existing code patterns and conventions
- [ ] Have a clear title and description

## Code review

- PRs require at least one maintainer approval
- Address review comments with additional commits (don't force-push during review)
- Squash merge is used for final merge to maintain a clean history

## Adding a new public API method

When adding a new method to `KubeRayClient`:

1. Add the method to `KubeRayClient` in `client.py`
2. Add the corresponding async method to `AsyncKubeRayClient` in `async_client.py`
3. If a new model is needed, create it in `models/`
4. If a new service method is needed, add it to the appropriate service in `services/`
5. Write unit tests for the model and service
6. Write a contract test if CRD generation is involved
7. Write an integration test for the end-to-end flow
8. Update docstrings with examples
9. The API reference is auto-generated — no manual docs update needed

## Reporting issues

Found a bug? Have a feature request? [Open an issue](https://github.com/szaher/kuberay-sdk/issues/new) with:

- A clear title describing the problem
- Steps to reproduce (for bugs)
- Expected vs. actual behavior
- Python version and SDK version
