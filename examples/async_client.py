"""Async client — concurrent cluster operations with AsyncKubeRayClient.

This example demonstrates:
1. Using AsyncKubeRayClient for non-blocking operations
2. Creating multiple clusters concurrently with asyncio.gather
3. Submitting jobs to clusters in parallel
4. Async cleanup
"""

import asyncio

from kuberay_sdk import AsyncKubeRayClient, SDKConfig


async def create_and_use_cluster(
    client: AsyncKubeRayClient,
    name: str,
    workers: int,
) -> str:
    """Create a cluster, run a job, and return the result."""
    # Create the cluster.
    cluster = await client.create_cluster(name, workers=workers)
    print(f"[{name}] Created, waiting for ready...")

    # Wait for the cluster to be ready.
    await cluster.wait_until_ready()
    status = await cluster.status()
    print(f"[{name}] Ready — {status.workers_ready} workers")

    # Submit a job via the Dashboard API.
    job = await cluster.submit_job(
        entrypoint=f"python -c \"print('Hello from {name}')\"",
    )
    result = await job.wait()
    logs = await job.logs()
    print(f"[{name}] Job done: {logs.strip()}")

    # Clean up.
    await cluster.delete()
    print(f"[{name}] Deleted")

    return f"{name}: {result}"


async def main() -> None:
    # Create an async client.
    client = AsyncKubeRayClient(config=SDKConfig(namespace="async-demo"))

    # Launch three clusters concurrently.
    # asyncio.gather runs all coroutines at the same time.
    print("Creating 3 clusters concurrently...\n")
    results = await asyncio.gather(
        create_and_use_cluster(client, "cluster-a", workers=1),
        create_and_use_cluster(client, "cluster-b", workers=2),
        create_and_use_cluster(client, "cluster-c", workers=3),
    )

    print("\n--- Results ---")
    for r in results:
        print(f"  {r}")

    # List any remaining clusters (should be empty after cleanup).
    remaining = await client.list_clusters()
    print(f"\nRemaining clusters: {len(remaining)}")


if __name__ == "__main__":
    asyncio.run(main())
