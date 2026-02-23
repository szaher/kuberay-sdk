# Experiment Tracking

kuberay-sdk integrates with MLflow for experiment tracking. The [`ExperimentTracking`][kuberay_sdk.models.runtime_env.ExperimentTracking] model injects tracking environment variables into your job's runtime environment automatically.

## Basic MLflow integration

```python
from kuberay_sdk import KubeRayClient
from kuberay_sdk.models.runtime_env import ExperimentTracking

client = KubeRayClient()

job = client.create_job(
    "tracked-training",
    entrypoint="python train.py",
    workers=4,
    gpus_per_worker=1,
    experiment_tracking=ExperimentTracking(
        provider="mlflow",
        tracking_uri="http://mlflow.ml-infra:5000",
        experiment_name="bert-finetune",
    ),
)
```

This automatically sets the following environment variables in the job's runtime environment:

| Variable | Value |
|---|---|
| `MLFLOW_TRACKING_URI` | `http://mlflow.ml-infra:5000` |
| `MLFLOW_EXPERIMENT_NAME` | `bert-finetune` |

## Custom environment variables

Pass additional environment variables alongside the tracking configuration:

```python
job = client.create_job(
    "custom-tracking",
    entrypoint="python train.py",
    experiment_tracking=ExperimentTracking(
        provider="mlflow",
        tracking_uri="http://mlflow:5000",
        experiment_name="my-experiment",
        env_vars={
            "MLFLOW_TRACKING_TOKEN": "my-token",
            "MLFLOW_REGISTRY_URI": "http://registry:5000",
        },
    ),
)
```

## Combining with runtime environment

Experiment tracking can be used alongside `RuntimeEnv` for pip packages and other settings:

```python
from kuberay_sdk.models.runtime_env import ExperimentTracking, RuntimeEnv

job = client.create_job(
    "full-tracking",
    entrypoint="python train.py",
    workers=4,
    runtime_env=RuntimeEnv(
        pip=["torch>=2.0", "transformers", "mlflow"],
        working_dir="/app",
    ),
    experiment_tracking=ExperimentTracking(
        provider="mlflow",
        tracking_uri="http://mlflow:5000",
        experiment_name="llm-finetune",
    ),
)
```

## Dashboard submission with tracking

Experiment tracking also works when submitting jobs to a running cluster via the Dashboard API:

```python
cluster = client.get_cluster("my-cluster")

job = cluster.submit_job(
    entrypoint="python eval.py",
    experiment_tracking=ExperimentTracking(
        provider="mlflow",
        tracking_uri="http://mlflow:5000",
    ),
)
```

!!! note
    Currently, only the `mlflow` provider is supported. Using any other provider value raises a `ValidationError`.
