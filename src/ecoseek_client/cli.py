"""ecoseek CLI — first-class local client for EcoSeek, AgenticPlug, and HPC."""

from __future__ import annotations

import json
import sys
from typing import Optional

import click

from . import __version__
from .providers import AgenticPlugClient, KNOWN_TASKS


def _sanitize(data: dict) -> dict:
    """Remove sensitive fields from output."""
    safe = dict(data)
    for key in ("token", "access_token", "bearer"):
        safe.pop(key, None)
    return {k: _sanitize(v) if isinstance(v, dict) else v for k, v in safe.items()}


def _print_result(result, token_safe: bool = True):
    if not result.success:
        click.secho(f"Error: {result.error}", fg="red", err=True)
        return
    data = result.data
    if token_safe and isinstance(data, dict):
        data = _sanitize(data)
    click.echo(json.dumps(data, indent=2, default=str))


def _get_client() -> AgenticPlugClient:
    return AgenticPlugClient()


# ── Root CLI ──────────────────────────────────────────────────────────

@click.group()
@click.version_option(version=__version__, prog_name="ecoseek")
@click.pass_context
def main(ctx: click.Context):
    """ecoseek — EcoSeek local client for AgenticPlug and HPC workflows."""
    ctx.ensure_object(dict)


# ── doctor ────────────────────────────────────────────────────────────

@main.command()
def doctor():
    """Run environment diagnostics."""
    import platform
    import shutil
    from pathlib import Path

    click.secho("ecoseek doctor", fg="cyan", bold=True)
    click.echo(f"  version: {__version__}")
    click.echo()

    click.secho("Python", fg="green", bold=True)
    click.echo(f"  {platform.python_version()} ({platform.python_implementation()})")
    click.echo(f"  executable: {sys.executable}")
    click.echo()

    click.secho("Platform", fg="green", bold=True)
    click.echo(f"  {platform.system()} {platform.release()}")
    try:
        with open("/proc/version") as f:
            ver = f.read()
        if "microsoft" in ver.lower() or "wsl" in ver.lower():
            click.echo("  WSL2: yes")
    except Exception:
        pass
    click.echo()

    click.secho("Git", fg="green", bold=True)
    git_path = shutil.which("git")
    click.echo(f"  git: {git_path or 'NOT FOUND'}")

    click.secho("AgenticPlug", fg="green", bold=True)
    client = _get_client()
    h_result = client.health()
    if h_result.success:
        click.echo(f"  connector: {client.base_url} (healthy, {h_result.elapsed_ms:.0f}ms)")
    else:
        click.secho(f"  connector: {client.base_url} (down)", fg="yellow")

    auth_status = "configured" if client.has_auth else "not set"
    click.echo(f"  auth: {auth_status}")

    session_path = Path.home() / ".config" / "agenticplug" / "session.json"
    if session_path.exists():
        click.echo(f"  session file: {session_path} (found)")
    else:
        click.echo(f"  session file: {session_path} (not found)")

    click.secho("HPC", fg="green", bold=True)
    if client.has_auth:
        hpc_result = client.task("hpc.status")
        if hpc_result.success:
            jobs = hpc_result.data.get("jobs", [])
            click.echo(f"  squeue: {len(jobs) if isinstance(jobs, list) else '?'} jobs")
        else:
            click.secho(f"  squeue: failed — {hpc_result.error}", fg="yellow")
    else:
        click.secho("  squeue: skipped (no auth)", fg="yellow")

    click.echo()
    click.secho("Done.", fg="green")


# ── agenticplug group ─────────────────────────────────────────────────

@main.group()
def agenticplug():
    """AgenticPlug broker/connector commands."""
    pass


