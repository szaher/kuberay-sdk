# Troubleshooting

This guide covers common issues you may encounter when using the kuberay-sdk and how to resolve them.

---

## Cluster Stuck in Creating State

### Symptoms

- `cluster.status()` returns `CREATING` for an extended period (more than 5 minutes).
- `cluster.wait_until_ready()` times out with a `TimeoutError`.
- Head pod or worker pods remain in `Pending` or `ContainerCreating` state.

### Common Causes

1. **Insufficient cluster resources** -- the Kubernetes cluster does not have enough CPU, memory, or GPU resources to schedule the Ray pods.
2. **Missing or incorrect container image** -- the Ray image cannot be pulled (e.g., wrong tag, private registry without credentials).
3. **PersistentVolumeClaim (PVC) not bound** -- storage volumes referenced in the cluster spec are not available.
4. **Node selector or tolerations mismatch** -- the pods require specific node labels or tolerations that no node satisfies.

### Resolution

**Step 1: Check pod status**

```bash
kubectl get pods -l ray.io/cluster=<cluster-name> -n <namespace>
```

**Step 2: Inspect pending pod events**

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Look for events such as `FailedScheduling`, `ImagePullBackOff`, or `Unschedulable`.

**Step 3: Verify resource availability**

```bash
kubectl describe nodes | grep -A 5 "Allocated resources"
```

**Step 4: Check image pull status**

```bash
kubectl get events -n <namespace> --field-selector reason=Failed
```

If images are in a private registry, ensure an `imagePullSecret` is configured.

**Step 5: Fix and recreate**

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()
# Delete the stuck cluster
cluster = client.get_cluster("my-cluster")
cluster.delete()

# Recreate with corrected settings
cluster = client.create_cluster(
    "my-cluster",
    workers=2,
    image="rayproject/ray:2.9.0",  # Use a valid, pullable image
    memory_per_worker="4Gi",
)
cluster.wait_until_ready(timeout=600)
```

---

## Dashboard Unreachable

### Symptoms

- `cluster.dashboard_url()` raises a connection error or times out.
- Cannot access the Ray Dashboard in a browser.
- `cluster.submit_job(...)` fails because it cannot connect to the dashboard.

### Common Causes

1. **Head pod is not running** -- the Ray head pod has not started or has crashed.
2. **Dashboard port is not exposed** -- no port-forward, Ingress, or OpenShift Route is configured.
3. **Network policy blocking access** -- a NetworkPolicy prevents traffic to port 8265.
4. **Firewall or proxy interference** -- corporate proxies or firewalls block the connection.

### Resolution

**Step 1: Verify the head pod is running**

```bash
kubectl get pods -l ray.io/node-type=head,ray.io/cluster=<cluster-name> -n <namespace>
```

The head pod should be in `Running` status with `1/1` containers ready.

**Step 2: Set up port forwarding manually**

```bash
kubectl port-forward svc/<cluster-name>-head-svc 8265:8265 -n <namespace>
```

Then access the dashboard at `http://localhost:8265`.

**Step 3: Check if an Ingress or Route exists**

```bash
# For Kubernetes Ingress
kubectl get ingress -n <namespace>

# For OpenShift Routes
kubectl get routes -n <namespace>
```

**Step 4: Check network policies**

```bash
kubectl get networkpolicies -n <namespace>
```

If a policy exists, ensure it allows ingress on port 8265 for the head service.

**Step 5: Use the SDK port-forward fallback**

The SDK automatically attempts port-forwarding when no Ingress or Route is detected:

```python
cluster = client.get_cluster("my-cluster")
url = cluster.dashboard_url()  # Auto port-forward
print(f"Dashboard available at: {url}")
```

---

## Authentication Failures

### Symptoms

- `KubeRayClient()` raises an `AuthenticationError` or `ConfigException`.
- Operations fail with `HTTP 401 Unauthorized` or `HTTP 403 Forbidden`.
- Error message mentions expired token or invalid credentials.

### Common Causes

