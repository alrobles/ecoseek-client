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
class ConnectorInfo:
    """Discovered connector/endpoint info (for list_connectors / cluster listing)."""

    connector_id: str
    connector_type: str = "connector"
    version: str = "unknown"
    health: str = "unknown"  # "online", "degraded", "stale", "unknown"
    tools: List[Dict[str, Any]] = field(default_factory=list)
    capabilities: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_online(self) -> bool:
        return self.health == "online"


@dataclass
class TaskResult:
    """Result of a dispatched task."""

    status: str  # "accepted", "running", "completed", "failed", "error"
    task_id: str = ""
    output: Optional[str] = None
    error: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WhoAmI:
    """Session identity (used by CLI whoami)."""

    login: Optional[str] = None
    name: Optional[str] = None
    scopes: List[str] = field(default_factory=list)
    default_cluster: Optional[str] = None
    session_expired: bool = False
    connector_id: str = "unknown"
    connected: bool = False


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

    def _get(self, path: str, auth: bool = False) -> httpx.Response:
        url = f"{self.base_url}{path}"
        headers: Dict[str, str] = {"Accept": "application/json"}
        if auth:
            headers.update(self._auth_headers())
        return httpx.get(
            url, headers=headers, timeout=self.timeout, verify=self.verify_ssl
        )

    def _post(self, path: str, body: Dict[str, Any], auth: bool = True) -> httpx.Response:
        url = f"{self.base_url}{path}"
        headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if auth:
            headers.update(self._auth_headers())
        return httpx.post(
            url, json=body, headers=headers, timeout=self.timeout, verify=self.verify_ssl
        )

    # ── Public API ────────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        """GET /health — liveness check (no auth). Returns dict with 'status' key."""
        try:
            resp = self._get("/health")
            return resp.json() if resp.content else {"status": "error"}
        except httpx.ConnectError:
            return {"status": "unreachable", "error": "Connection refused"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def healthz(self) -> Dict[str, Any]:
        """GET /healthz — reumanlab connector detail (no auth)."""
        try:
            resp = self._get("/healthz")
            return resp.json()
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def capabilities(self) -> Dict[str, Any]:
        """GET /capabilities — full endpoint listing (no auth)."""
        try:
            resp = self._get("/capabilities")
            return resp.json()
        except Exception:
            return {}

    def whoami(self) -> WhoAmI:
        """Identify the current user/session.

        Returns a WhoAmI object for CLI consumption.
        """
        # Try healthz for connector detail
        try:
            hz = self.healthz()
        except Exception:
            hz = {}

        connector_id = hz.get("connector_id", "unknown")
        connected = hz.get("status") == "ok" or bool(hz.get("connector_id"))

        sess = self.session
        if sess:
            return WhoAmI(
                login=sess.login,
                name=sess.name,
                scopes=sess.scopes if isinstance(sess.scopes, list) else [],
                default_cluster=sess.default_cluster,
                session_expired=sess.session_expired,
                connector_id=connector_id,
                connected=connected,
            )
        elif self.has_auth:
            return WhoAmI(
                login="authenticated",
                name=None,
                scopes=[],
                default_cluster=None,
                session_expired=False,
                connector_id=connector_id,
                connected=connected,
            )
        else:
            return WhoAmI(
                login=None,
                name=None,
                scopes=[],
                default_cluster=None,
                session_expired=False,
                connector_id=connector_id,
                connected=connected,
            )

    def list_connectors(self) -> List[ConnectorInfo]:
        """List discovered connectors from /healthz and /capabilities.

        Returns a list of ConnectorInfo objects for CLI clusters command.
        """
        connectors: List[ConnectorInfo] = []

        # From /healthz — the reumanlab connector itself
        try:
            hz = self.healthz()
        except Exception:
            hz = {}

        if hz:
            cid = hz.get("connector_id", "reumanlab")
            version = "unknown"
            result = hz.get("result", {})
            if isinstance(result, dict):
                version = str(result.get("version", "unknown"))

            # Build tools list from capabilities
            try:
                caps = self.capabilities()
            except Exception:
                caps = {}

            endpoints = caps.get("endpoints", {})
            tools = [
                {"name": ep, "description": info.get("description", "")}
                for ep, info in endpoints.items()
            ]

            health_status = "online" if hz.get("status") == "ok" else "degraded"

            connectors.append(
                ConnectorInfo(
                    connector_id=cid,
                    connector_type="connector",
                    version=version,
                    health=health_status,
                    tools=tools,
                    capabilities=caps,
                )
            )

        # Also add HPC if enabled
        try:
            caps = self.capabilities()
        except Exception:
            caps = {}
        hpc_info = caps.get("hpc", {})
        if hpc_info.get("enabled"):
            connectors.append(
                ConnectorInfo(
                    connector_id="ku-hpc",
                    connector_type="hpc",
                    version="n/a",
                    health="online" if connectors and connectors[0].is_online else "unknown",
                    tools=[{"name": "hpc.status", "description": "Slurm queue status"},
                           {"name": "hpc.queue", "description": "Slurm queue"},
                           {"name": "hpc.submit", "description": "Submit allowlisted job"}],
                    capabilities={"hpc": hpc_info},
                )
            )

        return connectors

    def get_connector(self, connector_id: str) -> ConnectorInfo:
        """Get a specific connector by ID. Raises AgenticPlugError if not found."""
        connectors = self.list_connectors()
        for c in connectors:
            if c.connector_id == connector_id:
                return c
        raise AgenticPlugError(f"Connector '{connector_id}' not found")

    def send_task(
        self,
        task_name: str,
        connector_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """Dispatch a task via POST /v1/tasks or a known shortcut.

        Maps known task names to the appropriate endpoint:
        - remote.health → POST /v1/tasks {capability: "remote.health"}
        - hpc.status   → GET /hpc/squeue (falls back to POST /v1/tasks)
        - hpc.queue    → GET /hpc/squeue (falls back to POST /v1/tasks)

        If the task name doesn't match a known shortcut, it's sent directly
        as a capability dispatch.
        """
        if not self.has_auth:
            raise AgenticPlugAuthError(
                "Not authenticated. Set AGENTICPLUG_SESSION or CONNECTOR_TOKEN."
            )

        # Known shortcuts
        if task_name in ("hpc.status", "hpc.queue"):
            try:
                resp = self._get("/hpc/squeue", auth=True)
                data = resp.json()
                if resp.is_success:
                    return TaskResult(
                        status="completed",
                        task_id="",
                        output=json.dumps(data.get("jobs", [])),
                        raw=data,
                    )
                else:
                    return TaskResult(
                        status="error",
                        error=data.get("detail") or data.get("error") or f"HTTP {resp.status_code}",
                        raw=data,
                    )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 401:
                    raise AgenticPlugAuthError("Invalid or expired token") from exc
                return TaskResult(
                    status="error",
                    error=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                )
            except httpx.ConnectError as exc:
                raise AgenticPlugError(f"Cannot reach connector at {self.base_url}") from exc

        # Default: capability dispatch via POST /v1/tasks
        capability = task_name
        body: Dict[str, Any] = {"capability": capability}
        if payload:
            body.update(payload)

        try:
            resp = self._post("/v1/tasks", body, auth=True)
            data = resp.json()
            status = "completed" if resp.is_success else "error"
            task_id = data.get("task_id", "")
            return TaskResult(
                status=status,
                task_id=task_id,
                output=data.get("output") or json.dumps(data),
                error=data.get("error") or data.get("detail"),
                raw=data,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise AgenticPlugAuthError("Invalid or expired token") from exc
            if exc.response.status_code == 429:
                raise AgenticPlugError("Rate limited. Wait and retry.") from exc
            return TaskResult(
                status="error",
                error=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            )
        except httpx.ConnectError as exc:
            raise AgenticPlugError(f"Cannot reach connector at {self.base_url}") from exc


# ── Helpers ────────────────────────────────────────────────────────────


def resolve_connector(client: Optional[AgenticPlugClient] = None) -> str:
    """Resolve the default connector ID.

    Priority:
    1. ECOSEEK_REMOTE_CONNECTOR env var
    2. First online connector from /healthz
    3. Default: "reumanlab"
    """
    if ECOSEEK_REMOTE_CONNECTOR:
        return ECOSEEK_REMOTE_CONNECTOR

    if client is None:
        client = AgenticPlugClient()

    try:
        connectors = client.list_connectors()
        for c in connectors:
            if c.is_online:
                return c.connector_id
    except Exception:
        pass

    return "reumanlab"
