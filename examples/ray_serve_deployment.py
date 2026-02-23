"""Ray Serve deployment — deploy, inspect, update, and delete a RayService.

This example shows how to:
1. Deploy a Ray Serve application from a Python import path
2. Check service status and endpoint URL
3. Update the number of replicas
4. Clean up the service
"""

from kuberay_sdk import KubeRayClient
from kuberay_sdk.models.runtime_env import RuntimeEnv


def main() -> None:
    client = KubeRayClient()

    # Deploy a Ray Serve application.
    # `import_path` points to a module:variable — e.g., "my_app.serve:deployment".
    print("Deploying Ray Serve application...")
    service = client.create_service(
        "text-classifier",
        import_path="my_app.serve:app",
        num_replicas=2,
        workers=2,
        cpus_per_worker=2,
        memory_per_worker="4Gi",
        runtime_env=RuntimeEnv(
            pip=["transformers", "torch"],
            env_vars={"MODEL_NAME": "distilbert-base-uncased"},
        ),
    )

    # Check the service status.
    status = service.status()
    print(f"Service: {status.name}")
    print(f"  State:    {status.state}")
    print(f"  Replicas: {status.replicas_ready}/{status.replicas_desired}")
    print(f"  Endpoint: {status.endpoint_url}")
    if status.route_url:
        print(f"  Route:    {status.route_url}")

    # Update the replica count (e.g., scale up for more traffic).
    print("\nScaling to 4 replicas...")
    service.update(num_replicas=4)

    status = service.status()
    print(f"  Replicas after update: {status.replicas_ready}/{status.replicas_desired}")

    # Update the application code by changing the import path and runtime env.
    print("\nUpdating application...")
    service.update(
        import_path="my_app.serve_v2:app",
        runtime_env=RuntimeEnv(
            pip=["transformers>=4.40", "torch"],
            env_vars={"MODEL_NAME": "bert-base-uncased"},
        ),
    )

    # List all services in the namespace.
    print("\nAll services:")
    for svc in client.list_services():
        print(f"  {svc.name} — {svc.state} ({svc.replicas_ready}/{svc.replicas_desired})")

    # Clean up.
    print("\nDeleting service...")
    service.delete()
    print("Done.")


if __name__ == "__main__":
    main()
