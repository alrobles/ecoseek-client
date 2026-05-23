"""ecoseek CLI — first-class local client for EcoSeek, AgenticPlug, and HPC."""

from __future__ import annotations

import json
import sys
from typing import Optional

import click

from . import __version__
from .providers import (
    AgenticPlugClient,
    HermesProvider,
    HermesOrchestrationResult,
    KNOWN_TASKS,
)


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


def _get_hermes() -> HermesProvider:
    return HermesProvider()


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

    click.secho("Hermes", fg="green", bold=True)
    try:
        hermes = _get_hermes()
        hermes_info = hermes.whoami()
        if hermes_info.get("healthy"):
            click.echo(f"  provider: hermes (connected)")
        else:
            click.secho(f"  provider: hermes (unreachable)", fg="yellow")
    except Exception as e:
        click.secho(f"  provider: hermes (error — {e})", fg="yellow")

    click.secho("HPC", fg="green", bold=True)
    if client.has_auth:
        hpc_result = client.task("hpc.status")
        if hpc_result.success:
            jobs = hpc_result.data.get("jobs", [])
            click.echo(f"  squeue: {len(jobs) if isinstance(jobs, list) else '?'} jobs")
        else:
            click.secho(f"  squeue: skipped ({hpc_result.error})", fg="yellow")
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
    """Show connected user and connector identity."""
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
    """Full status: health, capabilities, and HPC queue."""
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


# ── hermes group ──────────────────────────────────────────────────────

@main.group()
def hermes():
    """Hermes scientific agent provider (via AgenticPlug)."""
    pass


@hermes.command()
def whoami():
    """Check Hermes identity and connectivity."""
    provider = _get_hermes()
    info = provider.whoami()

    click.secho("Hermes Provider", fg="cyan", bold=True)
    click.echo(f"  connector: {info['connector']}")

    if info["healthy"]:
        click.secho(f"  status: connected ({info['elapsed_ms']:.0f}ms)", fg="green")
    else:
        click.secho(f"  status: unreachable ({info['elapsed_ms']:.0f}ms)", fg="red")

    detail = info.get("detail", {})
    if detail:
        click.echo()
        click.echo(json.dumps(detail, indent=2, default=str))


@hermes.command()
@click.argument("task_text", required=False)
@click.option("--mode", default="ecoSeek", help="Task mode: ecoSeek (orchestrated) or diy (direct)")
@click.option("--species", "-s", help="Target species")
@click.option("--region", "-r", help="Geographic region")
@click.option("--method", "-m", help="Analysis method")
def orchestrate(task_text: Optional[str], mode: str, species: Optional[str], region: Optional[str], method: Optional[str]):
    """Send a task to Hermes for orchestration.

    \b
    Examples:
      ecoseek hermes orchestrate "Run SDM for monarch butterfly in Mexico"
      ecoseek hermes orchestrate --species "Panthera onca" --region Yucatan --method MaxEnt
    """
    provider = _get_hermes()

    if task_text:
        task = task_text
    else:
        if not species:
            click.secho("Provide a task or --species.", fg="red", err=True)
            sys.exit(1)
        task = None  # will use science_task()

    click.secho("Hermes Orchestration", fg="cyan", bold=True)

    if task:
        click.echo(f"  task: {task}")
        click.echo(f"  mode: {mode}")
        click.echo()
        result = provider.orchestrate(task, mode=mode)
    elif species:
        click.echo(f"  species: {species}  region: {region}  method: {method}")
        click.echo()
        result = provider.science_task(
            goal="SDM" if not method else method,
            species=species,
            region=region,
            method=method,
        )
    else:
        click.secho("Provide a task or --species.", fg="red", err=True)
        sys.exit(1)

    if result.status == "completed":
        click.secho(f"Completed ({result.elapsed_ms:.0f}ms)", fg="green", bold=True)
        click.echo(f"  task_id: {result.task_id}")
        if result.plan:
            click.secho("  Plan:", fg="yellow")
            click.echo(f"    {json.dumps(result.plan, indent=4, default=str)}")
        if result.workers:
            click.secho(f"  Workers: {len(result.workers)} deployed", fg="yellow")
            for w in result.workers:
                status_icon = "✓" if w.get("status") == "success" else "✗"
                click.echo(f"    {status_icon} {w.get('name', '?')}: {w.get('status', '?')}")
        if result.report:
            click.secho("  Report:", fg="yellow")
            click.echo(f"    {result.report}")
    elif result.status == "failed":
        click.secho(f"Failed: {result.error}", fg="red", bold=True)
        sys.exit(1)
    elif result.status == "timeout":
        click.secho(f"Timeout after {provider.timeout}s: {result.task_id}", fg="red", bold=True)
        sys.exit(1)
    else:
        click.secho(f"Status: {result.status} (task_id: {result.task_id})", fg="yellow")


