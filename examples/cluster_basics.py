"""Cluster basics — create, monitor, scale, and delete a RayCluster.

This example shows the simplest kuberay-sdk workflow:
1. Create a cluster with basic resource requirements
2. Wait for it to become ready
3. Inspect its status and metrics
4. Scale the worker count up
5. Clean up by deleting the cluster
"""

from kuberay_sdk import KubeRayClient
from kuberay_sdk.errors import ClusterNotFoundError, TimeoutError


def main() -> None:
    # Create a client with default settings (uses kubeconfig context namespace).
    client = KubeRayClient()

    # Create a 2-worker cluster. Each worker gets 1 CPU and 2 GiB RAM (defaults).
    print("Creating cluster...")
    cluster = client.create_cluster("example-cluster", workers=2)

    # Block until the cluster reaches RUNNING state (up to 5 minutes).
    try:
        cluster.wait_until_ready(timeout=300)
    except TimeoutError:
        print("Cluster did not become ready in time, cleaning up.")
        cluster.delete()
        return

    # Inspect current status.
    status = cluster.status()
    print(f"Cluster: {status.name}")
    print(f"  State:   {status.state}")
    print(f"  Workers: {status.workers_ready}/{status.workers_desired}")
    print(f"  Ray:     {status.ray_version}")
    print(f"  Age:     {status.age}")

    # Fetch live metrics from the Ray Dashboard.
    metrics = cluster.metrics()
    print(f"  CPU utilization: {metrics.get('cpu_utilization', 'N/A')}")

    # Scale the cluster from 2 to 4 workers.
    print("\nScaling to 4 workers...")
    cluster.scale(workers=4)
    cluster.wait_until_ready()
    status = cluster.status()
    print(f"  Workers after scale: {status.workers_ready}/{status.workers_desired}")

    # List all clusters in the namespace.
    print("\nAll clusters:")
    for cs in client.list_clusters():
        print(f"  {cs.name} — {cs.state} ({cs.workers_ready} workers)")

    # Retrieve an existing cluster by name.
    try:
        same_cluster = client.get_cluster("example-cluster")
        print(f"\nRe-fetched cluster: {same_cluster.name}")
    except ClusterNotFoundError:
        print("\nCluster disappeared unexpectedly.")

    # Clean up.
    print("\nDeleting cluster...")
    cluster.delete()
    print("Done.")


if __name__ == "__main__":
    main()
