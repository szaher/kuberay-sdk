# Contract: Makefile Interface

**Purpose**: Define the command runner interface that developers use for local development tasks.

## Required Targets

Every target listed below MUST exist in the Makefile at the repository root.

| Target | Description | Exit Code 0 | Exit Code Non-Zero |
|--------|-------------|-------------|---------------------|
| `help` | Print all available targets with descriptions | Always | Never |
| `install` | Install all development dependencies | Dependencies installed | Installation failure |
| `lint` | Run linter + format check | No violations | Violations found |
| `typecheck` | Run type checker | No errors | Type errors found |
| `format` | Auto-fix formatting and lint issues | Fixed | — |
| `test-unit` | Run unit tests only | All pass | Any fail |
| `test-contract` | Run contract tests only | All pass | Any fail |
| `test-integration` | Run integration tests only | All pass | Any fail |
| `test-e2e` | Run e2e tests (requires cluster) | All pass | Any fail |
| `test` | Run unit + contract + integration tests | All pass | Any fail |
| `check` | Run lint + typecheck + test | All pass | Any fail |
| `coverage` | Run unit tests with coverage report | Report generated | Tests fail |
| `build` | Build distribution packages | Artifacts in dist/ | Build failure |
| `clean` | Remove build artifacts and caches | Cleaned | — |

## Behavioral Constraints

- `help` MUST be the default target (runs on bare `make` invocation)
- All targets MUST be `.PHONY`
- All targets MUST use `uv run` to execute in the managed virtual environment
- `test` MUST depend on `test-unit`, `test-contract`, `test-integration`
- `check` MUST depend on `lint`, `typecheck`, `test`
- `check` MUST mirror what CI runs, so local `make check` validates the same checks as a PR

## Output Contract

- `lint` MUST show file paths and line numbers for any violations
- `typecheck` MUST show file paths and line numbers for any type errors
- `test-*` targets MUST show test names and pass/fail status
- `coverage` MUST generate both terminal and HTML coverage reports
- `build` MUST produce `.tar.gz` and `.whl` files in `dist/`
