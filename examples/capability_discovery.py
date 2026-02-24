"""Capability discovery — adapt cluster configuration to the environment.

This example demonstrates ``client.get_capabilities()``, which probes the
connected Kubernetes cluster and returns a ``ClusterCapabilities`` object
describing what features are available.

This is useful for writing portable scripts that behave correctly across
different environments (e.g., GPU vs. CPU-only nodes, Kueue-enabled
clusters, OpenShift vs. vanilla Kubernetes).

ClusterCapabilities fields:
    - kuberay_installed (bool): Whether the KubeRay operator CRDs are present
    - kuberay_version (str): Installed KubeRay operator version
    - gpu_available (bool): Whether GPU resources are detected on any node
    - gpu_types (list[str]): GPU resource names (e.g., ["nvidia.com/gpu"])
    - kueue_available (bool): Whether the Kueue admission controller is installed
    - openshift (bool): Whether the cluster is OpenShift
"""

from __future__ import annotations

from kuberay_sdk import KubeRayClient
from kuberay_sdk.models.capabilities import ClusterCapabilities


def print_capabilities(caps: ClusterCapabilities) -> None:
    """Display discovered capabilities in a readable format."""
    print("Cluster Capabilities")
    print("=" * 40)
    print(f"  KubeRay installed : {caps.kuberay_installed}")
    print(f"  KubeRay version   : {caps.kuberay_version}")
    print(f"  GPU available     : {caps.gpu_available}")
    print(f"  GPU types         : {caps.gpu_types}")
    print(f"  Kueue available   : {caps.kueue_available}")
    print(f"  OpenShift         : {caps.openshift}")
    print()


def main() -> None:
    # Create a client using default kubeconfig context and namespace.
    client = KubeRayClient()

    # NOTE: Requires a running KubeRay cluster
    # Probe the cluster to discover available capabilities.
    caps = client.get_capabilities()
    print_capabilities(caps)

    # ------------------------------------------------------------------
    # Guard: ensure KubeRay is installed before proceeding
    # ------------------------------------------------------------------
    if not caps.kuberay_installed:
        print("KubeRay operator is not installed. Cannot create clusters.")
        print("Install it with: helm install kuberay-operator kuberay/kuberay-operator")
        return

    # ------------------------------------------------------------------
    # Adaptive GPU / CPU configuration
    # ------------------------------------------------------------------
    # Choose cluster settings based on whether GPUs are available.
    if caps.gpu_available:
        print(f"GPUs detected: {caps.gpu_types}")
        print("Configuring cluster with GPU workers.\n")

        # Use GPU-optimized settings.
        worker_count = 2
        gpus_per_worker = 1
        image = "rayproject/ray-ml:2.41.0-py310-gpu"
        entrypoint = "python train_gpu.py --epochs 20"
    else:
        print("No GPUs detected. Falling back to CPU-only configuration.\n")

        # Use CPU-only settings with more workers to compensate.
        worker_count = 4
        gpus_per_worker = 0
        image = "rayproject/ray-ml:2.41.0-py310"
        entrypoint = "python train_cpu.py --epochs 5"

    # ------------------------------------------------------------------
    # Kueue queue integration
    # ------------------------------------------------------------------
    # If Kueue is available, assign the cluster to a local queue for
    # fair-share scheduling and resource quota enforcement.
    labels: dict[str, str] = {}
    if caps.kueue_available:
        print("Kueue detected. Assigning cluster to local queue 'ml-team-queue'.\n")
        # The Kueue admission controller uses this label to manage the workload.
        labels["kueue.x-k8s.io/queue-name"] = "ml-team-queue"
    else:
        print("Kueue not available. Cluster will be scheduled without queue management.\n")

    # ------------------------------------------------------------------
    # OpenShift-specific adjustments
    # ------------------------------------------------------------------
    if caps.openshift:
        print("OpenShift detected. Applying security context constraints.\n")
        # On OpenShift, pods may need specific SCC annotations.
        # The SDK handles most of this automatically, but you can add
        # extra labels or annotations if needed.
        labels["app.openshift.io/runtime"] = "ray"

    # NOTE: Requires a running KubeRay cluster
    # Create the cluster with environment-adapted configuration.
    print("Creating cluster with adaptive configuration...")
    cluster = client.create_cluster(
        "capability-demo",
        workers=worker_count,
        gpus_per_worker=gpus_per_worker,
        image=image,
        labels=labels,
    )

    # NOTE: Requires a running KubeRay cluster
    cluster.wait_until_ready(timeout=300)
    print(f"Cluster ready with {worker_count} workers.")

    # NOTE: Requires a running KubeRay cluster
    # Submit a job using the chosen entrypoint.
    job = cluster.submit_job(entrypoint=entrypoint)
    result = job.wait(timeout=1800)
    print(f"Job completed: {result}")

    # NOTE: Requires a running KubeRay cluster
    # Clean up.
    cluster.delete()
    print("Done.")


if __name__ == "__main__":
    main()
