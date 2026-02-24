# CLI Reference

*Added in v0.2.0*

The `kuberay` command-line tool provides a terminal interface for managing Ray clusters, jobs, and services on Kubernetes. It is installed automatically with the SDK:

```bash
pip install kuberay-sdk
```

After installation, the `kuberay` command is available in your shell. It uses your current kubeconfig context by default, just like `kubectl`.

---

## Command Tree

```
kuberay
├── cluster
│   ├── list
│   ├── create
│   ├── get
│   ├── delete
│   └── scale
├── job
│   ├── list
│   ├── create
│   ├── get
│   └── delete
├── service
│   ├── list
│   ├── create
│   ├── get
│   └── delete
└── capabilities
```

---

## Global Options

These options apply to all commands and subcommands:

| Option | Type | Default | Description |
|---|---|---|---|
| `--namespace` / `-n` | `str` | Current kubeconfig context namespace | Kubernetes namespace to operate in. |
| `--output` / `-o` | `table \| json` | `table` | Output format. `table` for human-readable, `json` for machine-parseable. |
| `--config` | `path` | `~/.kuberay/config.yaml` | Path to the kuberay configuration file. |
| `--version` | flag | -- | Print the kuberay-sdk version and exit. |

```bash title="Example: version check"
$ kuberay --version
kuberay-sdk 0.2.0
```

---

## kuberay cluster

Manage RayCluster resources.

### kuberay cluster list

List all RayClusters in the target namespace.

```bash title="Synopsis"
kuberay cluster list [OPTIONS]
```

No additional options beyond global options.

=== "Table output"

    ```bash title="Example"
    $ kuberay cluster list -n ml-team
    NAME              STATE     WORKERS   READY   AGE
    training-cluster  RUNNING   4/4       True    2h15m
    dev-cluster       RUNNING   2/2       True    45m
    staging-cluster   CREATING  0/8       False   30s
    ```

=== "JSON output"

    ```bash title="Example"
    $ kuberay cluster list -n ml-team -o json
    ```

    ```json
    [
      {
        "name": "training-cluster",
        "namespace": "ml-team",
        "state": "RUNNING",
        "workers_ready": 4,
        "workers_desired": 4,
        "head_ready": true,
        "ray_version": "2.41.0",
        "age": "2h15m"
      },
      {
        "name": "dev-cluster",
        "namespace": "ml-team",
        "state": "RUNNING",
        "workers_ready": 2,
        "workers_desired": 2,
        "head_ready": true,
        "ray_version": "2.41.0",
        "age": "45m"
      },
      {
        "name": "staging-cluster",
        "namespace": "ml-team",
        "state": "CREATING",
        "workers_ready": 0,
        "workers_desired": 8,
        "head_ready": false,
        "ray_version": "2.41.0",
        "age": "30s"
      }
    ]
    ```

### kuberay cluster create

Create a new RayCluster.

```bash title="Synopsis"
kuberay cluster create --name NAME [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--name` | `str` | *required* | Name of the RayCluster to create. |
| `--workers` | `int` | `1` | Number of worker replicas. |
| `--preset` | `str` | -- | Hardware profile preset (e.g., `small`, `medium`, `large`, `gpu-large`). Overrides per-worker resource flags. |
| `--cpus-per-worker` | `float` | `1.0` | CPU cores per worker pod. |
| `--memory-per-worker` | `str` | `2Gi` | Memory per worker pod (e.g., `4Gi`, `16Gi`). |
| `--gpus-per-worker` | `int` | `0` | GPUs per worker pod. |
| `--dry-run` | flag | `false` | Print the generated YAML manifest without creating the cluster. |
| `--namespace` / `-n` | `str` | Global default | Override the namespace for this command. |

```bash title="Example: create a 4-worker GPU cluster"
$ kuberay cluster create --name training-cluster --workers 4 --gpus-per-worker 1 --memory-per-worker 16Gi -n ml-team
Cluster "training-cluster" created in namespace "ml-team".
Waiting for cluster to be ready...
Cluster "training-cluster" is RUNNING (4/4 workers ready).
```

!!! tip "Presets simplify common configurations"
    If your cluster administrator has defined hardware presets, you can use `--preset` instead of specifying individual resource flags:

    ```bash
    kuberay cluster create --name my-cluster --workers 4 --preset gpu-large
    ```

```bash title="Example: dry-run to preview the manifest"
$ kuberay cluster create --name preview-cluster --workers 2 --cpus-per-worker 4 --dry-run
```

```yaml
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: preview-cluster
  namespace: default
spec:
  headGroupSpec:
    rayStartParams:
      dashboard-host: "0.0.0.0"
    template:
      spec:
        containers:
          - name: ray-head
            resources:
              limits:
                cpu: "2"
                memory: "4Gi"
  workerGroupSpecs:
    - groupName: default-worker
      replicas: 2
      template:
        spec:
          containers:
            - name: ray-worker
              resources:
                limits:
                  cpu: "4"
                  memory: "2Gi"
```