1. **Expired authentication token** -- OIDC or bearer tokens have a limited lifetime.
2. **Wrong kubeconfig context** -- the active context points to a different cluster.
3. **Missing RBAC permissions** -- the service account lacks permissions for KubeRay CRDs.
4. **Invalid or missing kubeconfig** -- the `KUBECONFIG` environment variable is not set or points to a nonexistent file.

### Resolution

**Step 1: Verify current context**

```bash
kubectl config current-context
kubectl config get-contexts
```

Switch to the correct context if needed:

```bash
kubectl config use-context <correct-context>
```

**Step 2: Refresh expired tokens**

For OIDC-based authentication (e.g., OpenShift):

```bash
# OpenShift
oc login --server=https://<api-server> --token=<new-token>

# Generic OIDC
kubectl oidc-login
```

**Step 3: Verify RBAC permissions**

```bash
kubectl auth can-i list rayclusters.ray.io -n <namespace>
kubectl auth can-i create rayclusters.ray.io -n <namespace>
kubectl auth can-i delete rayclusters.ray.io -n <namespace>
```

If any return `no`, ask your cluster administrator to grant the required permissions.

**Step 4: Configure the SDK with explicit auth**

```python
from kuberay_sdk import KubeRayClient
from kuberay_sdk.config import SDKConfig, AuthConfig

# Explicit kubeconfig path
config = SDKConfig(auth=AuthConfig(kubeconfig_path="/path/to/kubeconfig"))
client = KubeRayClient(config=config)

# Or with a specific context
config = SDKConfig(auth=AuthConfig(context="my-cluster-context"))
client = KubeRayClient(config=config)
```

---

## KubeRay Operator Not Found

### Symptoms

- `KubeRayClient()` raises an error indicating that KubeRay CRDs are not installed.
- `kubectl get crd rayclusters.ray.io` returns `NotFound`.
- Creating clusters fails with `the server doesn't have a resource type "rayclusters"`.

### Common Causes

1. **KubeRay operator is not installed** -- the operator and its CRDs have not been deployed to the cluster.
2. **Operator is installed in a different namespace** -- the operator may be running but not watching the target namespace.
3. **CRD version mismatch** -- an older version of the CRDs is installed that does not support the requested API version.

### Resolution

**Step 1: Check if CRDs exist**

```bash
kubectl get crd rayclusters.ray.io
kubectl get crd rayjobs.ray.io
kubectl get crd rayservices.ray.io
```

**Step 2: Install KubeRay operator via Helm**

```bash
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm repo update

# Install the operator
helm install kuberay-operator kuberay/kuberay-operator \
  --namespace kuberay-system \
  --create-namespace
```

**Step 3: Verify the operator is running**

```bash
kubectl get pods -n kuberay-system
kubectl logs -l app.kubernetes.io/name=kuberay-operator -n kuberay-system
```

**Step 4: Verify CRDs are registered**

```bash
kubectl api-resources | grep ray.io
```

Expected output:

```
rayclusters    ray.io/v1    true    RayCluster
rayjobs        ray.io/v1    true    RayJob
rayservices    ray.io/v1    true    RayService
```

**Step 5: Test with the SDK**

```python
from kuberay_sdk import KubeRayClient

client = KubeRayClient()  # Should succeed now
clusters = client.list_clusters()
print(f"Found {len(clusters)} clusters")
```

---

## Job Timeout

### Symptoms

- `job.wait()` raises a `TimeoutError`.
- Job status remains `RUNNING` or `PENDING` for longer than expected.
- Job pods are repeatedly restarting (CrashLoopBackOff).

### Common Causes

1. **Insufficient resources** -- the job requires more CPU, memory, or GPUs than available.
2. **Application-level errors** -- the user script has bugs, infinite loops, or deadlocks.
3. **Wait timeout too short** -- the default `wait(timeout=3600)` may be insufficient for long-running jobs.
4. **Worker pods failing** -- workers crash before the job can complete.
5. **Network issues** -- the job cannot download dependencies specified in `runtime_env`.

### Resolution

**Step 1: Check job status and events**

```bash
kubectl get rayjob <job-name> -n <namespace> -o yaml
kubectl describe rayjob <job-name> -n <namespace>
```

**Step 2: Check pod logs for errors**

