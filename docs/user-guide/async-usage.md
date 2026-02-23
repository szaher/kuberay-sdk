# Async Usage

kuberay-sdk provides [`AsyncKubeRayClient`][kuberay_sdk.async_client.AsyncKubeRayClient], which mirrors every method of `KubeRayClient` with `async`/`await` syntax. This enables concurrent operations and integration with async frameworks.

## Basic async usage

```python
import asyncio
from kuberay_sdk import AsyncKubeRayClient

async def main():
    client = AsyncKubeRayClient()

    cluster = await client.create_cluster("my-cluster", workers=2)
    await cluster.wait_until_ready()

    status = await cluster.status()
    print(f"{status.name}: {status.state}")

    await cluster.delete()

asyncio.run(main())
```

## Concurrent cluster creation

Create multiple clusters simultaneously:

```python
import asyncio
from kuberay_sdk import AsyncKubeRayClient

async def main():
    client = AsyncKubeRayClient()

    # Create 3 clusters concurrently
    clusters = await asyncio.gather(
        client.create_cluster("cluster-a", workers=2),
        client.create_cluster("cluster-b", workers=4),
        client.create_cluster("cluster-c", workers=2, gpus_per_worker=1),
    )

    # Wait for all to be ready
    await asyncio.gather(*(c.wait_until_ready() for c in clusters))

    # Check statuses
    for cluster in clusters:
        status = await cluster.status()
        print(f"{status.name}: {status.state}")

asyncio.run(main())
```

## Async job submission

```python
async def submit_jobs():
    client = AsyncKubeRayClient()

    job = await client.create_job(
        "async-training",
        entrypoint="python train.py",
        workers=4,
        gpus_per_worker=1,
    )

    result = await job.wait(timeout=3600)
    logs = await job.logs()
    print(logs)

asyncio.run(submit_jobs())
```

## Async Ray Serve

```python
async def deploy_service():
    client = AsyncKubeRayClient()

    service = await client.create_service(
        "async-service",
        import_path="serve_app:deployment",
        num_replicas=2,
    )

    status = await service.status()
    print(f"Endpoint: {status.endpoint_url}")

    await service.update(num_replicas=4)
    await service.delete()

asyncio.run(deploy_service())
```

## Async Dashboard job submission

```python
async def dashboard_submit():
    client = AsyncKubeRayClient()

    cluster = await client.get_cluster("my-cluster")
    job = await cluster.submit_job(
        entrypoint="python eval.py",
        runtime_env={"pip": ["scikit-learn"]},
    )

    result = await job.wait()
    print(await job.logs())

asyncio.run(dashboard_submit())
```

## Configuration

`AsyncKubeRayClient` accepts the same `SDKConfig` as the sync client:

```python
from kuberay_sdk import AsyncKubeRayClient, SDKConfig

client = AsyncKubeRayClient(config=SDKConfig(
    namespace="ml-team",
    retry_max_attempts=5,
))
```

## Async handle methods

All handle methods are available as async variants:

| Sync (`ClusterHandle`) | Async (`AsyncClusterHandle`) |
|---|---|
| `cluster.status()` | `await cluster.status()` |
| `cluster.scale(workers=8)` | `await cluster.scale(workers=8)` |
| `cluster.delete()` | `await cluster.delete()` |
| `cluster.wait_until_ready()` | `await cluster.wait_until_ready()` |
| `cluster.dashboard_url()` | `await cluster.dashboard_url()` |
| `cluster.metrics()` | `await cluster.metrics()` |
| `cluster.submit_job(...)` | `await cluster.submit_job(...)` |
| `cluster.list_jobs()` | `await cluster.list_jobs()` |
