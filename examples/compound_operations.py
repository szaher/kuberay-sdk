"""Compound operations — create a cluster and submit a job in one call.

This example demonstrates ``client.create_cluster_and_submit_job()``, a
convenience method that provisions a RayCluster and immediately submits a
RayJob to it.  The key behavioural contract:

* On **success**, you receive a ``JobHandle`` that references both the job
  and its underlying cluster.
* On **failure** (e.g., the job submission fails after the cluster is
  already running), the SDK intentionally does **not** delete the cluster.
  Instead, the raised exception carries a reference to the cluster handle
  so you can inspect or retry without losing the provisioned resources.
"""

from __future__ import annotations

from kuberay_sdk import KubeRayClient
from kuberay_sdk.errors import KubeRayError


def main() -> None:
    # Create a client using default kubeconfig context and namespace.
    client = KubeRayClient()

    # ------------------------------------------------------------------
    # Happy path: create cluster + submit job in a single call
    # ------------------------------------------------------------------
    # NOTE: Requires a running KubeRay cluster
    try:
        print("Creating cluster and submitting job...")

        # The compound operation provisions a 2-worker cluster and submits
        # the given entrypoint as a RayJob in one atomic-looking call.
        job_handle = client.create_cluster_and_submit_job(
            cluster_name="compound-demo",
            entrypoint="python -c \"import ray; ray.init(); print(ray.cluster_resources())\"",
            workers=2,
        )

        # The returned JobHandle exposes both the job and the cluster.
        print(f"Job submitted: {job_handle.job_name}")
        print(f"Cluster:       {job_handle.cluster_name}")

        # NOTE: Requires a running KubeRay cluster
        # Wait for the job to complete.
        result = job_handle.wait(timeout=600)
        print(f"Job finished with status: {result}")

        # Fetch job logs.
        logs = job_handle.logs()
        print(f"Job output:\n{logs}")

    except KubeRayError as exc:
        # ------------------------------------------------------------------
        # Partial-failure handling
        # ------------------------------------------------------------------
        # If the cluster was created but the job submission failed, the SDK
        # raises a KubeRayError that includes a reference to the cluster.
        # This lets you inspect what went wrong without losing the cluster.
        print(f"\nOperation failed: {exc}")

        # Check whether a cluster was already provisioned before the error.
        cluster_handle = getattr(exc, "cluster_handle", None)
        if cluster_handle is not None:
            print(f"\nCluster '{cluster_handle.name}' is still running.")
            print("You can inspect it, retry the job, or delete it manually:")
            print(f"  kuberay cluster status {cluster_handle.name}")
            print(f"  kuberay cluster delete {cluster_handle.name}")

            # Example: inspect the cluster status before deciding next steps.
            # NOTE: Requires a running KubeRay cluster
            status = cluster_handle.status()
            print(f"\nCluster state: {status.state}")
            print(f"Workers ready: {status.workers_ready}/{status.workers_desired}")

            # Optionally delete the cluster if you do not need it.
            # cluster_handle.delete()
        else:
            # The error occurred before the cluster was created.
            print("No cluster was provisioned — nothing to clean up.")

    # ------------------------------------------------------------------
    # Best practice: always clean up in production code
    # ------------------------------------------------------------------
    # In production, wrap the entire block in try/finally to ensure
    # deterministic cleanup:
    #
    #   job_handle = client.create_cluster_and_submit_job(...)
    #   try:
    #       job_handle.wait()
    #   finally:
    #       job_handle.delete_cluster()
    #


if __name__ == "__main__":
    main()
