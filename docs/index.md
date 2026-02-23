# kuberay-sdk

A user-friendly Python SDK for managing Ray clusters, jobs, and services on Kubernetes and OpenShift via [KubeRay](https://ray-project.github.io/kuberay/).

## What is kuberay-sdk?

kuberay-sdk wraps the KubeRay CRD API and the Ray Dashboard REST API into a high-level Python interface. Instead of writing YAML manifests and calling `kubectl`, you get a typed, validated, handle-based workflow designed for AI engineers, data scientists, and ML practitioners.

## Key Features

- **Handle-based API** — `create_cluster()` returns a `ClusterHandle` you can `.scale()`, `.delete()`, or `.submit_job()` on
- **Two job modes** — standalone RayJob (CRD) or Dashboard submission to a running cluster
- **Ray Serve** — deploy, update, and inspect RayService resources
- **Pydantic models** — validated configs for clusters, jobs, services, storage, and runtime environments
- **OpenShift & Kueue** — hardware profiles, Route creation, queue integration
- **Async support** — `AsyncKubeRayClient` mirrors every sync method
- **No Kubernetes expertise required** — the SDK abstracts away CRDs, Pods, and Services

## Quick Example

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()
cluster = client.create_cluster("my-cluster", workers=2, cpus_per_worker=2)
cluster.wait_until_ready()
print(cluster.status())
```

## Documentation Sections

<div class="grid cards" markdown>

-   :material-book-open-variant:{ .lg .middle } **User Guide**

    ---

    Installation, quick start, and task-oriented guides for cluster management, job submission, Ray Serve, and more.

    [:octicons-arrow-right-24: Getting Started](user-guide/getting-started/installation.md)

-   :material-code-tags:{ .lg .middle } **API Reference**

    ---

    Auto-generated reference for all public classes, methods, and models with type annotations and examples.

    [:octicons-arrow-right-24: Browse API](reference/)

-   :material-wrench:{ .lg .middle } **Developer Guide**

    ---

    Architecture overview, development setup, testing conventions, and contribution guidelines.

    [:octicons-arrow-right-24: Start Contributing](developer-guide/architecture.md)

-   :material-notebook:{ .lg .middle } **Examples**

    ---

    Runnable Python scripts and Jupyter notebooks covering common workflows.

    [:octicons-arrow-right-24: View Examples](examples/index.md)

</div>
