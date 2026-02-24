"""Convenience imports — import common types from the top-level package.

Task: T063

The kuberay-sdk re-exports frequently used types from the top-level
``kuberay_sdk`` package so you do not have to remember deep module paths.

Before (deep imports):
    from kuberay_sdk.models.cluster import WorkerGroup
    from kuberay_sdk.models.runtime_env import RuntimeEnv
    from kuberay_sdk.models.storage import StorageVolume

After (convenience imports):
    from kuberay_sdk import WorkerGroup, RuntimeEnv, StorageVolume

This script is fully standalone — it only imports types and prints their
names to verify they resolve correctly.  No live cluster is needed.
"""

# All of these are re-exported from the top-level kuberay_sdk package.
# You no longer need to import from internal sub-modules.
from kuberay_sdk import (
    AsyncKubeRayClient,
    ClusterConfig,
    ExperimentTracking,
    HeadNodeConfig,
    JobConfig,
    KubeRayClient,
    RuntimeEnv,
    SDKConfig,
    ServiceConfig,
    StorageVolume,
    WorkerGroup,
)


def main() -> None:
    # Collect every re-exported type so we can verify them in one place.
    exported_types = [
        AsyncKubeRayClient,
        ClusterConfig,
        ExperimentTracking,
        HeadNodeConfig,
        JobConfig,
        KubeRayClient,
        RuntimeEnv,
        SDKConfig,
        ServiceConfig,
        StorageVolume,
        WorkerGroup,
    ]

    print("Convenience imports — all top-level re-exports resolve correctly:\n")
    for cls in exported_types:
        # Each type has a __module__ and __qualname__ that tell us where it
        # actually lives, proving the re-export works.
        print(f"  {cls.__qualname__:30s}  (from {cls.__module__})")

    # Quick sanity check: instantiate a few lightweight model types.
    # These do not require a Kubernetes connection.
    worker = WorkerGroup(name="demo", replicas=2, cpus=4, memory="8Gi")
    print(f"\nSample WorkerGroup: {worker}")

    runtime = RuntimeEnv(pip=["torch>=2.0", "numpy"], env_vars={"DEBUG": "1"})
    print(f"Sample RuntimeEnv:  {runtime}")

    volume = StorageVolume(name="data", mount_path="/mnt/data", size="50Gi")
    print(f"Sample StorageVolume: {volume}")

    config = SDKConfig(namespace="ml-team")
    print(f"Sample SDKConfig:   {config}")

    print("\nAll convenience imports verified successfully.")


if __name__ == "__main__":
    main()
