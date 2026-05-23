"""AgenticPlug session management.

Reads the session JSON produced by ``agenticplug login`` (GitHub Device Flow).
The session lives at ``~/.config/agenticplug/session.json`` and is owned/rotated
by the AgenticPlug CLI. ecoseek-client only consumes it as a client.

Session format (v2):
{
  "version": 2,
  "provider": "github",
  "user": {"login": "...", "name": "...", ...},
  "session": {
    "id": "<bearer-token>",
    "token_type": "Bearer",
    "expires_at": <unix-ms-timestamp>
  },
  "broker_url": "https://...",
  ...
}
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
    expires_at: Optional[str] = None  # ISO string for display
    expires_at_ms: Optional[int] = None  # raw Unix ms
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

    @property
    def login(self) -> Optional[str]:
        """GitHub login from session (used by CLI whoami)."""
        if not isinstance(self.user, dict):
            return None
        return self.user.get("login")

    @property
    def name(self) -> Optional[str]:
        """Display name from session."""
        if not isinstance(self.user, dict):
            return None
        return self.user.get("name") or self.user.get("login")

    @property
    def session_expired(self) -> bool:
        """True if the session is expired."""
        return self.is_expired()

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        """True if ``expires_at_ms`` is set and in the past."""
        if self.expires_at_ms is None:
            # Try parsing ISO string fallback
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

        # Unix ms timestamp
        exp_dt = datetime.fromtimestamp(self.expires_at_ms / 1000.0, tz=timezone.utc)
        current = now or datetime.now(timezone.utc)
        return exp_dt <= current

    def authorization_header(self) -> Optional[str]:
        """Build the Authorization header value."""
        if not self.token:
            return None
        return f"{self.token_type or 'Bearer'} {self.token}"


# Alias for the agenticplug provider
AgenticPlugSession = Session


def _parse_expires_at(expires_raw: Any) -> tuple[Optional[str], Optional[int]]:
    """Parse expires_at from either ISO string or Unix ms timestamp.

    Returns (iso_string, unix_ms).
    """
    if expires_raw is None:
        return None, None

    if isinstance(expires_raw, (int, float)):
        # Unix timestamp in milliseconds
        ms = int(expires_raw)
        try:
            dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
            return dt.isoformat(), ms
        except (ValueError, OSError):
            return str(ms), ms

    # String — try as ISO
    return str(expires_raw), None


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

    # v2 session format: token is at session.id
    session_data = data.get("session") or {}
    if not isinstance(session_data, dict):
        session_data = {}

    token = session_data.get("id") or data.get("token")
    token_type = session_data.get("token_type") or data.get("token_type") or "Bearer"

    expires_raw = session_data.get("expires_at") or data.get("expires_at")
    expires_at_iso, expires_at_ms = _parse_expires_at(expires_raw)

    scopes = data.get("scopes") or []
    if not isinstance(scopes, list):
        scopes = []

    user = data.get("user") or {}
    if not isinstance(user, dict):
        user = {}

    return Session(
        path=resolved,
        base_url=data.get("broker_url") or data.get("base_url"),
        token=token,
        token_type=token_type,
        expires_at=expires_at_iso,
        expires_at_ms=expires_at_ms,
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
