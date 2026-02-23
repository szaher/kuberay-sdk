# Quick Start

This guide walks you through the three most common kuberay-sdk operations: creating a Ray cluster, submitting a job, and deploying a Ray Serve application.

## Create a Ray cluster

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()

# Create a cluster with 2 workers, each with 2 CPUs and 4 GiB RAM
cluster = client.create_cluster(
    "my-cluster",
    workers=2,
    cpus_per_worker=2,
    memory_per_worker="4Gi",
)

# Wait for the cluster to be ready
cluster.wait_until_ready()

# Check the status
status = cluster.status()
print(f"Cluster {status.name}: {status.state}")
print(f"Workers: {status.workers_ready}/{status.workers_desired}")
```

## Submit a training job

A standalone `RayJob` creates its own disposable cluster, runs your script, and tears down automatically:

```python
job = client.create_job(
    "training-run",
    entrypoint="python train.py --epochs 10",
    workers=4,
    gpus_per_worker=1,
    memory_per_worker="8Gi",
)

# Wait for the job to complete
result = job.wait()

# Print the logs
print(job.logs())
```

## Deploy a Ray Serve application

```python
service = client.create_service(
    "my-model",
    import_path="serve_app:deployment",
    num_replicas=2,
)

# Check status and get the endpoint URL
status = service.status()
print(f"Service state: {status.state}")
print(f"Endpoint: {status.endpoint_url}")
```

## Clean up

```python
# Delete resources when done
cluster.delete()
service.delete()
```

## Next steps

- [Cluster Management](../cluster-management.md) — advanced cluster configuration, scaling, monitoring
- [Job Submission](../job-submission.md) — CRD jobs vs. Dashboard submission, log streaming
- [Ray Serve](../ray-serve.md) — service updates, replica management, endpoint access
- [Configuration](../configuration.md) — namespace defaults, retry policies, auth options
