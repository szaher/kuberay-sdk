# Contract: Handle Representations (US4)

## Public API

### ClusterHandle.__repr__

```python
def __repr__(self) -> str:
    """Return concise handle representation.

    Example: ClusterHandle(name='my-cluster', namespace='default')
    """
```

### JobHandle.__repr__

```python
def __repr__(self) -> str:
    """Return concise handle representation.

    Example: JobHandle(name='my-job', namespace='default', mode='CRD')
    """
```

### ServiceHandle.__repr__

```python
def __repr__(self) -> str:
    """Return concise handle representation.

    Example: ServiceHandle(name='my-service', namespace='default')
    """
```

## Implementation Rules

- `__repr__` MUST NOT make any API calls (FR-013).
- Uses only values known at construction time (`name`, `namespace`, `mode`).
- Format: `ClassName(key='value', key='value')` — standard Python repr convention.

## Async Handles

`AsyncClusterHandle`, `AsyncJobHandle`, `AsyncServiceHandle` follow the same pattern.

## Test Contract

```python
def test_cluster_handle_repr():
    handle = ClusterHandle(name="test", namespace="default", client=mock)
    assert repr(handle) == "ClusterHandle(name='test', namespace='default')"

def test_job_handle_repr():
    handle = JobHandle(name="job1", namespace="ns", client=mock, mode="CRD")
    assert repr(handle) == "JobHandle(name='job1', namespace='ns', mode='CRD')"

def test_service_handle_repr():
    handle = ServiceHandle(name="svc1", namespace="ns", client=mock)
    assert repr(handle) == "ServiceHandle(name='svc1', namespace='ns')"
```