### kuberay cluster get

Get details of a specific RayCluster.

```bash title="Synopsis"
kuberay cluster get --name NAME [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--name` | `str` | *required* | Name of the RayCluster. |

=== "Table output"

    ```bash title="Example"
    $ kuberay cluster get --name training-cluster
    NAME                STATE    WORKERS   READY   RAY VERSION   AGE
    training-cluster    RUNNING  4/4       True    2.41.0        2h15m

    HEAD NODE:
      IP:     10.244.0.12
      CPU:    2
      Memory: 4Gi

    WORKER GROUPS:
      NAME              REPLICAS   CPU   MEMORY   GPU   STATUS
      default-worker    4          2     8Gi      1     4/4 ready
    ```

=== "JSON output"

    ```bash title="Example"
    $ kuberay cluster get --name training-cluster -o json
    ```

    ```json
    {
      "name": "training-cluster",
      "namespace": "ml-team",
      "state": "RUNNING",
      "workers_ready": 4,
      "workers_desired": 4,
      "head_ready": true,
      "ray_version": "2.41.0",
      "age": "2h15m",
      "head": {
        "ip": "10.244.0.12",
        "cpu": "2",
        "memory": "4Gi"
      },
      "worker_groups": [
        {
          "name": "default-worker",
          "replicas": 4,
          "cpu": "2",
          "memory": "8Gi",
          "gpu": 1,
          "ready": 4
        }
      ]
    }
    ```

### kuberay cluster delete

Delete a RayCluster.

```bash title="Synopsis"
kuberay cluster delete --name NAME [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--name` | `str` | *required* | Name of the RayCluster to delete. |
| `--force` | flag | `false` | Skip graceful shutdown and delete immediately. |

```bash title="Example: graceful delete"
$ kuberay cluster delete --name training-cluster
Cluster "training-cluster" deleted.
```

```bash title="Example: force delete"
$ kuberay cluster delete --name stuck-cluster --force
Cluster "stuck-cluster" force-deleted.
```

### kuberay cluster scale

Scale the worker count of a RayCluster.

```bash title="Synopsis"
kuberay cluster scale --name NAME --workers COUNT [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--name` | `str` | *required* | Name of the RayCluster to scale. |
| `--workers` | `int` | *required* | Target number of worker replicas. |

```bash title="Example: scale up"
$ kuberay cluster scale --name training-cluster --workers 8
Cluster "training-cluster" scaled to 8 workers.
```

```bash title="Example: scale down"
$ kuberay cluster scale --name training-cluster --workers 2
Cluster "training-cluster" scaled to 2 workers.
```

---

## kuberay job

Manage RayJob resources.

### kuberay job list

List all RayJobs in the target namespace.

```bash title="Synopsis"
kuberay job list [OPTIONS]
```

No additional options beyond global options.

=== "Table output"

    ```bash title="Example"
    $ kuberay job list -n ml-team
    NAME              STATE       CLUSTER              AGE
    training-run-01   SUCCEEDED   training-run-01      4h30m
    training-run-02   RUNNING     training-run-02      15m
    eval-job          FAILED      eval-job             1h20m
    ```

=== "JSON output"

    ```bash title="Example"
    $ kuberay job list -n ml-team -o json
    ```

    ```json
    [
      {
        "name": "training-run-01",
        "namespace": "ml-team",
        "state": "SUCCEEDED",
        "cluster": "training-run-01",
        "entrypoint": "python train.py --epochs 10",
        "age": "4h30m"
      },
      {
        "name": "training-run-02",
        "namespace": "ml-team",
        "state": "RUNNING",
        "cluster": "training-run-02",
        "entrypoint": "python train.py --epochs 20",
        "age": "15m"
      },
      {
        "name": "eval-job",
        "namespace": "ml-team",
        "state": "FAILED",
        "cluster": "eval-job",
        "entrypoint": "python eval.py",
        "age": "1h20m"
      }
    ]
    ```

### kuberay job create

Create a new RayJob. By default, a standalone RayJob provisions its own disposable cluster.

```bash title="Synopsis"
kuberay job create --name NAME --entrypoint ENTRYPOINT [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--name` | `str` | *required* | Name of the RayJob to create. |
| `--entrypoint` | `str` | *required* | The shell command to execute (e.g., `"python train.py --epochs 10"`). |
| `--cluster` | `str` | -- | Submit to an existing RayCluster instead of creating a disposable one. |
| `--workers` | `int` | `1` | Number of worker replicas (ignored when `--cluster` is set). |
| `--cpus-per-worker` | `float` | `1.0` | CPU cores per worker pod. |
| `--memory-per-worker` | `str` | `2Gi` | Memory per worker pod. |
| `--gpus-per-worker` | `int` | `0` | GPUs per worker pod. |
| `--namespace` / `-n` | `str` | Global default | Override the namespace for this command. |

