"""Service CLI subcommands (T044).

Implements ``kuberay service create|list|get|delete``.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import click

from kuberay_sdk.cli.formatters import format_json, format_table
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
def service() -> None:
    """Manage RayServices."""


@service.command()
@click.argument("name")
@click.option("--import-path", required=True, help="Python import path for the Serve deployment.")
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace (overrides global).")
@click.pass_context
def create(ctx: click.Context, name: str, import_path: str, namespace: str | None) -> None:
    """Create a RayService."""
    try:
        client = _get_client(ctx)
        ns = namespace or ctx.obj.get("namespace")
        kwargs: dict[str, Any] = {"import_path": import_path}
        if ns:
            kwargs["namespace"] = ns
        client.create_service(name, **kwargs)
        click.echo(f"Service '{name}' created.")
    except KubeRayError as err:
        _handle_error(err)


@service.command("list")
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace (overrides global).")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default=None, help="Output format.")
@click.pass_context
def list_services(ctx: click.Context, namespace: str | None, output: str | None) -> None:
    """List RayServices."""
    try:
        client = _get_client(ctx)
        ns = namespace or ctx.obj.get("namespace")
        kwargs: dict[str, Any] = {}
        if ns:
            kwargs["namespace"] = ns
        services = client.list_services(**kwargs)
        fmt = output or ctx.obj.get("output", "table")
        if fmt == "json":
            data = [
                {
                    "name": s.name,
                    "state": s.state,
                    "replicas": s.replicas_ready,
                    "age": str(s.age),
                }
                for s in services
            ]
            click.echo(format_json(data))
        else:
            headers = ["NAME", "STATE", "REPLICAS", "AGE"]
            rows = [[s.name, s.state, str(s.replicas_ready), _format_age(s.age)] for s in services]
            click.echo(format_table(headers, rows))
    except KubeRayError as err:
        _handle_error(err)


@service.command()
@click.argument("name")
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace (overrides global).")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default=None, help="Output format.")
@click.pass_context
def get(ctx: click.Context, name: str, namespace: str | None, output: str | None) -> None:
    """Get a RayService status."""
    try:
        client = _get_client(ctx)
        ns = namespace or ctx.obj.get("namespace")
        kwargs: dict[str, Any] = {}
        if ns:
            kwargs["namespace"] = ns
        handle = client.get_service(name, **kwargs)
        status = handle.status()
        fmt = output or ctx.obj.get("output", "table")
        if fmt == "json":
            data = {
                "name": status.name,
                "state": status.state,
                "replicas": status.replicas_ready,
                "age": str(status.age),
            }
            click.echo(format_json(data))
        else:
            headers = ["NAME", "STATE", "REPLICAS", "AGE"]
            rows = [[status.name, status.state, str(status.replicas_ready), _format_age(status.age)]]
            click.echo(format_table(headers, rows))
    except KubeRayError as err:
        _handle_error(err)


@service.command()
@click.argument("name")
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace (overrides global).")
@click.pass_context
def delete(ctx: click.Context, name: str, namespace: str | None) -> None:
    """Delete a RayService."""
    try:
        client = _get_client(ctx)
        ns = namespace or ctx.obj.get("namespace")
        kwargs: dict[str, Any] = {}
        if ns:
            kwargs["namespace"] = ns
        handle = client.get_service(name, **kwargs)
        handle.delete()
        click.echo(f"Service '{name}' deleted.")
    except KubeRayError as err:
        _handle_error(err)
