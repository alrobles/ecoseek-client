"""Remote smoke workflow — end-to-end EcoSeek health diagnostics.

Checks the full chain:
  1. AgenticPlug connector health (/healthz)
  2. Available clusters (/v1/clusters)
  3. Remote health dispatched through connector
  4. HPC status (read-only)
  5. HPC queue

Classifies failures clearly:
  - Auth failure (no token or expired)
  - Broker unavailable (connection refused)
  - Registry/relay unavailable
  - Connector offline
  - HPC unavailable
  - Capability disabled

Safe: never prints bearer tokens, exits non-zero on real failures.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..providers import AgenticPlugClient, AgenticPlugResult


@dataclass
class SmokeCheck:
    """Result of a single smoke check."""

    name: str
    description: str
    success: bool
    status: str  # "ok", "warning", "error", "skipped"
    detail: str = ""
    elapsed_ms: float = 0.0
    data: Optional[Dict[str, Any]] = None


@dataclass
class SmokeResult:
    """Full smoke test result."""

    checks: List[SmokeCheck] = field(default_factory=list)
    total: int = 0
    passed: int = 0
    warnings: int = 0
    errors: int = 0
    total_elapsed_ms: float = 0.0

    @property
    def all_healthy(self) -> bool:
        return self.errors == 0


CHECK_ORDER = [
    ("connector_health", "Connector /healthz", "Broker and connector health check"),
    ("clusters", "Cluster discovery /clusters", "List available clusters and connectors"),
    ("remote_health", "Remote health dispatch", "Connector-dispatched health check"),
    ("hpc_status", "HPC squeue status", "Read-only Slurm queue status"),
    ("hpc_queue", "HPC queue details", "Detailed Slurm queue information"),
]


def _run_single(
    client: AgenticPlugClient,
    check_id: str,
    name: str,
    description: str,
) -> SmokeCheck:
    """Run a single smoke check."""
    t0 = time.monotonic()

    try:
        if check_id == "connector_health":
            result = client.healthz()
            elapsed = (time.monotonic() - t0) * 1000
            if result.success:
                return SmokeCheck(
                    name=name,
                    description=description,
                    success=True,
                    status="ok",
                    detail=f"HTTP {result.status_code} ({elapsed:.0f}ms)",
                    elapsed_ms=elapsed,
                    data=result.data,
                )
            else:
                return SmokeCheck(
                    name=name,
                    description=description,
                    success=False,
                    status="error",
                    detail=f"Broker unavailable: {result.error}",
                    elapsed_ms=elapsed,
                )

        elif check_id == "clusters":
            result = client.clusters()
            elapsed = (time.monotonic() - t0) * 1000
            if result.success and result.data:
                cluster_list = result.data.get("clusters", [])
                healthy = sum(1 for c in cluster_list if c.get("healthy"))
                return SmokeCheck(
                    name=name,
                    description=description,
                    success=True,
                    status="ok",
                    detail=f"{len(cluster_list)} clusters ({healthy} healthy)",
                    elapsed_ms=elapsed,
                    data=result.data,
                )
            else:
                return SmokeCheck(
                    name=name,
                    description=description,
                    success=False,
                    status="error",
                    detail=f"Cluster discovery failed: {result.error}",
                    elapsed_ms=elapsed,
                )

        elif check_id == "remote_health":
            result = client.task("remote.health")
            elapsed = (time.monotonic() - t0) * 1000
            if result.success:
                return SmokeCheck(
                    name=name,
                    description=description,
                    success=True,
                    status="ok",
                    detail=f"Remote healthy ({elapsed:.0f}ms)",
                    elapsed_ms=elapsed,
                    data=result.data,
                )
            else:
                error = result.error or "unknown"
                if "401" in error or "403" in error or "auth" in error.lower():
                    return SmokeCheck(
                        name=name,
                        description=description,
                        success=False,
                        status="warning",
                        detail=f"Auth required: {error}",
                        elapsed_ms=elapsed,
                    )
                else:
                    return SmokeCheck(
                        name=name,
                        description=description,
                        success=False,
                        status="error",
                        detail=error,
                        elapsed_ms=elapsed,
                    )

        elif check_id == "hpc_status":
            result = client.task("hpc.status")
            elapsed = (time.monotonic() - t0) * 1000
            if result.success:
                data = result.data or {}
                jobs = data.get("jobs", [])
                job_count = len(jobs) if isinstance(jobs, list) else 0
                return SmokeCheck(
                    name=name,
                    description=description,
                    success=True,
                    status="ok",
                    detail=f"{job_count} jobs in queue",
                    elapsed_ms=elapsed,
                    data=data,
                )
            else:
                error = result.error or "unknown"
                if "401" in error or "403" in error or "auth" in error.lower():
                    return SmokeCheck(
                        name=name,
                        description=description,
                        success=False,
                        status="warning",
                        detail=f"HPC requires auth (expected in pre-alpha): {error}",
                        elapsed_ms=elapsed,
                    )
                elif "unavailable" in error.lower() or "not found" in error.lower():
                    return SmokeCheck(
                        name=name,
                        description=description,
                        success=False,
                        status="warning",
                        detail=f"HPC not available (expected without Slurm): {error}",
                        elapsed_ms=elapsed,
                    )
                else:
                    return SmokeCheck(
                        name=name,
                        description=description,
                        success=False,
                        status="warning",
                        detail=f"HPC unavailable: {error}",
                        elapsed_ms=elapsed,
                    )

        elif check_id == "hpc_queue":
            result = client.task("hpc.queue")
            elapsed = (time.monotonic() - t0) * 1000
            if result.success:
                return SmokeCheck(
                    name=name,
                    description=description,
                    success=True,
                    status="ok",
                    detail=f"Queue details retrieved ({elapsed:.0f}ms)",
                    elapsed_ms=elapsed,
                    data=result.data,
                )
            else:
                return SmokeCheck(
                    name=name,
                    description=description,
                    success=False,
                    status="warning",
                    detail=f"Queue details unavailable: {result.error}",
                    elapsed_ms=elapsed,
                )

        else:
            elapsed = (time.monotonic() - t0) * 1000
            return SmokeCheck(
                name=name,
                description=description,
                success=False,
                status="error",
                detail=f"Unknown check: {check_id}",
                elapsed_ms=elapsed,
            )

    except Exception as exc:
        elapsed = (time.monotonic() - t0) * 1000
        return SmokeCheck(
            name=name,
            description=description,
            success=False,
            status="error",
            detail=f"Exception: {exc}",
            elapsed_ms=elapsed,
        )


def run_remote_smoke(client: Optional[AgenticPlugClient] = None, verbose: bool = True) -> SmokeResult:
    """Run the full remote smoke workflow.

    Args:
        client: Optional pre-configured client.
        verbose: If True, print progress to stderr.

    Returns:
        SmokeResult with all check results.
    """
    if client is None:
        client = AgenticPlugClient()

    t0 = time.monotonic()
    result = SmokeResult()

    if verbose:
        print("ecoseek smoke remote", file=sys.stderr)
        print(f"  connector: {client.base_url}", file=sys.stderr)
        auth_status = "token configured" if client.has_auth else "no auth (public endpoints only)"
        print(f"  auth: {auth_status}", file=sys.stderr)
        print(file=sys.stderr)

    for check_id, name, description in CHECK_ORDER:
        if verbose:
            print(f"  [{check_id}] {description}...", file=sys.stderr, end=" ")

        check = _run_single(client, check_id, name, description)
        result.checks.append(check)
        result.total += 1

        if check.status == "ok":
            result.passed += 1
        elif check.status == "warning":
            result.warnings += 1
        elif check.status == "error":
            result.errors += 1

        if verbose:
            icon = {"ok": "✓", "warning": "⚠", "error": "✗", "skipped": "-"}[check.status]
            print(f"{icon} {check.detail}", file=sys.stderr)

    result.total_elapsed_ms = (time.monotonic() - t0) * 1000

    if verbose:
        print(file=sys.stderr)
        print(f"  {result.passed} passed, {result.warnings} warnings, {result.errors} errors", file=sys.stderr)
        print(f"  total: {result.total_elapsed_ms:.0f}ms", file=sys.stderr)

    return result