@agenticplug.command()
def whoami():
    """Show connected user and connector identity.

    Reads session from AGENTICPLUG_SESSION env var or
    ~/.config/agenticplug/session.json. Never prints tokens.
    """
    client = _get_client()

    if not client.has_auth:
        click.secho("No session token found.", fg="yellow")
        click.echo("Set AGENTICPLUG_SESSION or run: agenticplug login")
        click.echo()

    result = client.whoami()
    if result.success:
        identity = result.data.get("user") or result.data.get("connector_id", "unknown")
        click.secho(f"Connected as: {identity}", fg="green")
        click.echo()
        click.echo(json.dumps(_sanitize(result.data), indent=2, default=str))
    else:
        click.secho(f"Error: {result.error}", fg="red", err=True)


@agenticplug.command()
def health():
    """Check connector health."""
    client = _get_client()
    result = client.health()
    if result.success:
        click.secho("Connector: healthy", fg="green")
    else:
        click.secho(f"Connector: down — {result.error}", fg="red")
    _print_result(result)


@agenticplug.command()
def status():
    """Full status: health, capabilities, and HPC queue (if auth)."""
    client = _get_client()
    result = client.status()

    if not result.success:
        click.secho("Some checks failed:", fg="yellow", err=True)

    data = _sanitize(result.data)

    connector = data.get("connector", {})
    health_status = "healthy" if connector.get("healthy") else "down"
    color = "green" if connector.get("healthy") else "red"
    click.secho(f"Connector ({connector.get('url', '?')}): {health_status}", fg=color)

    auth = data.get("auth", "none")
    auth_color = "green" if auth == "token_configured" else "yellow"
    click.secho(f"Auth: {auth}", fg=auth_color)

    hpc = data.get("hpc", {})
    if hpc:
        jobs = hpc.get("jobs", [])
        click.secho(f"HPC jobs: {len(jobs) if isinstance(jobs, list) else '?'}")

    click.echo()
    _print_result(result)


@agenticplug.command()
def clusters():
    """List available clusters and connectors."""
    client = _get_client()
    result = client.clusters()
    if not result.success:
        click.secho(f"Error: {result.error}", fg="red", err=True)
        return

    cluster_list = result.data.get("clusters", [])
    if not cluster_list:
        click.secho("No clusters found.", fg="yellow")
        return

    click.secho(f"Clusters ({len(cluster_list)}):", fg="green")
    for c in cluster_list:
        icon = "✓" if c.get("healthy") else "✗"
        ctype = c.get("type", "?")
        cid = c.get("id", "?")
        extra = ""
        if ctype == "hpc":
            submit = "rw" if c.get("submit_enabled") else "ro"
            extra = f" [{submit}]"
        click.echo(f"  {icon} {cid} ({ctype}){extra}")

    click.echo()
    _print_result(result)


@agenticplug.group()
def task():
    """Run named tasks through the connector."""
    pass


@task.command(name="list")
def task_list():
    """List available tasks."""
    click.secho("Available tasks:", fg="green")
    for name, info in sorted(KNOWN_TASKS.items()):
        click.echo(f"  {name:20s}  {info['method']:4s} {info['endpoint']:20s}  {info['description']}")


@task.command(name="run")
@click.argument("task_name")
def task_run(task_name: str):
    """Run a named task (e.g. remote.health, hpc.status)."""
    client = _get_client()

    if task_name not in KNOWN_TASKS:
        click.secho(f"Unknown task: {task_name}", fg="red", err=True)
        click.echo(f"Available: {', '.join(sorted(KNOWN_TASKS))}")
        sys.exit(1)

    task_def = KNOWN_TASKS[task_name]
    click.secho(f"Running: {task_name} — {task_def['description']}", fg="cyan")
    click.echo(f"  {task_def['method']} {task_def['endpoint']}")

    if "/hpc/" in task_def["endpoint"] and not client.has_auth:
        click.secho("Auth required for this task. Set AGENTICPLUG_SESSION.", fg="red", err=True)
        sys.exit(1)

    result = client.task(task_name)
    if result.success:
        click.secho(f"  OK ({result.elapsed_ms:.0f}ms)", fg="green")
    else:
        click.secho(f"  FAILED: {result.error}", fg="red")

    click.echo()
    _print_result(result)


if __name__ == "__main__":
    main()