@hermes.command()
@click.argument("message")
def chat(message: str):
    """Send a message to Hermes chat.

    Example:
      ecoseek hermes chat "What ecological tools are available?"
    """
    provider = _get_hermes()
    response = provider.chat([
        {"role": "user", "content": message}
    ])

    click.secho("Hermes:", fg="cyan", bold=True)
    click.echo(response.message.content)
    if response.tool_calls:
        click.echo()
        click.secho("Tool calls:", fg="yellow")
        for tc in response.tool_calls:
            click.echo(f"  {tc.name}({json.dumps(tc.arguments)})")


# ── smoke group ───────────────────────────────────────────────────────

@main.group()
def smoke():
    """Diagnostic smoke tests."""
    pass


@smoke.command()
def remote():
    """Run full remote smoke workflow.

    Checks connector health, clusters, remote dispatch, and HPC.
    Classifies failures clearly: auth, broker, connector, HPC, capability.
    Never prints bearer tokens.
    """
    from .workflows import run_remote_smoke

    client = _get_client()
    result = run_remote_smoke(client, verbose=True)

    if not result.all_healthy:
        click.echo()
        click.secho(
            f"Remote smoke: {result.errors} error(s), {result.warnings} warning(s).",
            fg="red",
            bold=True,
        )
        sys.exit(1)
    else:
        click.echo()
        click.secho("Remote smoke: all clear.", fg="green", bold=True)


# ── aar group ─────────────────────────────────────────────────────────

@main.group()
def aar():
    """AAR (After Action Review) ReAct loop."""
    pass


@aar.command()
@click.argument("goal")
@click.option("--cycles", "-c", type=int, default=3, help="Max cycles (default: 3, max: 5)")
def run(goal: str, cycles: int):
    """Run the AAR loop for a goal.

    observe → reason → act → evaluate → update

    \b
    Example:
      ecoseek aar run "Check HPC cluster status and connector health"
    """
    from .aar import AARLoop

    provider = _get_hermes()
    loop = AARLoop(provider)
    loop.max_cycles = min(cycles, 5)

    click.secho(f"AAR: {goal}", fg="cyan", bold=True)
    click.echo(f"  max cycles: {loop.max_cycles}")
    click.echo()

    result = loop.run(goal)

    for cycle in result.cycles:
        icon = "✓" if cycle.result.success else "✗"
        click.secho(f"[{cycle.cycle_id}] {icon} {cycle.action.tool}", fg="green" if cycle.result.success else "red")
        click.echo(f"     reason: {cycle.reasoning[:120]}...")
        click.echo(f"     result: {cycle.result.data}")
        click.echo()

    if result.success:
        click.secho(f"AAR complete: {result.summary[:200]}", fg="green", bold=True)
    else:
        click.secho(f"AAR incomplete after {len(result.cycles)} cycles", fg="yellow", bold=True)

    click.echo(f"  total: {result.total_elapsed_ms:.0f}ms")


@aar.command()
def status():
    """Show AAR loop capabilities."""
    click.secho("AAR Loop (Observe → Reason → Act → Evaluate → Update)", fg="cyan", bold=True)
    click.echo()
    click.echo("  Powered by: Hermes (reasoning) + AgenticPlug (actions)")
    click.echo("  Max cycles: 5 (configurable)")
    click.echo()
    click.echo("  Available actions:")
    click.echo("    agenticplug.task  — Run named connector tasks")
    click.echo("    hermes.orchestrate — Full agent orchestration")
    click.echo("    hermes.chat       — Direct chat completion")
    click.echo()
    click.echo("  Observation sources:")
    click.echo("    agenticplug       — Connector health, clusters, HPC")
    click.echo("    hpc               — Slurm queue and job status")
    click.echo("    filesystem        — Local file operations")


# ── skill group ───────────────────────────────────────────────────────

@main.group()
def skill():
    """Scientific skills for ecology workflows."""
    pass


@skill.command(name="list")
def skill_list():
    """List available scientific skills."""
    from .skills import SkillLoader

    loader = SkillLoader()
    skills = loader.list_all()

    if not skills:
        click.secho("No skills loaded.", fg="yellow")
        return

    categories: dict = {}
    for s in skills:
        categories.setdefault(s.category, []).append(s)

    for cat, cat_skills in sorted(categories.items()):
        click.secho(f"{cat}", fg="cyan", bold=True)
        for s in cat_skills:
            click.echo(f"  {s.name:25s} {s.description}")
        click.echo()

    click.echo(f"  Total: {len(skills)} skills in {len(categories)} categories")


@skill.command(name="show")
@click.argument("name")
def skill_show(name: str):
    """Show a skill's full content."""
    from .skills import SkillLoader

    loader = SkillLoader()
    skill = loader.get(name)

    if not skill:
        click.secho(f"Skill not found: {name}", fg="red", err=True)
        available = [s.name for s in loader.list_all()]
        if available:
            click.echo(f"Available: {', '.join(available)}")
        sys.exit(1)

    click.secho(f"Skill: {skill.name}", fg="cyan", bold=True)
    click.echo(f"  category: {skill.category}")
    if skill.triggers:
        click.echo(f"  triggers: {', '.join(skill.triggers)}")
    click.echo()
    click.echo(skill.body)


if __name__ == "__main__":
    main()
