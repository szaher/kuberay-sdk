"""Cluster CLI subcommands (T042).

Implements ``kuberay cluster create|list|get|delete|scale``.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import click

from kuberay_sdk.cli.formatters import format_json, format_rich_table
from kuberay_sdk.errors import KubeRayError


def _format_age(age_timedelta: timedelta) -> str:
    """Format timedelta as human-readable age (e.g., '2h', '5m', '3d')."""
    total_seconds = int(age_timedelta.total_seconds())
    if total_seconds < 60:
        return f"{total_seconds}s"
    if total_seconds < 3600:
        return f"{total_seconds // 60}m"
    if total_seconds < 86400:
        return f"{total_seconds // 3600}h"
    return f"{total_seconds // 86400}d"


def _get_client(ctx: click.Context) -> Any:
    """Create a KubeRayClient from CLI context."""
    from kuberay_sdk.client import KubeRayClient
    from kuberay_sdk.config import SDKConfig

    config_kwargs: dict[str, Any] = {}
    if ctx.obj.get("namespace"):
        config_kwargs["namespace"] = ctx.obj["namespace"]
    config = SDKConfig(**config_kwargs) if config_kwargs else None
    return KubeRayClient(config=config)


def _handle_error(err: KubeRayError) -> None:
    """Print error and remediation to stderr, then exit."""
    click.echo(f"Error: {err}", err=True)
    if err.remediation:
        click.echo(f"To fix:\n{err.remediation}", err=True)
    raise SystemExit(1)


@click.group()
def cluster() -> None:
    """Manage RayClusters."""


@cluster.command()
@click.argument("name")
@click.option("--workers", "-w", default=1, type=int, help="Number of worker replicas.")
@click.option("--preset", default=None, help="Named preset to apply.")
@click.option("--ray-version", default=None, help="Ray version.")
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace (overrides global).")
@click.pass_context
def create(
    ctx: click.Context, name: str, workers: int, preset: str | None, ray_version: str | None, namespace: str | None
) -> None:
    """Create a RayCluster."""
    try:
        client = _get_client(ctx)
        kwargs: dict[str, Any] = {"workers": workers}
        if ray_version:
            kwargs["ray_version"] = ray_version
        ns = namespace or ctx.obj.get("namespace")
        if ns:
            kwargs["namespace"] = ns
        client.create_cluster(name, **kwargs)
        click.echo(f"Cluster '{name}' created.")
    except KubeRayError as err:
        _handle_error(err)


@cluster.command("list")
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace (overrides global).")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default=None, help="Output format.")
@click.pass_context
def list_clusters(ctx: click.Context, namespace: str | None, output: str | None) -> None:
    """List RayClusters."""
    try:
        client = _get_client(ctx)
        ns = namespace or ctx.obj.get("namespace")
        kwargs: dict[str, Any] = {}
        if ns:
            kwargs["namespace"] = ns
        clusters = client.list_clusters(**kwargs)
        fmt = output or ctx.obj.get("output", "table")
        if fmt == "json":
            data = [
                {
                    "name": c.name,
                    "state": c.state,
                    "workers": c.workers_ready,
                    "age": str(c.age),
                }
                for c in clusters
            ]
            click.echo(format_json(data))
        else:
            headers = ["NAME", "STATE", "WORKERS", "AGE"]
            rows = [[c.name, c.state, str(c.workers_ready), _format_age(c.age)] for c in clusters]
            format_rich_table(headers, rows, state_column=1)
    except KubeRayError as err:
        _handle_error(err)


@cluster.command()
@click.argument("name")
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace (overrides global).")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default=None, help="Output format.")
@click.pass_context
def get(ctx: click.Context, name: str, namespace: str | None, output: str | None) -> None:
    """Get a RayCluster status."""
    try:
        client = _get_client(ctx)
        ns = namespace or ctx.obj.get("namespace")
        kwargs: dict[str, Any] = {}
        if ns:
            kwargs["namespace"] = ns
        handle = client.get_cluster(name, **kwargs)
        status = handle.status()
        fmt = output or ctx.obj.get("output", "table")
        if fmt == "json":
            data = {
                "name": status.name,
                "state": status.state,
                "workers": status.workers_ready,
                "age": str(status.age),
            }
            click.echo(format_json(data))
        else:
            headers = ["NAME", "STATE", "WORKERS", "AGE"]
            rows = [[status.name, status.state, str(status.workers_ready), _format_age(status.age)]]
            format_rich_table(headers, rows, state_column=1)
    except KubeRayError as err:
        _handle_error(err)


@cluster.command()
@click.argument("name")
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace (overrides global).")
@click.option("--force", is_flag=True, default=False, help="Force delete even if jobs are running.")
@click.pass_context
def delete(ctx: click.Context, name: str, namespace: str | None, force: bool) -> None:
    """Delete a RayCluster."""
    try:
        client = _get_client(ctx)
        ns = namespace or ctx.obj.get("namespace")
        kwargs: dict[str, Any] = {}
        if ns:
            kwargs["namespace"] = ns
        handle = client.get_cluster(name, **kwargs)
        handle.delete(force=force)
        click.echo(f"Cluster '{name}' deleted.")
    except KubeRayError as err:
        _handle_error(err)


@cluster.command()
@click.argument("name")
@click.option("--workers", "-w", required=True, type=int, help="Target number of workers.")
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace (overrides global).")
@click.pass_context
def scale(ctx: click.Context, name: str, workers: int, namespace: str | None) -> None:
    """Scale a RayCluster."""
    try:
        client = _get_client(ctx)
        ns = namespace or ctx.obj.get("namespace")
        kwargs: dict[str, Any] = {}
        if ns:
            kwargs["namespace"] = ns
        handle = client.get_cluster(name, **kwargs)
        handle.scale(workers)
        click.echo(f"Cluster '{name}' scaled to {workers} workers.")
    except KubeRayError as err:
        _handle_error(err)