```bash title="Example: standalone job with disposable cluster"
$ kuberay job create --name training-run --entrypoint "python train.py --epochs 10" --workers 4 --gpus-per-worker 1
Job "training-run" created in namespace "default".
```

```bash title="Example: submit to an existing cluster"
$ kuberay job create --name eval-run --entrypoint "python eval.py" --cluster training-cluster
Job "eval-run" submitted to cluster "training-cluster".
```

### kuberay job get

Get details of a specific RayJob.

```bash title="Synopsis"
kuberay job get --name NAME [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--name` | `str` | *required* | Name of the RayJob. |

=== "Table output"

    ```bash title="Example"
    $ kuberay job get --name training-run
    NAME            STATE      CLUSTER          ENTRYPOINT                       AGE
    training-run    RUNNING    training-run     python train.py --epochs 10      15m
    ```

=== "JSON output"

    ```bash title="Example"
    $ kuberay job get --name training-run -o json
    ```

    ```json
    {
      "name": "training-run",
      "namespace": "default",
      "state": "RUNNING",
      "cluster": "training-run",
      "entrypoint": "python train.py --epochs 10",
      "workers_ready": 4,
      "workers_desired": 4,
      "age": "15m"
    }
    ```

### kuberay job delete

Delete a RayJob. For standalone jobs, this also tears down the associated disposable cluster.

```bash title="Synopsis"
kuberay job delete --name NAME [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--name` | `str` | *required* | Name of the RayJob to delete. |

```bash title="Example"
$ kuberay job delete --name training-run
Job "training-run" deleted.
```

---

## kuberay service

Manage RayService resources.

### kuberay service list

List all RayServices in the target namespace.

```bash title="Synopsis"
kuberay service list [OPTIONS]
```

No additional options beyond global options.

=== "Table output"

    ```bash title="Example"
    $ kuberay service list -n ml-team
    NAME         STATE     REPLICAS   ENDPOINT                              AGE
    my-llm       RUNNING   2/2        http://my-llm-serve-svc:8000          3d
    classifier   RUNNING   4/4        http://classifier-serve-svc:8000      1d12h
    staging-app  CREATING  0/1        --                                    2m
    ```

=== "JSON output"

    ```bash title="Example"
    $ kuberay service list -n ml-team -o json
    ```

    ```json
    [
      {
        "name": "my-llm",
        "namespace": "ml-team",
        "state": "RUNNING",
        "replicas_ready": 2,
        "replicas_desired": 2,
        "endpoint_url": "http://my-llm-serve-svc:8000",
        "age": "3d"
      },
      {
        "name": "classifier",
        "namespace": "ml-team",
        "state": "RUNNING",
        "replicas_ready": 4,
        "replicas_desired": 4,
        "endpoint_url": "http://classifier-serve-svc:8000",
        "age": "1d12h"
      },
      {
        "name": "staging-app",
        "namespace": "ml-team",
        "state": "CREATING",
        "replicas_ready": 0,
        "replicas_desired": 1,
        "endpoint_url": null,
        "age": "2m"
      }
    ]
    ```

### kuberay service create

Create a new RayService deployment.

```bash title="Synopsis"
kuberay service create --name NAME --import-path IMPORT_PATH [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--name` | `str` | *required* | Name of the RayService to create. |
| `--import-path` | `str` | *required* | Python import path for the Serve deployment (e.g., `serve_app:deployment`). |
| `--num-replicas` | `int` | `1` | Number of Serve replicas. |
| `--workers` | `int` | `1` | Number of worker replicas in the backing cluster. |
| `--cpus-per-worker` | `float` | `1.0` | CPU cores per worker pod. |
| `--memory-per-worker` | `str` | `2Gi` | Memory per worker pod. |
| `--gpus-per-worker` | `int` | `0` | GPUs per worker pod. |
| `--namespace` / `-n` | `str` | Global default | Override the namespace for this command. |

```bash title="Example: deploy a Serve application"
$ kuberay service create --name my-llm --import-path "serve_app:deployment" --num-replicas 2 --gpus-per-worker 1 --memory-per-worker 16Gi
Service "my-llm" created in namespace "default".
Waiting for service to be ready...
Service "my-llm" is RUNNING (endpoint: http://my-llm-serve-svc:8000).
```

### kuberay service get

Get details of a specific RayService.

```bash title="Synopsis"
kuberay service get --name NAME [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--name` | `str` | *required* | Name of the RayService. |

