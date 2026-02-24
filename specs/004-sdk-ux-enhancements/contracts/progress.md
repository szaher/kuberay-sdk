# Contract: Progress Feedback (US2)

## Public API

### ProgressStatus model

```python
from pydantic import BaseModel

class ProgressStatus(BaseModel):
    """Status update passed to progress callbacks during wait operations."""
    state: str               # Current resource state
    elapsed_seconds: float   # Time since wait started
    message: str = ""        # Human-readable status message
    metadata: dict[str, Any] = {}  # Additional context
```

### Modified wait methods

```python
# ClusterHandle
def wait_until_ready(
    self,
    timeout: float = 300,
    progress_callback: Callable[[ProgressStatus], None] | None = None,
) -> None: ...

# JobHandle
def wait(
    self,
    timeout: float = 3600,
    progress_callback: Callable[[ProgressStatus], None] | None = None,
) -> Any: ...

# AsyncClusterHandle
async def wait_until_ready(
    self,
    timeout: float = 300,
    progress_callback: Callable[[ProgressStatus], None] | None = None,
) -> None: ...

# AsyncJobHandle
async def wait(
    self,
    timeout: float = 3600,
    progress_callback: Callable[[ProgressStatus], None] | None = None,
) -> Any: ...
```

### Callback Invocation

- Callback is invoked every poll cycle (5-10 seconds).
- Callback receives a `ProgressStatus` with current state, elapsed time, and a human-readable message.
- If callback raises an exception, it is logged and the wait continues (callback errors must not abort the wait).

### TimeoutError enhancement

```python
class TimeoutError(KubeRayError):
    def __init__(self, operation: str, timeout: float, last_status: ProgressStatus | None = None):
        ...
        self.last_status = last_status
```

## Backward Compatibility

- `progress_callback=None` (default) preserves current silent behavior.
- `TimeoutError.last_status` defaults to `None` for existing codepaths.

## Test Contract

```python
def test_callback_invoked_during_wait():
    """Callback is called at least once during a wait operation."""
    statuses = []
    cluster.wait_until_ready(timeout=30, progress_callback=statuses.append)
    assert len(statuses) > 0
    assert all(isinstance(s, ProgressStatus) for s in statuses)

def test_no_callback_silent():
    """Without callback, wait behaves as before (no output)."""
    cluster.wait_until_ready(timeout=30)  # no exception, no output

def test_timeout_includes_last_status():
    """TimeoutError includes the last known resource status."""
    with pytest.raises(TimeoutError) as exc_info:
        cluster.wait_until_ready(timeout=1)
    assert exc_info.value.last_status is not None
```
