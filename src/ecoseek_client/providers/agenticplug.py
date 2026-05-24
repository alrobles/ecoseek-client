"""AgenticPlug provider — HTTP client for the AgenticPlug broker/connector.

Talks to the local connector (default: http://127.0.0.1:3101).

Endpoints consumed (matching connector/main.js):
- GET  /health           — liveness (no auth)
- GET  /healthz          — reumanlab connector detail (no auth)
- GET  /capabilities     — endpoint listing + hpc/hermes flags (no auth)
- POST /v1/tasks         — capability dispatch (auth required)
- GET  /hpc/squeue       — Slurm queue (auth required)

Token handling:
- AGENTICPLUG_SESSION or CONNECTOR_TOKEN from env.
- Falls back to ~/.config/agenticplug/session.json.
- NEVER prints tokens in output.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from ecoseek_client.config import (
    AGENTICPLUG_TIMEOUT,
    AGENTICPLUG_URL,
    AGENTICPLUG_VERIFY_SSL,
    ECOSEEK_REMOTE_CONNECTOR,
    agenticplug_token,
)
from ecoseek_client.session import AgenticPlugSession, load_session_or_none


# ── Exceptions ─────────────────────────────────────────────────────────


class AgenticPlugError(Exception):
    """Base error for AgenticPlug client operations."""


class AgenticPlugAuthError(AgenticPlugError):
    """Authentication or session error."""


# ── Data types ─────────────────────────────────────────────────────────


@dataclass
class AgenticPlugResult:
    """Result from an AgenticPlug API call (CLI-compatible)."""

    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    status_code: int = 0
    error: str = ""
    elapsed_ms: float = 0.0
    endpoint: str = ""


# ── Task registry ──────────────────────────────────────────────────────

KNOWN_TASKS: Dict[str, Dict[str, str]] = {
    "remote.health": {
        "endpoint": "/v1/tasks",
        "method": "POST",
        "capability": "remote.health",
        "description": "Reumanlab connector health check",
    },
    "hpc.status": {
        "endpoint": "/hpc/squeue",
        "method": "GET",
        "capability": "hpc.status",
        "description": "Slurm queue status (read-only)",
    },
    "hpc.queue": {
        "endpoint": "/hpc/squeue",
        "method": "GET",
        "capability": "hpc.queue",
        "description": "Slurm queue status (read-only)",
    },
    "hpc.submit": {
        "endpoint": "/hpc/submit",
        "method": "POST",
        "capability": "hpc.submit",
        "description": "Submit allowlisted template job",
    },
}


# ── Client ─────────────────────────────────────────────────────────────


class AgenticPlugClient:
    """Synchronous HTTP client for the AgenticPlug connector/broker."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: Optional[int] = None,
        verify_ssl: Optional[bool] = None,
    ):
        self.base_url = (base_url or AGENTICPLUG_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else AGENTICPLUG_TIMEOUT
        self.verify_ssl = verify_ssl if verify_ssl is not None else AGENTICPLUG_VERIFY_SSL
        self._token: Optional[str] = token
        self._session: Optional[AgenticPlugSession] = None

    @property
    def token(self) -> Optional[str]:
        """Resolve the bearer token, loading session file on first access."""
        if self._token:
            return self._token
        self._token = agenticplug_token()
        if self._token:
            return self._token
        sess = load_session_or_none()
        if sess and sess.token:
            self._session = sess
            self._token = sess.token
            return self._token
        return None

    @property
    def has_auth(self) -> bool:
        return self.token is not None

    @property
    def session(self) -> Optional[AgenticPlugSession]:
        if self._session is None:
            self._session = load_session_or_none()
        return self._session

    # ── HTTP helpers ──────────────────────────────────────────────────

    def _auth_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        token = self.token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        auth: bool = False,
        json_body: Optional[Dict] = None,
    ) -> AgenticPlugResult:
        url = f"{self.base_url}{path}"
        headers: Dict[str, str] = {"Accept": "application/json"}
        if auth:
            headers.update(self._auth_headers())
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        t0 = time.monotonic()
        try:
            with httpx.Client(timeout=self.timeout, verify=self.verify_ssl) as client:
                if method == "GET":
                    resp = client.get(url, headers=headers)
                elif method == "POST":
                    resp = client.post(url, headers=headers, json=json_body)
                else:
                    return AgenticPlugResult(
                        success=False, error=f"Unsupported method: {method}", endpoint=path
                    )

            elapsed = (time.monotonic() - t0) * 1000
            try:
                data = resp.json() if resp.content else {}
            except (json.JSONDecodeError, ValueError):
                data = {"raw": resp.text[:1000]}

            return AgenticPlugResult(
                success=resp.is_success,
                data=data if isinstance(data, dict) else {"value": data},
                status_code=resp.status_code,
                elapsed_ms=round(elapsed, 1),
                endpoint=path,
            )
        except httpx.ConnectError as exc:
            return AgenticPlugResult(
                success=False, error=f"Connection refused at {url}: {exc}", endpoint=path
            )
        except httpx.TimeoutException:
            return AgenticPlugResult(
                success=False,
                error=f"Request timed out after {self.timeout}s: {url}",
                endpoint=path,
            )
        except Exception as exc:
            return AgenticPlugResult(
                success=False, error=f"Request failed: {exc}", endpoint=path
            )

    # ── Public API ────────────────────────────────────────────────────

    def health(self) -> AgenticPlugResult:
        """GET /health — liveness check (no auth)."""
        return self._request("GET", "/health")

    def healthz(self) -> AgenticPlugResult:
        """GET /healthz — reumanlab connector detail (no auth)."""
        return self._request("GET", "/healthz")

    def capabilities(self) -> AgenticPlugResult:
        """GET /capabilities — full endpoint listing (no auth)."""
        return self._request("GET", "/capabilities")

    def me(self) -> AgenticPlugResult:
        """GET /v1/me — canonical authenticated identity (broker endpoint)."""
        return self._request("GET", "/v1/me", auth=True)

    def whoami(self) -> AgenticPlugResult:
        """Identify the current user/session."""
        hz_result = self.healthz()
        sess = self.session

        identity: Dict[str, Any] = {}
        if sess:
            identity["user"] = sess.login or sess.identity
            identity["name"] = sess.name
            identity["scopes"] = sess.scopes if isinstance(sess.scopes, list) else []
            identity["default_cluster"] = sess.default_cluster
            identity["session_expired"] = sess.session_expired

        if hz_result.success:
            identity["connector_id"] = hz_result.data.get("connector_id", "unknown")
            identity["connected"] = True
        else:
            identity["connector_id"] = "unknown"
            identity["connected"] = False

        return AgenticPlugResult(
            success=bool(sess or self.has_auth),
            data=identity,
            elapsed_ms=hz_result.elapsed_ms,
            endpoint="/healthz",
        )

    def clusters(self) -> AgenticPlugResult:
        """List available clusters/connectors."""
        hz_result = self.healthz()
        cap_result = self.capabilities()

        clusters: List[Dict[str, Any]] = []

        if hz_result.success:
            cid = hz_result.data.get("connector_id", "reumanlab")
            result_data = hz_result.data.get("result", {})
            version = "unknown"
            if isinstance(result_data, dict):
                version = str(result_data.get("version", "unknown"))
            clusters.append({
                "id": cid,
                "name": cid,
                "type": "connector",
                "healthy": hz_result.success,
                "version": version,
            })

        if cap_result.success:
            hpc = cap_result.data.get("hpc", {})
            if hpc.get("enabled"):
                clusters.append({
                    "id": "ku-hpc",
                    "name": "KU-HPC",
                    "type": "hpc",
                    "healthy": hz_result.success,
                    "submit_enabled": hpc.get("submit_enabled", False),
                })

        return AgenticPlugResult(
            success=True,
            data={"clusters": clusters, "count": len(clusters)},
        )

    def status(self) -> AgenticPlugResult:
        """Full status: health + capabilities + HPC (if auth)."""
        h_result = self.health()
        hz_result = self.healthz()
        cap_result = self.capabilities()

        status_data: Dict[str, Any] = {
            "connector": {
                "healthy": h_result.success,
                "url": self.base_url,
                "latency_ms": h_result.elapsed_ms,
            },
            "connector_detail": hz_result.data if hz_result.success else {},
            "capabilities": cap_result.data if cap_result.success else {},
            "auth": "token_configured" if self.has_auth else "none",
        }

        if self.has_auth:
            hpc_result = self._request("GET", "/hpc/squeue", auth=True)
            if hpc_result.success:
                status_data["hpc"] = hpc_result.data

        overall_healthy = h_result.success and hz_result.success
        return AgenticPlugResult(success=overall_healthy, data=status_data)

    def task(self, task_name: str) -> AgenticPlugResult:
        """Run a named task through the connector."""
        task_def = KNOWN_TASKS.get(task_name)
        if task_def is None:
            return AgenticPlugResult(
                success=False,
                error=f"Unknown task: {task_name}. Known: {', '.join(sorted(KNOWN_TASKS))}",
            )

        # For hpc tasks that go directly to /hpc/squeue
        if task_def["endpoint"].startswith("/hpc/"):
            return self._request(task_def["method"], task_def["endpoint"], auth=True)

        # For capability dispatch via POST /v1/tasks
        body = {"capability": task_def.get("capability", task_name)}
        return self._request(task_def["method"], task_def["endpoint"], auth=True, json_body=body)

    def send_task(
        self,
        task_name: str,
        connector_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> AgenticPlugResult:
        """Alias for task() with explicit connector_id (unused for local dispatch)."""
        return self.task(task_name)


# ── Helpers ────────────────────────────────────────────────────────────


def resolve_connector(client: Optional[AgenticPlugClient] = None) -> str:
    """Resolve the default connector ID.

    Priority:
    1. ECOSEEK_REMOTE_CONNECTOR env var
    2. First healthy connector from /healthz
    3. Default: "reumanlab"
    """
    if ECOSEEK_REMOTE_CONNECTOR:
        return ECOSEEK_REMOTE_CONNECTOR

    if client is None:
        client = AgenticPlugClient()

    try:
        clusters_result = client.clusters()
        if clusters_result.success:
            for c in clusters_result.data.get("clusters", []):
                if c.get("healthy"):
                    return c["id"]
    except Exception:
        pass

    return "reumanlab"
