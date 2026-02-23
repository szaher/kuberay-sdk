# Contract: CI Workflow Interface

**Purpose**: Define the GitHub Actions workflow triggers, jobs, and expected behaviors.

## Workflow: ci.yml

**Trigger**: `pull_request` to `main`, `push` to `main`

| Job | Python Version(s) | Depends On | Required Status Check |
|-----|-------------------|------------|----------------------|
| `lint` | 3.10 (minimum supported) | — | Yes |
| `typecheck` | 3.10 (minimum supported) | — | Yes |
| `test` | Matrix: [3.10, 3.11, 3.12, 3.13] | lint, typecheck | Yes |

### Job: lint

| Step | Command | Output |
|------|---------|--------|
| Checkout | actions/checkout@v4 | — |
| Setup Python | actions/setup-python@v5 | — |
| Install uv | astral-sh/setup-uv@v4 | — |
| Install deps | uv sync --all-extras | — |
| Ruff check | uv run ruff check --output-format=github src/ tests/ | GitHub annotations |
| Ruff format check | uv run ruff format --check src/ tests/ | Pass/fail |

### Job: typecheck

| Step | Command | Output |
|------|---------|--------|
| Checkout | actions/checkout@v4 | — |
| Setup Python | actions/setup-python@v5 | — |
| Install uv | astral-sh/setup-uv@v4 | — |
| Install deps | uv sync --all-extras | — |
| Mypy | uv run mypy src/ | Type errors with file/line |

### Job: test (matrix)

| Step | Command | Output |
|------|---------|--------|
| Checkout | actions/checkout@v4 | — |
| Setup Python | actions/setup-python@v5 (matrix version) | — |
| Install uv | astral-sh/setup-uv@v4 | — |
| Install deps | uv sync --all-extras | — |
| Unit tests | uv run pytest tests/unit/ -v --cov=src/kuberay_sdk --cov-report=xml | Test results + coverage XML |
| Contract tests | uv run pytest tests/contract/ -v | Test results |
| Integration tests | uv run pytest tests/integration/ -v | Test results |
| Upload coverage | codecov/codecov-action@v4 (only on 3.12) | Coverage report |

---

## Workflow: release.yml

**Trigger**: `push` tags matching `v*.*.*`

| Job | Depends On | Environment | Permissions |
|-----|------------|-------------|-------------|
| `quality-gate` | — | — | Default |
| `build` | — | — | Default |
| `version-check` | — | — | Default |
| `create-release` | quality-gate, build, version-check | — | contents: write |
| `publish-pypi` | create-release | pypi | id-token: write |

### Job: quality-gate

Runs the same lint + typecheck + test steps as `ci.yml` (on a single Python version 3.12 for speed).

### Job: build

| Step | Command | Output |
|------|---------|--------|
| Checkout | actions/checkout@v4 | — |
| Setup Python | actions/setup-python@v5 | — |
| Install build | pip install build | — |
| Build | python -m build | dist/*.tar.gz, dist/*.whl |
| Upload artifact | actions/upload-artifact@v4 | Artifact: dist |

### Job: version-check

| Step | Logic | Output |
|------|-------|--------|
| Extract tag version | `${GITHUB_REF#refs/tags/v}` | e.g., "0.1.0" |
| Extract package version | `python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"` | e.g., "0.1.0" |
| Compare | If not equal, exit 1 | Pass/fail |

### Job: create-release

| Step | Action | Config |
|------|--------|--------|
| Download dist | actions/download-artifact@v4 | — |
| Create release | softprops/action-gh-release@v2 | generate_release_notes: true, files: dist/* |

### Job: publish-pypi

| Step | Action | Config |
|------|--------|--------|
| Download dist | actions/download-artifact@v4 | — |
| Publish | pypa/gh-action-pypi-publish@release/v1 | Uses OIDC (no secrets) |

---

## Workflow: e2e.yml

**Trigger**: `workflow_dispatch`, `push` to `release/*` branches

| Job | Python Version | Timeout |
|-----|---------------|---------|
| `e2e` | 3.12 | 30 minutes |

### Job: e2e

| Step | Command/Action | Output |
|------|----------------|--------|
| Checkout | actions/checkout@v4 | — |
| Setup Python | actions/setup-python@v5 | — |
| Install uv | astral-sh/setup-uv@v4 | — |
| Install deps | uv sync --all-extras | — |
| Create Kind cluster | helm/kind-action@v1 | kubeconfig configured |
| Add Helm repo | helm repo add kuberay https://ray-project.github.io/kuberay-helm/ | — |
| Install KubeRay | helm install kuberay-operator kuberay/kuberay-operator | Operator running |
| Wait for operator | kubectl wait --for=condition=available deployment/kuberay-operator --timeout=120s | Ready |
| Run e2e tests | uv run pytest tests/e2e/ -v --timeout=300 | Test results |
| Cleanup | kind delete cluster (if: always) | Cluster removed |

---

## Release Notes Configuration: .github/release.yml

```yaml
changelog:
  categories:
    - title: "Breaking Changes"
      labels: ["breaking"]
    - title: "Features"
      labels: ["enhancement", "feature"]
    - title: "Bug Fixes"
      labels: ["bug", "fix"]
    - title: "Documentation"
      labels: ["documentation"]
    - title: "Dependencies"
      labels: ["dependencies"]
    - title: "Other Changes"
      labels: ["*"]
  exclude:
    labels: ["skip-changelog"]
```
