# Examples

Runnable examples demonstrating common kuberay-sdk workflows. Each example includes the full source code with inline comments explaining each step.

## Python Scripts

| Example | Description |
|---|---|
| [Cluster Basics](cluster-basics.md) | Create, monitor, scale, and delete a Ray cluster |
| [Job Submission](job-submission.md) | Submit jobs via CRD and Dashboard API, stream logs |
| [Advanced Config](advanced-config.md) | Worker groups, storage, runtime env, tolerations |
| [Async Client](async-client.md) | Concurrent operations with AsyncKubeRayClient |
| [Ray Serve Deployment](ray-serve-deployment.md) | Deploy, update, and manage Ray Serve apps |
| [OpenShift Features](openshift-features.md) | Hardware profiles, Kueue queues, platform detection |

### New in v0.2.0

| Example | Description |
|---|---|
| [Convenience Imports](convenience-imports.md) | Import common types from the top-level package |
| [Config & Env Vars](config-env-vars.md) | Config file and environment variable precedence |
| [Dry-Run Preview](dry-run-preview.md) | Preview CRD manifests without creating resources |
| [Presets](presets-usage.md) | Built-in cluster configuration presets |
| [Progress Callbacks](progress-callbacks.md) | Monitor long-running wait operations |
| [Compound Operations](compound-operations.md) | Create cluster and submit job in one call |
| [Capability Discovery](capability-discovery.md) | Detect cluster features before operations |
| [CLI Usage](cli-usage.md) | Manage Ray resources from the terminal |

## Jupyter Notebooks

| Notebook | Description |
|---|---|
| [MNIST Training](mnist_training.ipynb) | Distributed MNIST training on a Ray cluster |

## Running the examples

### Prerequisites

- kuberay-sdk installed (`pip install kuberay-sdk`)
- A Kubernetes cluster with KubeRay operator
- kubectl configured with cluster access

### Python scripts

```bash
python examples/cluster_basics.py
```

### Jupyter notebooks

```bash
pip install jupyter
jupyter notebook examples/mnist_training.ipynb
```

## Downloading examples

Each example page includes a link to download the original source file (`.py` or `.ipynb`).
