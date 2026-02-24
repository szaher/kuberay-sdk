"""Job CLI subcommands (T043).

Implements ``kuberay job create|list|get|delete``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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
def job() -> None:
    """Manage RayJobs."""


@job.command()
@click.argument("name")
@click.option("--entrypoint", "-e", required=True, help="Job entrypoint command.")
@click.option("--cluster", default=None, help="Existing cluster to submit to.")
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace (overrides global).")
@click.pass_context
def create(ctx: click.Context, name: str, entrypoint: str, cluster: str | None, namespace: str | None) -> None:
    """Create a RayJob."""
    try:
        client = _get_client(ctx)
        ns = namespace or ctx.obj.get("namespace")
        kwargs: dict[str, Any] = {"entrypoint": entrypoint}
        if ns:
            kwargs["namespace"] = ns
        client.create_job(name, **kwargs)
        click.echo(f"Job '{name}' created.")
    except KubeRayError as err:
        _handle_error(err)


@job.command("list")
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace (overrides global).")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default=None, help="Output format.")
@click.pass_context
def list_jobs(ctx: click.Context, namespace: str | None, output: str | None) -> None:
    """List RayJobs."""
    try:
        client = _get_client(ctx)
        ns = namespace or ctx.obj.get("namespace")
        kwargs: dict[str, Any] = {}
        if ns:
            kwargs["namespace"] = ns
        jobs = client.list_jobs(**kwargs)
        fmt = output or ctx.obj.get("output", "table")
        if fmt == "json":
            data = [
                {
                    "name": j.name,
                    "state": str(j.state),
                    "entrypoint": j.entrypoint,
                    "age": str(datetime.now(timezone.utc) - j.submitted_at),
                }
                for j in jobs
            ]
            click.echo(format_json(data))
        else:
            headers = ["NAME", "STATE", "ENTRYPOINT", "AGE"]
            rows = [
                [j.name, str(j.state), j.entrypoint, _format_age(datetime.now(timezone.utc) - j.submitted_at)]
                for j in jobs
            ]
            click.echo(format_table(headers, rows))
    except KubeRayError as err:
        _handle_error(err)


@job.command()
@click.argument("name")
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace (overrides global).")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default=None, help="Output format.")
@click.pass_context
def get(ctx: click.Context, name: str, namespace: str | None, output: str | None) -> None:
    """Get a RayJob status."""
    try:
        client = _get_client(ctx)
        ns = namespace or ctx.obj.get("namespace")
        kwargs: dict[str, Any] = {}
        if ns:
            kwargs["namespace"] = ns
        handle = client.get_job(name, **kwargs)
        status = handle.status()
        fmt = output or ctx.obj.get("output", "table")
        age = datetime.now(timezone.utc) - status.submitted_at
        if fmt == "json":
            data = {
                "name": status.name,
                "state": str(status.state),
                "entrypoint": status.entrypoint,
                "age": str(age),
            }
            click.echo(format_json(data))
        else:
            headers = ["NAME", "STATE", "ENTRYPOINT", "AGE"]
            rows = [[status.name, str(status.state), status.entrypoint, _format_age(age)]]
            click.echo(format_table(headers, rows))
    except KubeRayError as err:
        _handle_error(err)


@job.command()
@click.argument("name")
@click.option("--namespace", "-n", default=None, help="Kubernetes namespace (overrides global).")
@click.pass_context
def delete(ctx: click.Context, name: str, namespace: str | None) -> None:
    """Delete a RayJob."""
    try:
        from kuberay_sdk.services.job_service import JobService

        client = _get_client(ctx)
        ns = namespace or ctx.obj.get("namespace")
        svc = JobService(client._custom_api, client._config)
        effective_ns = ns or "default"
        svc.stop(name, effective_ns)
        click.echo(f"Job '{name}' deleted.")
    except KubeRayError as err:
        _handle_error(err)
