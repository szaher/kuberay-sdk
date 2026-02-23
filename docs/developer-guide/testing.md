# Testing

kuberay-sdk uses pytest with three test categories: unit, contract, and integration tests.

## Running tests

```bash
# Run all tests
pytest

# Run with concise output
pytest --tb=short -q

# Skip integration tests
pytest -m "not integration"

# Run a specific test file
pytest tests/unit/test_cluster_config.py

# Run a specific test
pytest tests/unit/test_cluster_config.py::test_simple_mode_creates_default_worker_group
```

## Test categories

### Unit tests (`tests/unit/`)

Test individual functions and classes in isolation. These test Pydantic model validation, CRD generation, error translation, namespace resolution, and retry logic.

```bash
pytest tests/unit/
```

### Contract tests (`tests/contract/`)

Verify that SDK-generated Kubernetes CRD manifests match expected schemas. These tests validate that `ClusterConfig.to_crd_dict()`, `JobConfig.to_crd_dict()`, and `ServiceConfig.to_crd_dict()` produce valid KubeRay manifests.

```bash
pytest tests/contract/
```

### Integration tests (`tests/integration/`)

Test end-to-end workflows with mocked Kubernetes API responses. These use `pytest-httpx` for Dashboard API mocking and mock `CustomObjectsApi` for K8s calls.

```bash
pytest tests/integration/
```

## Test file conventions

- Test files mirror the source structure: `src/kuberay_sdk/client.py` → `tests/unit/test_client.py`
- Test function names follow the pattern: `test_<method>_<scenario>_<expected_outcome>`
- Example: `test_create_cluster_with_queue_injects_kueue_label`

## Shared fixtures

Common fixtures are defined in `tests/conftest.py`:

- `mock_k8s_client` — a mocked `kubernetes.client.ApiClient`
- `mock_custom_api` — a mocked `CustomObjectsApi`
- `sdk_config` — a default `SDKConfig` for testing
- `sample_cluster_cr` — a sample RayCluster CR response dict

## Async tests

Async tests use `pytest-asyncio` with `asyncio_mode = "auto"` (configured in `pyproject.toml`):

```python
async def test_async_create_cluster():
    client = AsyncKubeRayClient(config=SDKConfig(...))
    cluster = await client.create_cluster("test", workers=2)
    assert cluster.name == "test"
```

## Writing new tests

1. Identify the test category (unit, contract, or integration)
2. Create or extend the test file matching the source module
3. Write the test function following the naming convention
4. Use shared fixtures from `conftest.py`
5. Run the test to confirm it passes: `pytest tests/unit/test_your_module.py -v`

## Coverage

```bash
pytest --cov=kuberay_sdk --cov-report=term-missing
```
