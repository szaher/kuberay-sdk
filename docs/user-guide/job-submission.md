# Job Submission

kuberay-sdk supports two modes for running Ray jobs: **standalone RayJob** (via KubeRay CRD) and **Dashboard submission** (to a running cluster via the Ray Dashboard API).

## Standalone RayJob (CRD mode)

A standalone RayJob provisions its own disposable cluster, runs your entrypoint script, and tears down automatically when done:

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()

job = client.create_job(
    "training-run",
    entrypoint="python train.py --epochs 10",
    workers=4,
    gpus_per_worker=1,
    memory_per_worker="8Gi",
)

# Wait for completion
result = job.wait(timeout=3600)
print(f"Job finished with status: {result}")
```

### Keep the cluster alive after the job

By default, the cluster shuts down when the job completes. To keep it running:

```python
job = client.create_job(
    "interactive-job",
    entrypoint="python setup.py",
    workers=2,
    shutdown_after_finish=False,
)
```

## Dashboard submission (to a running cluster)

Submit a job to an existing, already-running cluster via the Ray Dashboard API:

```python
cluster = client.get_cluster("my-cluster")
cluster.wait_until_ready()

job = cluster.submit_job(
    entrypoint="python eval.py",
    runtime_env={"pip": ["scikit-learn"]},
)
```

This mode is useful for iterative development — the cluster stays up between job submissions.

## Job logs

```python
# Get full logs after completion
print(job.logs())

# Stream logs in real-time
for line in job.logs(stream=True, follow=True):
    print(line)

# Get last N lines
print(job.logs(tail=50))
```

## Job lifecycle

```python
# Check status
status = job.status()
print(f"State: {status.state}")

# Get progress information
progress = job.progress()
print(progress)

# Stop a running job
job.stop()
```

## Download artifacts

```python
job.download_artifacts("./output")
```

## List jobs

```python
# List all RayJob CRs in the namespace
jobs = client.list_jobs()

# List jobs submitted to a specific cluster via Dashboard
cluster_jobs = cluster.list_jobs()
```

## Runtime environment

Specify Python packages, environment variables, and working directory for your job:

```python
from kuberay_sdk.models.runtime_env import RuntimeEnv

job = client.create_job(
    "ml-job",
    entrypoint="python train.py",
    workers=4,
    runtime_env=RuntimeEnv(
        pip=["torch>=2.0", "transformers", "datasets"],
        env_vars={"WANDB_PROJECT": "my-project"},
        working_dir="/app",
    ),
)
```

See [Storage & Runtime Environment](storage-runtime-env.md) for more details.

## Experiment tracking

Integrate with MLflow for automatic experiment tracking:

```python
from kuberay_sdk.models.runtime_env import ExperimentTracking

job = client.create_job(
    "tracked-job",
    entrypoint="python train.py",
    experiment_tracking=ExperimentTracking(
        provider="mlflow",
        tracking_uri="http://mlflow.ml-infra:5000",
        experiment_name="bert-finetune",
    ),
)
```

See [Experiment Tracking](experiment-tracking.md) for more details.
