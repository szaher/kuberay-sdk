# Quickstart Scenarios: CI Pipeline, Release Automation & Developer Guides

## Scenario 1: Run All Checks Locally (US3)

**Goal**: Verify all quality checks pass locally before pushing a PR.

```bash
# Clone and setup
git clone https://github.com/szaher/kuberay-sdk.git
cd kuberay-sdk
make install

# Run all checks (lint + typecheck + tests)
make check
```

**Expected**: All checks pass. Output shows lint OK, typecheck OK, unit/contract/integration tests pass.

## Scenario 2: Run Individual Test Categories (US3)

**Goal**: Run only specific test categories during development.

```bash
# Only unit tests
make test-unit

# Only contract tests
make test-contract

# Only integration tests
make test-integration

# Only linting
make lint

# Only type checking
make typecheck
```

**Expected**: Each command runs only its category and reports pass/fail independently.

## Scenario 3: PR Quality Gate (US1 + US2)

**Goal**: Open a PR and verify CI runs all quality checks.

1. Create a branch, make a change, push, open PR against `main`
2. Verify CI triggers automatically
3. Check the PR status checks:
   - `lint` — passes/fails independently
   - `typecheck` — passes/fails independently
   - `test (3.10)` — passes/fails independently
   - `test (3.11)` — passes/fails independently
   - `test (3.12)` — passes/fails independently
   - `test (3.13)` — passes/fails independently
4. If any check fails, inspect the logs for file paths and line numbers

**Expected**: All 6 status checks appear. PR cannot be merged if any check fails.

## Scenario 4: Lint Violation Detection (US1)

**Goal**: Verify CI catches linting violations.

1. Introduce a linting violation (e.g., add `import os` without using it)
2. Push to a PR branch
3. Check the `lint` status check

**Expected**: `lint` job fails. Error output shows the specific file, line number, and violation code.

## Scenario 5: Release and PyPI Publishing (US4)

**Goal**: Publish a release to PyPI via tag push.

1. Update version in `pyproject.toml` to `0.2.0`
2. Commit and merge to `main`
3. Create and push tag: `git tag v0.2.0 && git push origin v0.2.0`
4. Watch the `release.yml` workflow:
   - Quality gate runs (lint + typecheck + tests)
   - Version check validates tag matches pyproject.toml
   - Build creates distribution artifacts
   - GitHub Release created with auto-generated notes
   - Package published to PyPI via OIDC
5. Verify: `pip install kuberay-sdk==0.2.0`

**Expected**: Package available on PyPI. GitHub Release shows categorized PR summaries.

## Scenario 6: Version Mismatch Detection (US4 — Edge Case)

**Goal**: Verify the release pipeline rejects mismatched versions.

1. pyproject.toml has `version = "0.1.0"`
2. Push tag `v0.2.0`
3. Watch the `release.yml` workflow

**Expected**: `version-check` job fails with clear error: tag version `0.2.0` does not match package version `0.1.0`. No release created, no PyPI publish.

## Scenario 7: E2E Test Execution (US5)

**Goal**: Run e2e tests against a real Kubernetes cluster.

1. Navigate to Actions tab → `e2e.yml` workflow
2. Click "Run workflow" → select branch → run
3. Watch the workflow:
   - Kind cluster provisioned
   - KubeRay operator installed via Helm
   - E2E tests run against the cluster
   - Cluster cleaned up

**Expected**: E2E tests pass. Cluster is deleted regardless of test outcome.

## Scenario 8: New Contributor Onboarding (US3)

**Goal**: A new contributor sets up the development environment from scratch.

1. Read CONTRIBUTING.md
2. Follow setup instructions:
   ```bash
   git clone https://github.com/szaher/kuberay-sdk.git
   cd kuberay-sdk
   make install
   make check
   ```
3. Read DEVELOPMENT.md for project structure understanding
4. Create a feature branch following naming convention
5. Make a change, run `make check` locally
6. Push and open PR

**Expected**: Contributor successfully sets up environment, runs checks, and opens a PR without external help.

## Scenario 9: Fork PR Security (Edge Case)

**Goal**: Verify fork PRs cannot access secrets.

1. Fork the repository
2. Open a PR from the fork
3. Verify CI runs lint, typecheck, and tests
4. Verify the PR does NOT trigger release or publish workflows

**Expected**: Quality checks run normally. No access to `pypi` environment or repository secrets.

## Scenario 10: Coverage Reporting (US2)

**Goal**: Verify test coverage is measured and reported.

1. Open a PR with code changes
2. Check CI test job output
3. Look for coverage report in job logs or PR comment

**Expected**: Coverage percentage reported for unit tests. Coverage XML artifact uploaded.
