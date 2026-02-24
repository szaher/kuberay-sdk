# Contract: Preset Configurations (US7)

## Public API

### Preset model

```python
from pydantic import BaseModel

class Preset(BaseModel):
    """Named cluster configuration preset."""
    name: str
    description: str = ""
    workers: int = 1
    head_cpu: str = "1"
    head_memory: str = "2Gi"
    worker_cpu: str = "1"
    worker_memory: str = "2Gi"
    worker_gpu: int = 0
    ray_version: str = "2.41.0"
```

### Preset registry

```python
def get_preset(name: str) -> Preset:
    """Look up a built-in preset by name.
    Raises ValueError if not found.
    """

def list_presets() -> list[Preset]:
    """Return all built-in presets."""
```

### Built-in presets

| Name | Workers | CPU | Memory | GPU | Description |
|------|---------|-----|--------|-----|-------------|
| `dev` | 1 | 1 | 2Gi | 0 | Lightweight development cluster |
| `gpu-single` | 1 | 4 | 8Gi | 1 | Single-GPU training node |
| `data-processing` | 4 | 2 | 4Gi | 0 | Multi-node data processing |

### create_cluster integration

```python
def create_cluster(
    self,
    name: str,
    ...,
    preset: str | Preset | None = None,
    ...,
) -> ClusterHandle | DryRunResult:
    """
    If preset is a string, look up the built-in preset.
    If preset is a Preset object, use directly.
    Explicit parameters override preset defaults.
    """
```

### Override behavior

```python
# Preset provides workers=1, explicit overrides to 8
cluster = client.create_cluster("test", preset="dev", workers=8)
# Result: 8 workers with dev preset's other defaults
```

## Test Contract

```python
def test_list_presets():
    presets = list_presets()
    assert len(presets) >= 3
    names = [p.name for p in presets]
    assert "dev" in names
    assert "gpu-single" in names

def test_preset_by_name():
    result = client.create_cluster("test", preset="dev", dry_run=True)
    d = result.to_dict()
    # dev preset defaults applied
    assert d["spec"]["workerGroupSpecs"][0]["replicas"] == 1

def test_explicit_overrides_preset():
    result = client.create_cluster("test", preset="dev", workers=8, dry_run=True)
    d = result.to_dict()
    assert d["spec"]["workerGroupSpecs"][0]["replicas"] == 8

def test_unknown_preset_raises():
    with pytest.raises(ValueError, match="Unknown preset"):
        client.create_cluster("test", preset="nonexistent")
```
