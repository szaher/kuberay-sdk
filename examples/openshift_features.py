"""OpenShift features — hardware profiles, Kueue queues, and platform detection.

This example demonstrates OpenShift-specific features:
1. Platform detection (OpenShift, Kueue, hardware profiles)
2. Hardware profile-based cluster creation
3. Kueue queue integration for resource quotas
4. Route creation for external dashboard access
"""

from kuberay_sdk import KubeRayClient, SDKConfig


def main() -> None:
    client = KubeRayClient(config=SDKConfig(
        namespace="ml-workloads",
        # Namespace where HardwareProfile CRs are stored.
        hardware_profile_namespace="redhat-ods-applications",
    ))

    # --- Platform detection ---
    # The SDK can detect platform capabilities at runtime.
    # Note: these functions require the raw K8s API client.
    # In normal usage, the KubeRayClient handles this internally.
    print("Platform detection:")
    print("  (Detection is performed automatically by create_cluster/create_job)")
    print("  Hardware profiles, Kueue, and Routes are used when available.\n")

    # --- Hardware profile ---
    # On OpenShift with Open Data Hub, hardware profiles define GPU types,
    # tolerations, node selectors, and optional queue assignments.
    # The SDK resolves these automatically when you pass `hardware_profile=`.
    print("=== Hardware Profile Cluster ===\n")
    cluster = client.create_cluster(
        "gpu-training-cluster",
        # The hardware profile resolves to specific GPU resources, tolerations,
        # and node selectors defined by the cluster admin.
        hardware_profile="nvidia-gpu-large",
        workers=4,
        memory_per_worker="32Gi",
        image="rayproject/ray-ml:2.41.0-py310-gpu",
    )

    cluster.wait_until_ready()
    status = cluster.status()
    print(f"Cluster: {status.name}")
    print(f"  State:   {status.state}")
    print(f"  Workers: {status.workers_ready}/{status.workers_desired}")

    # The dashboard URL is automatically exposed via an OpenShift Route.
    dashboard = cluster.dashboard_url()
    print(f"  Dashboard: {dashboard}")

    # --- Kueue queue ---
    # Kueue manages resource quotas across teams. Assign a queue to ensure
    # your workload is admitted according to the cluster's quota policy.
    print("\n=== Kueue Queue Job ===\n")
    job = client.create_job(
        "queued-training-job",
        entrypoint="python train.py --epochs 50",
        workers=2,
        gpus_per_worker=1,
        # Assign to a Kueue LocalQueue. The SDK injects the required labels.
        queue="team-ml-queue",
        # shutdown_after_finish must be True when using Kueue with RayJobs.
        shutdown_after_finish=True,
    )

    print(f"Job submitted to queue: {job.name}")
    result = job.wait()
    print(f"Job result: {result}")

    # --- Combined: hardware profile + queue ---
    print("\n=== Hardware Profile + Queue ===\n")
    combined_job = client.create_job(
        "full-featured-job",
        entrypoint="python large_model_train.py",
        hardware_profile="nvidia-gpu-xlarge",
        queue="priority-queue",
        workers=8,
        memory_per_worker="64Gi",
        shutdown_after_finish=True,
    )

    print(f"Job with HW profile + queue: {combined_job.name}")
    combined_job.wait()

    # Clean up.
    cluster.delete()
    print("\nDone.")


if __name__ == "__main__":
    main()
