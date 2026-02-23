"""Advanced configuration — heterogeneous workers, storage, runtime env, and scheduling.

This example demonstrates:
1. Heterogeneous worker groups (CPU + GPU pools)
2. Persistent storage volumes (new PVC and existing claim)
3. Runtime environment with pip packages and env vars
4. Kubernetes scheduling constraints (tolerations, node selectors, labels)
5. Custom head node configuration
6. Raw overrides for arbitrary CRD fields
"""

from kuberay_sdk import KubeRayClient
from kuberay_sdk.models.cluster import HeadNodeConfig, WorkerGroup
from kuberay_sdk.models.runtime_env import RuntimeEnv
from kuberay_sdk.models.storage import StorageVolume


def main() -> None:
    client = KubeRayClient()

    # --- Heterogeneous worker groups ---
    # Define two pools: a CPU pool for data preprocessing and a GPU pool for training.
    cpu_workers = WorkerGroup(
        name="cpu-pool",
        replicas=4,
        cpus=4,
        memory="8Gi",
        # Autoscaling bounds (requires enable_autoscaling=True on the cluster).
        min_replicas=2,
        max_replicas=8,
    )

    gpu_workers = WorkerGroup(
        name="gpu-pool",
        replicas=2,
        cpus=2,
        gpus=1,
        memory="16Gi",
        gpu_type="nvidia.com/gpu",
        # Custom Ray start parameters for GPU workers.
        ray_start_params={"num-gpus": "1"},
    )

    # --- Storage ---
    # Create a new 100 GiB PVC for training data.
    data_volume = StorageVolume(
        name="training-data",
        mount_path="/mnt/data",
        size="100Gi",
        storage_class="gp3",
        access_mode="ReadWriteOnce",
    )

    # Attach an existing shared PVC for model checkpoints.
    checkpoint_volume = StorageVolume(
        name="checkpoints",
        mount_path="/mnt/checkpoints",
        existing_claim="shared-checkpoints-pvc",
    )

    # --- Runtime environment ---
    runtime = RuntimeEnv(
        pip=["torch>=2.0", "lightning", "wandb"],
        env_vars={
            "WANDB_PROJECT": "distributed-training",
            "NCCL_DEBUG": "INFO",
        },
        working_dir="/app",
    )

    # --- Custom head node ---
    head = HeadNodeConfig(
        cpus=2,
        memory="4Gi",
        ray_start_params={"dashboard-host": "0.0.0.0"},
    )

    # --- Create the cluster ---
    print("Creating advanced cluster...")
    cluster = client.create_cluster(
        "advanced-cluster",
        worker_groups=[cpu_workers, gpu_workers],
        head=head,
        storage=[data_volume, checkpoint_volume],
        runtime_env=runtime,
        image="rayproject/ray-ml:2.41.0-py310-gpu",
        enable_autoscaling=True,
        # Kubernetes scheduling.
        labels={"team": "ml-platform", "project": "distributed-training"},
        annotations={"prometheus.io/scrape": "true"},
        tolerations=[
            {
                "key": "nvidia.com/gpu",
                "operator": "Exists",
                "effect": "NoSchedule",
            }
        ],
        node_selector={"node-type": "compute"},
        # Raw overrides for fields not covered by the SDK.
        raw_overrides={
            "spec": {
                "headGroupSpec": {
                    "template": {
                        "spec": {
                            "terminationGracePeriodSeconds": 60,
                        }
                    }
                }
            }
        },
    )

    cluster.wait_until_ready()
    status = cluster.status()
    print(f"Cluster ready: {status.workers_ready} workers across {len([cpu_workers, gpu_workers])} groups")

    # Submit a training job to the running cluster.
    job = cluster.submit_job(
        entrypoint="python -m lightning_train --gpus 2 --nodes 1",
        runtime_env={"pip": ["lightning"]},
    )
    result = job.wait()
    print(f"Job result: {result}")

    # Clean up.
    cluster.delete()
    print("Done.")


if __name__ == "__main__":
    main()
