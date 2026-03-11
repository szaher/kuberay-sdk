# Installation

## Prerequisites

Before installing kuberay-sdk, ensure you have:

- **Python 3.10+**
- **A Kubernetes cluster** with the [KubeRay operator](https://ray-project.github.io/kuberay/deploy/installation/) installed
- **kubectl** configured with access to the target cluster (a valid kubeconfig)

## Install the SDK

```bash
pip install kuberay-sdk
```

## Authentication Setup

kuberay-sdk uses [kube-authkit](https://pypi.org/project/kube-authkit/) for Kubernetes authentication. By default, it auto-detects credentials from your kubeconfig or in-cluster service account.

### Default (kubeconfig auto-detection)

If you have a working `kubectl` setup, no extra configuration is needed:

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()  # Uses kubeconfig automatically
```

### Explicit authentication

For environments that require specific auth methods (OIDC, token-based, etc.):

```python
from kube_authkit import AuthConfig
from kuberay_sdk import KubeRayClient, SDKConfig

config = SDKConfig(
    auth=AuthConfig(method="oidc", oidc_issuer="https://sso.example.com", client_id="my-app"),
)
client = KubeRayClient(config=config)
```

## Optional Extras

The base package provides all SDK functionality with plain text output. Install optional extras for enhanced display:

```bash
# Rich terminal output (styled tables, progress bars, colored logs)
pip install kuberay-sdk[rich]

# Notebook widgets (HTML tables, ipywidgets progress bars, action buttons)
pip install kuberay-sdk[notebook]

# Both terminal and notebook support
pip install kuberay-sdk[display]
```

See [Rich Display & Notebook Integration](../rich-display.md) for usage details.

## Verify the installation

After installing, verify that the SDK can connect to your cluster and detect the KubeRay operator:

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()
clusters = client.list_clusters()
print(f"Found {len(clusters)} existing clusters")
```

If the KubeRay operator is not installed, you'll see a `KubeRayOperatorNotFoundError` with a link to the installation guide.

## Next steps

Once installed, head to the [Quick Start](quick-start.md) to create your first cluster, submit a job, and deploy a service.
