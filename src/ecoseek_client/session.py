"""AgenticPlug session management.

Reads the session JSON produced by ``agenticplug login`` (GitHub Device Flow).
The session lives at ``~/.config/agenticplug/session.json`` and is owned/rotated
by the AgenticPlug CLI. ecoseek-client only consumes it as a client.

This module is intentionally dependency-free. It does not perform auth, refresh
tokens, or talk to the gateway — higher layers do that.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ecoseek_client.config import get_agenticplug_session_file

LOGIN_HINT = (
    "Run `agenticplug login` to create a session, then `agenticplug whoami` "
    "to confirm it. See docs/agenticplug.md for setup."
)


class SessionError(Exception):
    """Raised when a session file is missing, unreadable, or invalid."""


@dataclass
class Session:
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
        """Best-effort human-readable identity (GitHub login)."""
        if not isinstance(self.user, dict):
            return None
        return self.user.get("login") or self.user.get("name") or self.user.get("id")

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        """True if ``expires_at`` is set and in the past."""
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
        """Build the Authorization header value."""
        if not self.token:
            return None
        return f"{self.token_type or 'Bearer'} {self.token}"


def load_session(path: Optional[Path] = None) -> Session:
    """Load and parse the AgenticPlug session file.

    Raises ``SessionError`` with an actionable hint on any failure.
    """
    resolved = Path(path).expanduser() if path else get_agenticplug_session_file()
    if not resolved.exists():
        raise SessionError(
            f"AgenticPlug session not found at {resolved}. {LOGIN_HINT}"
        )
    try:
        data = json.loads(resolved.read_text())
    except json.JSONDecodeError as exc:
        raise SessionError(
            f"Session at {resolved} is not valid JSON: {exc}. {LOGIN_HINT}"
        ) from exc
    except OSError as exc:
        raise SessionError(
            f"Cannot read session at {resolved}: {exc}. {LOGIN_HINT}"
        ) from exc

    if not isinstance(data, dict):
        raise SessionError(f"Session must be a JSON object. {LOGIN_HINT}")

    scopes = data.get("scopes") or []
    if not isinstance(scopes, list):
        scopes = []

    user = data.get("user") or {}
    if not isinstance(user, dict):
        user = {}

    return Session(
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


def load_session_or_none(path: Optional[Path] = None) -> Optional[Session]:
    """Same as ``load_session`` but returns ``None`` when file is absent."""
    try:
        return load_session(path)
    except SessionError as exc:
        if "not found" in str(exc):
            return None
        raise
