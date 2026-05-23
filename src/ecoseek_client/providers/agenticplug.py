"""AgenticPlug provider — HTTP client for the AgenticPlug broker/connector.

Talks to the local connector (default: http://localhost:3100) or a remote
gateway. Supports:

- Health checks (no auth)
- Capability listing (no auth)
- Authenticated calls with bearer token from env or session file
- HPC operations (squeue, logs, submit)
- Task dispatch via Hermes orchestration

Token handling:
- Prefers AGENTICPLUG_SESSION / CONNECTOR_TOKEN from environment.
- Falls back to ~/.config/agenticplug/session.json.
- NEVER prints tokens in output.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from ..config import (
    AGENTICPLUG_TIMEOUT,
    AGENTICPLUG_URL,
    AGENTICPLUG_VERIFY_SSL,
    agenticplug_token,
)
from ..session import AgenticPlugSession, load_session_or_none

# ── AgenticPlug task dispatch ─────────────────────────────────────────
KNOWN_TASKS = {
    "remote.health": {
        "endpoint": "/healthz",
        "method": "GET",
        "description": "Connector health check",
    },
    "hpc.status": {
        "endpoint": "/hpc/squeue",
        "method": "GET",
        "description": "Slurm queue status (read-only)",
    },
    "hpc.queue": {
        "endpoint": "/hpc/squeue",
        "method": "GET",
        "description": "Slurm queue status (read-only)",
    },
    "hpc.submit": {
        "endpoint": "/hpc/submit",
        "method": "POST",
        "description": "Submit allowlisted template job",
    },
}


@dataclass
class AgenticPlugResult:
    """Result from an AgenticPlug API call."""

    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    status_code: int = 0
    error: str = ""
    elapsed_ms: float = 0.0
    endpoint: str = ""


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

    def _auth_headers(self) -> Dict[str, str]:
        headers = {}
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
                success=False, error=f"Request timed out after {self.timeout}s: {url}", endpoint=path
            )
        except Exception as exc:
            return AgenticPlugResult(
                success=False, error=f"Request failed: {exc}", endpoint=path
            )

    # ── Public API ────────────────────────────────────────────────────

    def health(self) -> AgenticPlugResult:
        """Basic connector health check (no auth)."""
        return self._request("GET", "/health")

    def healthz(self) -> AgenticPlugResult:
        """Detailed reumanlab connector health (no auth)."""
        return self._request("GET", "/healthz")

    def capabilities(self) -> AgenticPlugResult:
        """List all connector capabilities (no auth)."""
        return self._request("GET", "/capabilities")

    def whoami(self) -> AgenticPlugResult:
        """Identify the current user/session."""
        result = self.healthz()
        if not result.success:
            return result

        connector_id = result.data.get("connector_id", "unknown")
        info: Dict[str, Any] = {
            "connector_id": connector_id,
            "connected": result.success,
        }

        sess = self.session
        if sess and sess.identity:
            info["user"] = sess.identity
            info["scopes"] = sess.scopes
            info["default_cluster"] = sess.default_cluster
            if sess.expires_at:
                info["session_expires"] = sess.expires_at
        elif self.has_auth:
            info["auth"] = "token_configured"
        else:
            info["auth"] = "none"

        return AgenticPlugResult(
            success=True,
            data=info,
            status_code=result.status_code,
            elapsed_ms=result.elapsed_ms,
            endpoint=result.endpoint,
        )

    def clusters(self) -> AgenticPlugResult:
        """List available clusters/connectors."""
        cap_result = self.capabilities()
        hz_result = self.healthz()

        clusters: List[Dict[str, Any]] = []

        if hz_result.success:
            connector_id = hz_result.data.get("connector_id", "reumanlab")
            version = "unknown"
            r = hz_result.data.get("result", {})
            if isinstance(r, dict):
                version = r.get("version", "unknown")
            clusters.append({
                "id": connector_id,
                "name": connector_id,
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
        """Full status: health + capabilities + HPC status (with auth)."""
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
        return self._request(task_def["method"], task_def["endpoint"], auth=True)

    def submit_task(self, task_description: str, repo: str = "") -> AgenticPlugResult:
        """Submit a task for Hermes orchestration via POST /v1/orchestrate."""
        body: Dict[str, str] = {"task": task_description}
        if repo:
            body["repo"] = repo
            body["mode"] = "ecoSeek"
        return self._request("POST", "/v1/orchestrate", auth=True, json_body=body)

    def poll_task(self, task_id: str) -> AgenticPlugResult:
        """Poll the status of a previously submitted task."""
        return self._request("GET", f"/tasks/{task_id}", auth=True)
