"""Job submission — standalone RayJob and Dashboard API submission.

This example demonstrates two ways to run jobs:

1. **Standalone RayJob (CRD mode)** — creates a disposable cluster, runs the
   job, and tears down the cluster automatically.
2. **Dashboard submission** — submits a job to an already-running cluster via
   the Ray Dashboard REST API.
"""

from kuberay_sdk import KubeRayClient
from kuberay_sdk.models.runtime_env import ExperimentTracking, RuntimeEnv


def standalone_job(client: KubeRayClient) -> None:
    """Create a standalone RayJob that provisions its own cluster."""
    print("=== Standalone RayJob ===\n")

    # The job creates a 2-GPU cluster, runs the entrypoint, then shuts down.
    job = client.create_job(
        "training-job",
        entrypoint="python train.py --epochs 10 --lr 0.001",
        workers=2,
        gpus_per_worker=1,
        memory_per_worker="8Gi",
        runtime_env=RuntimeEnv(
            pip=["torch>=2.0", "transformers"],
            env_vars={"CUDA_VISIBLE_DEVICES": "0"},
        ),
        # Cluster is deleted after the job finishes (default behavior).
        shutdown_after_finish=True,
    )

    print(f"Job created: {job.name} in {job.namespace}")

    # Block until the job completes (up to 1 hour).
    result = job.wait(timeout=3600)
    print(f"Job finished: {result}")

    # Fetch the full log output.
    logs = job.logs()
    print(f"Logs (last 500 chars):\n{logs[-500:]}")


def dashboard_job(client: KubeRayClient) -> None:
    """Submit a job to a running cluster via the Dashboard API."""
    print("\n=== Dashboard Job Submission ===\n")

    # Get a handle to an existing cluster.
    cluster = client.get_cluster("my-cluster")
    cluster.wait_until_ready()

    # Submit a lightweight evaluation script via the Dashboard.
    job = cluster.submit_job(
        entrypoint="python eval.py --split test",
        runtime_env=RuntimeEnv(pip=["scikit-learn", "pandas"]),
        experiment_tracking=ExperimentTracking(
            provider="mlflow",
            tracking_uri="http://mlflow:5000",
            experiment_name="eval-run",
        ),
        metadata={"user": "alice", "run_type": "evaluation"},
    )

    print(f"Dashboard job submitted: {job.name}")

    # Stream logs as they arrive.
    print("\nStreaming logs:")
    for line in job.logs(stream=True, follow=True):
        print(f"  {line}", end="")

    # Check final status.
    status = job.status()
    print(f"\nFinal status: {status}")

    # List all jobs submitted to this cluster.
    print("\nAll cluster jobs:")
    for j in cluster.list_jobs():
        print(f"  {j}")


def main() -> None:
    client = KubeRayClient()

    standalone_job(client)
    dashboard_job(client)


if __name__ == "__main__":
    main()
