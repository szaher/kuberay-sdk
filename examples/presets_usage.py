"""Preset configurations — quickly create clusters from named templates.

Task: T066

Presets provide sensible default configurations for common use cases so you
can create a cluster with a single keyword instead of specifying every
resource parameter.

Built-in presets:
  - ``dev``             — lightweight single-worker cluster for development
  - ``gpu-single``      — single GPU training node with more memory
  - ``data-processing`` — multi-node CPU cluster for data pipelines

You can also override any preset default by passing explicit parameters.
"""

from kuberay_sdk import KubeRayClient
from kuberay_sdk.presets import Preset, get_preset, list_presets


def main() -> None:
    # ------------------------------------------------------------------
    # 1. List all available presets.
    # ------------------------------------------------------------------
    print("=== Available presets ===\n")

    presets = list_presets()
    for preset in presets:
        print(f"  [{preset.name}]")
        print(f"    Description:   {preset.description}")
        print(f"    Workers:       {preset.workers}")
        print(f"    Head CPU/Mem:  {preset.head_cpu} / {preset.head_memory}")
        print(f"    Worker CPU/Mem: {preset.worker_cpu} / {preset.worker_memory}")
        print(f"    Worker GPU:    {preset.worker_gpu}")
        print(f"    Ray version:   {preset.ray_version}")
        print()

    # ------------------------------------------------------------------
    # 2. Look up a specific preset by name.
    # ------------------------------------------------------------------
    print("=== Look up the 'gpu-single' preset ===\n")

    gpu_preset = get_preset("gpu-single")
    print(f"  Name:        {gpu_preset.name}")
    print(f"  Description: {gpu_preset.description}")
    print(f"  Workers:     {gpu_preset.workers}")
    print(f"  GPU count:   {gpu_preset.worker_gpu}")

    # ------------------------------------------------------------------
    # 3. Create a cluster from a preset (dry-run to preview).
    # ------------------------------------------------------------------
    print("\n=== Dry-run: cluster from 'dev' preset ===\n")

    # NOTE: Requires kubeconfig to be configured
    client = KubeRayClient()

    # Pass preset="dev" to apply the dev preset defaults.
    # dry_run=True previews the manifest without creating anything.
    result = client.create_cluster(
        "my-dev-cluster",
        preset="dev",
        dry_run=True,
    )

    print(f"  Result: {result!r}")
    print(f"\n{result.to_yaml()}")

    # ------------------------------------------------------------------
    # 4. Override preset defaults with explicit parameters.
    # ------------------------------------------------------------------
    print("=== Dry-run: preset with overrides ===\n")

    # Start from the data-processing preset but bump workers to 8 and
    # increase per-worker memory. Explicit values take precedence over
    # the preset defaults.
    overridden = client.create_cluster(
        "custom-data-cluster",
        preset="data-processing",
        workers=8,
        memory_per_worker="8Gi",
        labels={"team": "data-eng"},
        dry_run=True,
    )

    manifest = overridden.to_dict()
    print(f"  Kind:      {manifest['kind']}")
    print(f"  Name:      {manifest['metadata']['name']}")
    print(f"\n{overridden.to_yaml()}")

    # ------------------------------------------------------------------
    # 5. Use a Preset object directly (advanced usage).
    # ------------------------------------------------------------------
    print("=== Dry-run: custom Preset object ===\n")

    # You can construct your own Preset and pass it directly instead of
    # using a built-in name string.
    custom_preset = Preset(
        name="custom-large",
        description="Large multi-GPU training cluster",
        workers=8,
        head_cpu="4",
        head_memory="8Gi",
        worker_cpu="8",
        worker_memory="32Gi",
        worker_gpu=2,
        ray_version="2.41.0",
    )

    custom_result = client.create_cluster(
        "large-training",
        preset=custom_preset,
        dry_run=True,
    )

    print(f"  Custom preset result: {custom_result!r}")
    print(f"\n{custom_result.to_yaml()}")

    print("All preset examples completed successfully.")


if __name__ == "__main__":
    main()
