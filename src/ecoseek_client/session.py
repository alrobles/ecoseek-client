"""AgenticPlug session-file loader.

Reads the session JSON produced by ``agenticplug login`` (GitHub Device Flow).
The session lives at ``~/.config/agenticplug/session.json`` and is owned and
rotated by the AgenticPlug CLI. ecoseek-client consumes it read-only.

Schema (fields treated as optional unless noted):

    {
      "base_url":       "https://<host>/v1",
      "token":          "<bearer>",
      "token_type":     "Bearer",
      "expires_at":     "2026-05-17T20:00:00Z",
      "user": {"login": "octocat", "id": 1, "name": "..."},
      "scopes":         ["read:user", "read:org"],
      "route_header":   "hermes",
      "model":          "hermes",
      "default_cluster": "ku-hpc"
    }
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import AGENTICPLUG_SESSION_FILE

LOGIN_HINT = (
    "Run `agenticplug login` to create a session, then `agenticplug whoami` "
    "to confirm it. See docs/agenticplug_device_flow.md for setup."
)


class AgenticPlugSessionError(Exception):
    """Raised when a session file is missing, unreadable, or invalid."""


@dataclass
class AgenticPlugSession:
    """Parsed view of ``~/.config/agenticplug/session.json``."""

    path: Path
    base_url: Optional[str] = None
    token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[str] = None
    user: Dict[str, Any] = field(default_factory=dict)
    scopes: List[str] = field(default_factory=list)
    route_header: Optional[str] = None
    model: Optional[str] = None
    default_cluster: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def identity(self) -> Optional[str]:
        if not isinstance(self.user, dict):
            return None
        return self.user.get("login") or self.user.get("name") or str(self.user.get("id", ""))

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        if not self.expires_at:
            return False
        try:
            ts = self.expires_at
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            exp = datetime.fromisoformat(ts)
        except ValueError:
            return False
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        current = now or datetime.now(timezone.utc)
        return exp <= current

    def authorization_header(self) -> Optional[str]:
        if not self.token:
            return None
        return f"{self.token_type or 'Bearer'} {self.token}"


def default_session_path() -> Path:
    override = os.environ.get("AGENTICPLUG_SESSION_FILE")
    if override:
        return Path(override).expanduser()
    return Path(AGENTICPLUG_SESSION_FILE) if AGENTICPLUG_SESSION_FILE else Path.home() / ".config" / "agenticplug" / "session.json"


def load_session(path: Optional[Path] = None) -> AgenticPlugSession:
    resolved = Path(path).expanduser() if path else default_session_path()
    if not resolved.exists():
        raise AgenticPlugSessionError(
            f"AgenticPlug session not found at {resolved}. {LOGIN_HINT}"
        )
    try:
        data = json.loads(resolved.read_text())
    except json.JSONDecodeError as exc:
        raise AgenticPlugSessionError(
            f"AgenticPlug session at {resolved} is not valid JSON: {exc}. {LOGIN_HINT}"
        ) from exc
    except OSError as exc:
        raise AgenticPlugSessionError(
            f"Cannot read AgenticPlug session at {resolved}: {exc}. {LOGIN_HINT}"
        ) from exc

    if not isinstance(data, dict):
        raise AgenticPlugSessionError(
            f"AgenticPlug session at {resolved} must be a JSON object. {LOGIN_HINT}"
        )

    scopes = data.get("scopes") or []
    if not isinstance(scopes, list):
        scopes = []

    user = data.get("user") or {}
    if not isinstance(user, dict):
        user = {}

    return AgenticPlugSession(
        path=resolved,
        base_url=data.get("base_url"),
        token=data.get("token"),
        token_type=data.get("token_type") or "Bearer",
        expires_at=data.get("expires_at"),
        user=user,
        scopes=scopes,
        route_header=data.get("route_header"),
        model=data.get("model"),
        default_cluster=data.get("default_cluster"),
        raw=data,
    )


def load_session_or_none(path: Optional[Path] = None) -> Optional[AgenticPlugSession]:
    try:
        return load_session(path)
    except AgenticPlugSessionError as exc:
        if "not found" in str(exc):
            return None
        raise