```bash
# Head pod logs
kubectl logs -l ray.io/cluster=<job-name>,ray.io/node-type=head -n <namespace>

# Worker pod logs
kubectl logs -l ray.io/cluster=<job-name>,ray.io/node-type=worker -n <namespace>
```

**Step 3: Use SDK to stream logs**

```python
job = client.get_job("my-job")
# Stream logs in real-time
for line in job.logs(stream=True, follow=True):
    print(line)
```

**Step 4: Increase the timeout**

```python
# Default is 3600 seconds (1 hour)
job.wait(timeout=7200)  # 2 hours
```

**Step 5: Check events for scheduling issues**

```bash
kubectl get events -n <namespace> --sort-by='.metadata.creationTimestamp' | grep <job-name>
```

**Step 6: Fix and resubmit**

```python
# Delete the failed job
job = client.get_job("my-failed-job")
job.stop()

# Resubmit with more resources
job = client.create_job(
    "my-job-v2",
    entrypoint="python train.py",
    workers=4,
    memory_per_worker="8Gi",
    gpus_per_worker=1,
)
job.wait(timeout=7200)
```

---

## Cluster Delete Fails or Hangs

### Symptoms

- `cluster.delete()` hangs or raises an error.
- The RayCluster custom resource remains after deletion.
- Finalizers prevent the resource from being removed.

### Common Causes

1. **Active jobs are still running** -- the SDK warns before deleting clusters with running jobs.
2. **Finalizers blocking deletion** -- custom finalizers on the resource prevent garbage collection.
3. **Operator is not running** -- the KubeRay operator handles cleanup; if it is down, deletion stalls.

### Resolution

**Step 1: Force delete via SDK**

```python
cluster.delete(force=True)  # Skips the running-jobs warning
```

**Step 2: Check for stuck finalizers**

```bash
kubectl get raycluster <name> -n <namespace> -o json | jq '.metadata.finalizers'
```

If finalizers are present and the operator is not running, remove them manually:

```bash
kubectl patch raycluster <name> -n <namespace> --type=merge -p '{"metadata":{"finalizers":[]}}'
```

**Step 3: Verify the operator is healthy**

```bash
kubectl get pods -n kuberay-system
kubectl logs -l app.kubernetes.io/name=kuberay-operator -n kuberay-system --tail=50
```

---

## RuntimeEnv or Pip Dependencies Fail to Install

### Symptoms

- Job fails immediately after starting with import errors.
- Worker logs show `pip install` failures.
- Error message mentions network timeouts or package-not-found.

### Common Causes

1. **No internet access from pods** -- cluster network policies or air-gapped environments block PyPI access.
2. **Incorrect package names** -- typos in the pip requirements list.
3. **Conflicting dependencies** -- packages have incompatible version requirements.

### Resolution

**Step 1: Check worker logs for pip errors**

```bash
kubectl logs <worker-pod> -n <namespace> | grep -i "pip\|error\|fail"
```

**Step 2: Use a custom image with pre-installed dependencies**

```python
cluster = client.create_cluster(
    "my-cluster",
    image="my-registry/ray-custom:latest",  # Pre-built image with all deps
    workers=4,
)
```

**Step 3: Specify a custom pip index**

```python
job = client.create_job(
    "my-job",
    entrypoint="python train.py",
    runtime_env={
        "pip": {
            "packages": ["torch==2.1.0", "transformers"],
            "pip_options": "--index-url https://my-pypi-mirror.example.com/simple",
        },
    },
)
```

---

## Getting More Help

If the steps above do not resolve your issue:

1. **Enable debug logging** to get more detailed output:

    ```python
    import logging
    logging.basicConfig(level=logging.DEBUG)
    ```

2. **Collect diagnostic information**:

    ```bash
    kubectl get rayclusters,rayjobs,rayservices -n <namespace>
    kubectl get pods -n <namespace> -o wide
    kubectl get events -n <namespace> --sort-by='.metadata.creationTimestamp'
    kubectl logs -l app.kubernetes.io/name=kuberay-operator -n kuberay-system --tail=100
    ```

3. **File an issue** on the [kuberay-sdk GitHub repository](https://github.com/szaher/kuberay-sdk/issues) with the collected diagnostic output.
