# Quickstart: Rich Display & Notebook Integration

## Installation

```bash
# Terminal rich output (progress bars, styled tables, colored logs)
pip install kuberay-sdk[rich]

# Notebook widgets (ipywidgets progress bars, HTML tables, action buttons)
pip install kuberay-sdk[notebook]

# Both terminal and notebook support
pip install kuberay-sdk[display]
```

## Terminal Usage

After installing `kuberay-sdk[rich]`, rich display activates automatically:

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()

# Progress bar appears automatically during wait
cluster = client.create_cluster("my-cluster", workers=4)
cluster.wait_until_ready()  # Shows: ⠋ CREATING ━━━━━━━━━━ 12s

# Styled tables with color-coded states
from kuberay_sdk import display
clusters = client.list_clusters()
display(clusters)
# ┌─────────────┬───────────┬─────────┬─────────┐
# │ NAME        │ NAMESPACE │ STATE   │ WORKERS │
# ├─────────────┼───────────┼─────────┼─────────┤
# │ my-cluster  │ default   │ RUNNING │ 4       │
# │ old-cluster │ default   │ FAILED  │ 0       │
# └─────────────┴───────────┴─────────┴─────────┘
```

## Notebook Usage

After installing `kuberay-sdk[notebook]`, notebook widgets activate automatically:

```python
# In a Jupyter notebook cell
from kuberay_sdk import KubeRayClient

client = KubeRayClient()
cluster = client.create_cluster("my-cluster", workers=4)

# ipywidgets progress bar renders inline
cluster.wait_until_ready()

# Evaluating a handle renders an HTML card with action buttons
cluster  # Shows styled card with Delete, Scale, Dashboard buttons
```

## Disabling Rich Display

```python
# Disable progress bar for a specific operation
cluster.wait_until_ready(progress=False)

# Disable globally via environment variable
# export KUBERAY_DISPLAY=plain
```

## Colored Log Streaming

```python
# Terminal: colored log output
for line in job.logs(stream=True, follow=True):
    pass  # Automatically color-coded by log level

# Notebook: HTML-styled log output
```

## CLI

The `kuberay` CLI automatically uses rich tables when the `[rich]` extra is installed:

```bash
kuberay cluster list
# Renders a styled table with color-coded states

kuberay cluster list --output json
# JSON output (always plain, never styled)
```