=== "Table output"

    ```bash title="Example"
    $ kuberay service get --name my-llm
    NAME     STATE     REPLICAS   ENDPOINT                        AGE
    my-llm   RUNNING   2/2        http://my-llm-serve-svc:8000    3d

    IMPORT PATH:  serve_app:deployment

    WORKER GROUPS:
      NAME              REPLICAS   CPU   MEMORY   GPU   STATUS
      default-worker    2          1     16Gi     1     2/2 ready
    ```

=== "JSON output"

    ```bash title="Example"
    $ kuberay service get --name my-llm -o json
    ```

    ```json
    {
      "name": "my-llm",
      "namespace": "default",
      "state": "RUNNING",
      "replicas_ready": 2,
      "replicas_desired": 2,
      "endpoint_url": "http://my-llm-serve-svc:8000",
      "import_path": "serve_app:deployment",
      "age": "3d",
      "worker_groups": [
        {
          "name": "default-worker",
          "replicas": 2,
          "cpu": "1",
          "memory": "16Gi",
          "gpu": 1,
          "ready": 2
        }
      ]
    }
    ```

### kuberay service delete

Delete a RayService.

```bash title="Synopsis"
kuberay service delete --name NAME [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--name` | `str` | *required* | Name of the RayService to delete. |

```bash title="Example"
$ kuberay service delete --name my-llm
Service "my-llm" deleted.
```

---

## kuberay capabilities

Detect the capabilities of the connected Kubernetes cluster, including the KubeRay operator version, GPU availability, Kueue integration, and OpenShift features. This is useful for troubleshooting and verifying cluster setup.

```bash title="Synopsis"
kuberay capabilities [OPTIONS]
```

No additional options beyond global options.

=== "Table output"

    ```bash title="Example"
    $ kuberay capabilities
    CAPABILITY          STATUS      DETAILS
    KubeRay Operator    Available   v1.3.0
    GPU Support         Available   NVIDIA (4x A100 80GB)
    Kueue Integration   Available   v0.10.0
    OpenShift           Not Found   --
    Ray Version         Detected    2.41.0
    ```

=== "JSON output"

    ```bash title="Example"
    $ kuberay capabilities -o json
    ```

    ```json
    {
      "kuberay_operator": {
        "available": true,
        "version": "v1.3.0"
      },
      "gpu_support": {
        "available": true,
        "vendor": "NVIDIA",
        "devices": "4x A100 80GB"
      },
      "kueue": {
        "available": true,
        "version": "v0.10.0"
      },
      "openshift": {
        "available": false
      },
      "ray_version": "2.41.0"
    }
    ```

!!! tip "Run `capabilities` first when debugging"
    If you encounter issues creating clusters or jobs, `kuberay capabilities` is the fastest way to verify that the KubeRay operator is installed and functioning correctly.

---

## Output Formats

All commands support two output formats via the `--output` / `-o` flag.

### Table (default)

Human-readable tabular output, designed for terminal use:

```bash
$ kuberay cluster list
NAME              STATE     WORKERS   READY   AGE
training-cluster  RUNNING   4/4       True    2h15m
dev-cluster       RUNNING   2/2       True    45m
```

### JSON

Machine-parseable JSON output, useful for scripting and automation:

```bash
$ kuberay cluster list -o json
```

```json
[
  {
    "name": "training-cluster",
    "namespace": "default",
    "state": "RUNNING",
    "workers_ready": 4,
    "workers_desired": 4,
    "head_ready": true,
    "ray_version": "2.41.0",
    "age": "2h15m"
  },
  {
    "name": "dev-cluster",
    "namespace": "default",
    "state": "RUNNING",
    "workers_ready": 2,
    "workers_desired": 2,
    "head_ready": true,
    "ray_version": "2.41.0",
    "age": "45m"
  }
]
```

!!! tip "Pipe JSON to `jq` for filtering"
    Combine `--output json` with `jq` for powerful filtering and transformation:

    ```bash
    # Get names of all running clusters
    kuberay cluster list -o json | jq -r '.[] | select(.state == "RUNNING") | .name'

    # Count workers across all clusters
    kuberay cluster list -o json | jq '[.[].workers_ready] | add'
    ```

---

## Configuration File

The CLI reads defaults from `~/.kuberay/config.yaml` (overridable with `--config`). This avoids repeating common flags:

```yaml title="~/.kuberay/config.yaml"
namespace: ml-team
output: table
```

With this file in place, `kuberay cluster list` is equivalent to `kuberay cluster list -n ml-team -o table`.

Command-line flags always take precedence over the configuration file.

---

## See Also

- [Configuration](configuration.md) -- SDK-level configuration options (`SDKConfig`).
- [Quick Start](getting-started/quick-start.md) -- get started with the Python API.
- [Migration Guide](migration.md) -- side-by-side comparison with `kubectl` commands.
- [Troubleshooting](troubleshooting.md) -- common issues and solutions.
