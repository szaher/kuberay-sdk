# Storage & Runtime Environment

This guide covers attaching persistent storage to clusters and jobs, and configuring the Ray runtime environment for package installation, environment variables, and working directories.

## Storage volumes

### Create a new PVC

Attach a new persistent volume claim that the SDK creates automatically:

```python
from kuberay_sdk import KubeRayClient
from kuberay_sdk.models.storage import StorageVolume

client = KubeRayClient()

cluster = client.create_cluster(
    "cluster-with-storage",
    workers=2,
    storage=[
        StorageVolume(name="training-data", mount_path="/mnt/data", size="100Gi"),
        StorageVolume(name="checkpoints", mount_path="/mnt/checkpoints", size="50Gi"),
    ],
)
```

### Use an existing PVC

Reference a pre-existing PersistentVolumeClaim by name:

```python
cluster = client.create_cluster(
    "cluster-shared-storage",
    workers=2,
    storage=[
        StorageVolume(
            name="shared-models",
            mount_path="/models",
            existing_claim="shared-models-pvc",
        ),
    ],
)
```

### StorageVolume options

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Volume name (used as PVC name for new volumes) |
| `mount_path` | `str` | Absolute path where the volume is mounted in containers |
| `size` | `str` | PVC size (e.g., `"100Gi"`). Set for new volumes. |
| `existing_claim` | `str` | Name of an existing PVC. Mutually exclusive with `size`. |
| `access_mode` | `str` | PVC access mode: `ReadWriteOnce`, `ReadOnlyMany`, `ReadWriteMany`. Default: `ReadWriteOnce` |
| `storage_class` | `str` | Kubernetes StorageClass name. Optional. |

!!! note
    Exactly one of `size` (new PVC) or `existing_claim` (existing PVC) must be set.

## Runtime environment

The [`RuntimeEnv`][kuberay_sdk.models.runtime_env.RuntimeEnv] model configures the Ray runtime environment for dependency installation and configuration.

### Pip packages

```python
from kuberay_sdk.models.runtime_env import RuntimeEnv

job = client.create_job(
    "ml-job",
    entrypoint="python train.py",
    runtime_env=RuntimeEnv(
        pip=["torch>=2.0", "transformers", "datasets"],
    ),
)
```

### Conda environment

```python
job = client.create_job(
    "conda-job",
    entrypoint="python train.py",
    runtime_env=RuntimeEnv(
        conda="environment.yml",
    ),
)
```

!!! warning
    `pip` and `conda` are mutually exclusive (Ray constraint). You cannot use both in the same runtime environment.

### Environment variables

```python
job = client.create_job(
    "env-job",
    entrypoint="python train.py",
    runtime_env=RuntimeEnv(
        pip=["torch"],
        env_vars={
            "WANDB_PROJECT": "my-project",
            "WANDB_API_KEY": "secret-key",
            "HF_TOKEN": "hf_abc123",
        },
    ),
)
```

### Working directory

```python
job = client.create_job(
    "workdir-job",
    entrypoint="python train.py",
    runtime_env=RuntimeEnv(
        working_dir="/app",
        pip=["torch"],
    ),
)
```

### Combining storage with runtime environment

```python
cluster = client.create_cluster(
    "full-setup",
    workers=4,
    gpus_per_worker=1,
    storage=[
        StorageVolume(name="data", mount_path="/mnt/data", existing_claim="training-data"),
    ],
    runtime_env=RuntimeEnv(
        pip=["torch>=2.0", "transformers"],
        env_vars={"DATA_DIR": "/mnt/data"},
        working_dir="/app",
    ),
)
```
