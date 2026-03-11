# What's New

## v0.3.0

### Rich Display & Notebook Integration

- **Display extras**: Install `kuberay-sdk[rich]`, `kuberay-sdk[notebook]`, or `kuberay-sdk[display]` for enhanced output
- **Auto environment detection**: Automatically selects the best display backend (terminal, notebook, or plain)
- **Styled tables**: Color-coded resource states in terminal (via Rich) and HTML tables in notebooks
- **Auto progress bars**: `wait_until_ready()` and `job.wait()` show progress bars automatically (disable with `progress=False`)
- **Colored log streaming**: Log lines color-coded by level (ERROR, WARNING, INFO)
- **Notebook resource cards**: Handles render as HTML cards with action buttons when evaluated in notebook cells
- **`display()` function**: New unified entry point for rendering resource data
- **`KUBERAY_DISPLAY` env var**: Override auto-detection with `plain`, `rich`, `notebook`, or `auto`
- **CLI rich tables**: `kuberay cluster list` and other CLI commands use styled tables when `[rich]` is installed

## v0.1.0 (Initial Release)

### Highlights

The first release of kuberay-sdk provides a complete Python interface for managing Ray workloads on Kubernetes and OpenShift via KubeRay.

### Features

- **KubeRayClient** — synchronous SDK entry point with handle-based API
- **AsyncKubeRayClient** — async/await variant mirroring all sync methods
- **Cluster Management** — create, scale, monitor, and delete RayClusters
    - Simple mode (flat `workers`/`cpus`/`gpus`/`memory` parameters)
    - Advanced mode (explicit `WorkerGroup` list for heterogeneous clusters)
    - Custom head node configuration via `HeadNodeConfig`
    - Autoscaling support with min/max replicas
- **Job Submission** — two modes for running Ray jobs
    - Standalone RayJob via KubeRay CRD (disposable cluster)
    - Dashboard submission to running clusters via Ray Dashboard REST API
    - Log streaming, progress tracking, artifact download
- **Ray Serve** — deploy, update, and manage RayService resources
- **Storage** — PVC attachment with new and existing claims via `StorageVolume`
- **Runtime Environment** — pip/conda packages, env vars, working directory via `RuntimeEnv`
- **Experiment Tracking** — MLflow integration via `ExperimentTracking`
- **OpenShift Integration** — hardware profiles, Kueue queues, Route auto-creation
- **Error Handling** — domain-specific error hierarchy with K8s error translation
- **Retry** — configurable retry with exponential backoff for transient errors
- **Auth** — kube-authkit delegation with OIDC, token, and auto-detection support

### API Surface

| Class | Description |
|---|---|
| `KubeRayClient` | Main sync client |
| `AsyncKubeRayClient` | Main async client |
| `SDKConfig` | Client-wide configuration |
| `ClusterHandle` / `AsyncClusterHandle` | Cluster operations |
| `JobHandle` / `AsyncJobHandle` | Job operations |
| `ServiceHandle` / `AsyncServiceHandle` | Service operations |
| `WorkerGroup` | Worker group configuration |
| `HeadNodeConfig` | Head node resource overrides |
| `StorageVolume` | PVC attachment |
| `RuntimeEnv` | Runtime environment |
| `ExperimentTracking` | MLflow integration |
