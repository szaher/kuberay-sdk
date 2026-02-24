"""Dry-run mode — preview Kubernetes manifests without applying them.

Task: T065

The ``dry_run=True`` flag on ``create_cluster``, ``create_job``, and
``create_service`` lets you preview the full CRD manifest that *would* be
sent to the Kubernetes API server — without actually creating anything.

This is useful for:
- Validating configuration before deployment
- Generating manifests for GitOps / CI pipelines
- Debugging unexpected resource shapes
- Reviewing YAML before committing to a cluster change

No live Kubernetes cluster is needed for the dry-run itself; however,
``KubeRayClient()`` does require a valid kubeconfig to initialise.
"""

from kuberay_sdk import KubeRayClient


def main() -> None:
    # Initialise the client.
    # NOTE: Requires kubeconfig to be configured
    client = KubeRayClient()

    # ------------------------------------------------------------------
    # 1. Dry-run a basic cluster creation.
    # ------------------------------------------------------------------
    print("=== Dry-run: basic cluster ===\n")

    # dry_run=True returns a DryRunResult instead of a ClusterHandle.
    # No resources are created on the cluster.
    result = client.create_cluster(
        "test-cluster",
        workers=2,
        dry_run=True,
    )

    # Inspect the result as a Python dict.
    manifest_dict = result.to_dict()
    print(f"Kind:      {manifest_dict['kind']}")
    print(f"Name:      {manifest_dict['metadata']['name']}")
    print(f"Namespace: {manifest_dict['metadata']['namespace']}")

    # Render the full manifest as YAML — handy for piping to kubectl apply.
    print("\nFull YAML manifest:")
    print(result.to_yaml())

    # ------------------------------------------------------------------
    # 2. Dry-run with more options (GPU workers, autoscaling).
    # ------------------------------------------------------------------
    print("=== Dry-run: GPU cluster with autoscaling ===\n")

    gpu_result = client.create_cluster(
        "gpu-cluster",
        workers=4,
        gpus_per_worker=1,
        memory_per_worker="16Gi",
        image="rayproject/ray-ml:2.41.0-py310-gpu",
        enable_autoscaling=True,
        labels={"team": "ml-platform"},
        dry_run=True,
    )

    # The repr gives a quick summary.
    print(f"Result repr: {gpu_result!r}")
    print(f"\n{gpu_result.to_yaml()}")

    # ------------------------------------------------------------------
    # 3. Dry-run a RayJob.
    # ------------------------------------------------------------------
    print("=== Dry-run: standalone RayJob ===\n")

    job_result = client.create_job(
        "eval-job",
        entrypoint="python eval.py --split test",
        workers=2,
        dry_run=True,
    )

    print(f"Job manifest kind: {job_result.to_dict()['kind']}")
    print(f"\n{job_result.to_yaml()}")

    print("All dry-run previews generated successfully — no resources were created.")


if __name__ == "__main__":
    main()
