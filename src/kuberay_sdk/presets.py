"""Preset configurations for common cluster patterns."""

from __future__ import annotations

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


_BUILTIN_PRESETS: dict[str, Preset] = {
    "dev": Preset(
        name="dev",
        description="Lightweight development cluster",
        workers=1,
        head_cpu="1",
        head_memory="2Gi",
        worker_cpu="1",
        worker_memory="2Gi",
        worker_gpu=0,
    ),
    "gpu-single": Preset(
        name="gpu-single",
        description="Single-GPU training node",
        workers=1,
        head_cpu="2",
        head_memory="4Gi",
        worker_cpu="4",
        worker_memory="8Gi",
        worker_gpu=1,
    ),
    "data-processing": Preset(
        name="data-processing",
        description="Multi-node data processing",
        workers=4,
        head_cpu="2",
        head_memory="4Gi",
        worker_cpu="2",
        worker_memory="4Gi",
        worker_gpu=0,
    ),
}


def get_preset(name: str) -> Preset:
    """Look up a built-in preset by name.

    Raises ValueError if not found.
    """
    if name not in _BUILTIN_PRESETS:
        available = ", ".join(sorted(_BUILTIN_PRESETS.keys()))
        raise ValueError(f"Unknown preset '{name}'. Available presets: {available}")
    return _BUILTIN_PRESETS[name]


def list_presets() -> list[Preset]:
    """Return all built-in presets."""
    return list(_BUILTIN_PRESETS.values())
