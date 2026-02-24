"""KubeRay CLI entry point (T041, T045).

Provides the ``kuberay`` command-line interface with subcommands for
managing RayClusters, RayJobs, RayServices, and cluster capabilities.
"""

from __future__ import annotations

from typing import Any

import click

from kuberay_sdk.cli.cluster import cluster
from kuberay_sdk.cli.formatters import format_json, format_table
from kuberay_sdk.cli.job import job
from kuberay_sdk.cli.service import service
from kuberay_sdk.errors import KubeRayError


@click.group()
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace.")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format.",
)
@click.option(
    "--config",
    default=None,
    type=click.Path(),
    help="Config file path.",
)
@click.version_option(package_name="kuberay-sdk")
@click.pass_context
def cli(ctx: click.Context, namespace: str | None, output: str, config: str | None) -> None:
    """KubeRay SDK command-line interface."""
    ctx.ensure_object(dict)
    ctx.obj["namespace"] = namespace
    ctx.obj["output"] = output
    ctx.obj["config"] = config


cli.add_command(cluster)
cli.add_command(job)
cli.add_command(service)


def _get_client(ctx: click.Context) -> Any:
    """Create a KubeRayClient from CLI context."""
    from kuberay_sdk.client import KubeRayClient
    from kuberay_sdk.config import SDKConfig

    config_kwargs: dict[str, Any] = {}
    if ctx.obj.get("namespace"):
        config_kwargs["namespace"] = ctx.obj["namespace"]
    config = SDKConfig(**config_kwargs) if config_kwargs else None
    return KubeRayClient(config=config)


@cli.command()
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace (overrides global).")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default=None, help="Output format.")
@click.pass_context
def capabilities(ctx: click.Context, namespace: str | None, output: str | None) -> None:
    """Discover cluster capabilities (KubeRay, GPU, Kueue, OpenShift)."""
    try:
        client = _get_client(ctx)
        caps = client.get_capabilities()
        fmt = output or ctx.obj.get("output", "table")

        if fmt == "json":
            data = {
                "kuberay": caps.kuberay_version if caps.kuberay_installed else "not installed",
                "gpu": ", ".join(caps.gpu_types) if caps.gpu_available else "not available",
                "kueue": "available" if caps.kueue_available else "not installed",
                "openshift": "detected" if caps.openshift else "not detected",
            }
            click.echo(format_json(data))
        else:
            headers = ["CAPABILITY", "STATUS"]
            rows = [
                ["KubeRay", caps.kuberay_version or "not installed"],
                ["GPU", ", ".join(caps.gpu_types) if caps.gpu_available and caps.gpu_types else ("not available" if caps.gpu_available is False else "unknown")],
                ["Kueue", "available" if caps.kueue_available else "not installed"],
                ["OpenShift", "detected" if caps.openshift else "not detected"],
            ]
            click.echo(format_table(headers, rows))
    except KubeRayError as err:
        click.echo(f"Error: {err}", err=True)
        if err.remediation:
            click.echo(f"To fix:\n{err.remediation}", err=True)
        raise SystemExit(1) from None
