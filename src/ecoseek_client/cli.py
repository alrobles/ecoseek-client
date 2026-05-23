"""CLI entry point for ecoseek-client.

Commands:

    ecoseek doctor                 Environment diagnostics
    ecoseek agenticplug whoami     Show session identity
    ecoseek agenticplug clusters   List registered connectors
    ecoseek agenticplug task NAME  Dispatch a task to the gateway
    ecoseek smoke remote           Full remote smoke test
"""

from __future__ import annotations

import sys
from typing import Optional

import click

from ecoseek_client import __version__


# ---------------------------------------------------------------------------
# Helper — safe token masking
# ---------------------------------------------------------------------------

def _safe_str(value: Optional[str], show_chars: int = 8) -> str:
    """Return a token-safe representation: first N chars + '...'"""
    if not value:
        return "(not set)"
    if len(value) <= show_chars:
        return value
    return value[:show_chars] + "..."


# ---------------------------------------------------------------------------
# Main group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(version=__version__, prog_name="ecoseek")
def main():
    """EcoSeek first-class local client — CLI, providers, and HPC workflows."""


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


@main.command()
def doctor():
    """Run environment diagnostics."""
    from ecoseek_client.doctor import run_doctor

    sys.exit(run_doctor())


# ---------------------------------------------------------------------------
# agenticplug group
# ---------------------------------------------------------------------------


@main.group()
def agenticplug():
    """AgenticPlug broker/connector commands."""


@agenticplug.command()
def whoami():
    """Show current AgenticPlug session identity."""
    from ecoseek_client.providers.agenticplug import AgenticPlugClient

    client = AgenticPlugClient()
    info = client.whoami()

    if not info.login:
        click.secho("Not authenticated.", fg="yellow")
        click.echo("Run `agenticplug login` (GitHub Device Flow) to authenticate.")
        click.echo("See docs/agenticplug.md for setup instructions.")
        sys.exit(1)

    click.secho(f"Login: {info.login}", fg="green")
    if info.name:
        click.echo(f"Name:  {info.name}")
    if info.scopes:
        click.echo(f"Scopes: {', '.join(info.scopes)}")
    if info.default_cluster:
        click.echo(f"Default cluster: {info.default_cluster}")
    if info.session_expired:
        click.secho("WARNING: Session is expired.", fg="red")
        click.echo("Run `agenticplug login` to refresh.")


@agenticplug.command()
def clusters():
    """List registered connectors on the gateway."""
    from ecoseek_client.providers.agenticplug import AgenticPlugClient, AgenticPlugError

    client = AgenticPlugClient()
    try:
        connectors = client.list_connectors()
    except AgenticPlugError as exc:
        click.secho(f"Error: {exc}", fg="red")
        sys.exit(1)

    if not connectors:
        click.secho("No connectors discovered.", fg="yellow")
        return

    click.secho(f"Discovered {len(connectors)} connector(s):", fg="green")
    for c in connectors:
        icon = {"online": "[OK]", "degraded": "[!!]", "stale": "[--]"}.get(c.health, "[??]")
        color = "green" if c.is_online else "yellow"
        tools = ", ".join(t.get("name", "?") for t in c.tools[:5]) or "(none)"
        click.secho(
            f"  {icon} {c.connector_id} ({c.connector_type}) "
            f"v{c.version} — tools: {tools}",
            fg=color,
        )


@agenticplug.command()
@click.argument("task_name")
@click.option("--connector", "-c", help="Target connector ID (default: auto-resolve)")
def task(task_name: str, connector: Optional[str] = None):
    """Dispatch a task to the AgenticPlug gateway.

    TASK_NAME can be a simple name (e.g., 'remote.health', 'hpc.status')
    or a free-form task description.
    """
    from ecoseek_client.providers.agenticplug import (
        AgenticPlugAuthError,
        AgenticPlugClient,
        AgenticPlugError,
        resolve_connector,
    )

    client = AgenticPlugClient()
    target = connector or resolve_connector(client)

    click.echo(f"Dispatching '{task_name}' -> {target}...")

    try:
        result = client.send_task(task_name, connector_id=target)
    except AgenticPlugAuthError as exc:
        click.secho(f"Auth error: {exc}", fg="red")
        sys.exit(1)
    except AgenticPlugError as exc:
        click.secho(f"Error: {exc}", fg="red")
        sys.exit(1)

    if result.status in ("accepted", "running", "completed"):
        click.secho(f"Status: {result.status}", fg="green")
        if result.task_id:
            click.echo(f"Task ID: {result.task_id}")
        if result.output:
            click.echo(f"Output: {result.output}")
    else:
        click.secho(f"Status: {result.status}", fg="red")
        if result.error:
            click.secho(f"Error: {result.error}", fg="red")
        sys.exit(1)


# ---------------------------------------------------------------------------
# smoke group
# ---------------------------------------------------------------------------


@main.group()
def smoke():
    """Smoke tests for remote connectivity."""


@smoke.command()
@click.option("--connector", "-c", help="Target connector ID")
def remote(connector: Optional[str] = None):
    """Full remote smoke test: health, clusters, remote.health, hpc.status."""
    from ecoseek_client.providers.agenticplug import (
        AgenticPlugAuthError,
        AgenticPlugClient,
        AgenticPlugError,
        resolve_connector,
    )

    client = AgenticPlugClient()
    failures = 0

    def step(name: str, fn, *args) -> bool:
        nonlocal failures
        try:
            result = fn(*args)
            click.secho(f"  [OK] {name}", fg="green")
            return True
        except Exception as exc:
            click.secho(f"  [FAIL] {name}: {exc}", fg="red")
            failures += 1
            return False

    click.echo("ecoseek smoke remote")
    click.echo("=" * 50)

    # 1. Gateway health
    step("Gateway health", lambda: _check_health(client))

    # 2. List connectors
    connectors = client.list_connectors() if step("List connectors", client.list_connectors) else []

    # 3. Resolve target
    target = connector or resolve_connector(client)
    click.echo(f"  Target connector: {target}")

    # 4. Connector health
    if target:
        step(f"Connector {target} health", client.get_connector, target)

    # 5. Task dispatch
    try:
        result = client.send_task("remote.health", connector_id=target)
        if result.status in ("accepted", "running", "completed"):
            click.secho(f"  [OK] Task remote.health: {result.status}", fg="green")
            if result.task_id:
                click.echo(f"         Task ID: {result.task_id}")
        else:
            click.secho(f"  [FAIL] Task remote.health: {result.error}", fg="red")
            failures += 1
    except AgenticPlugAuthError:
        click.secho("  [SKIP] Task dispatch (not authenticated)", fg="yellow")

    # 6. HPC status (best-effort)
    try:
        result = client.send_task("hpc.status", connector_id=target)
        if result.status in ("accepted", "running", "completed"):
            click.secho(f"  [OK] Task hpc.status: {result.status}", fg="green")
        else:
            click.secho(f"  [WARN] Task hpc.status: {result.error}", fg="yellow")
    except AgenticPlugAuthError:
        click.secho("  [SKIP] Task hpc.status (not authenticated)", fg="yellow")

    click.echo("=" * 50)
    if failures == 0:
        click.secho("All checks passed.", fg="green")
    else:
        click.secho(f"{failures} check(s) failed.", fg="red")
        sys.exit(1)


def _check_health(client) -> None:
    """Raise if health check fails."""
    h = client.health()
    if h.get("status") != "ok":
        raise RuntimeError(h.get("error", "unhealthy"))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    main()
