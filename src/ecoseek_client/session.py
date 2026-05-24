"""AgenticPlug session-file loader.

Reads the session JSON produced by ``agenticplug login`` (GitHub Device Flow).
The session lives at ``~/.config/agenticplug/session.json`` and is owned and
rotated by the AgenticPlug CLI. ecoseek-client consumes it read-only.

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
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

LOGIN_HINT = (
    "Run `ecoseek login` to create a session, then `ecoseek agenticplug me` "
    "to confirm it."
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
        if not isinstance(self.user, dict):
            return None
        return self.user.get("login") or self.user.get("name") or str(self.user.get("id", ""))

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
        if not self.token:
            return None
        return f"{self.token_type or 'Bearer'} {self.token}"


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


def default_session_path() -> Path:
    override = os.environ.get("AGENTICPLUG_SESSION_FILE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "agenticplug" / "session.json"


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

    return AgenticPlugSession(
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


def save_session(
    session_id: str,
    user: Dict[str, Any],
    expires_at: Any = None,
    broker_url: Optional[str] = None,
    scopes: Optional[List[str]] = None,
    path: Optional[Path] = None,
) -> Path:
    """Write a v2 session file to disk.

    Creates parent directories if needed. Returns the path written.
    """
    resolved = Path(path).expanduser() if path else default_session_path()
    resolved.parent.mkdir(parents=True, exist_ok=True)

    data: Dict[str, Any] = {
        "version": 2,
        "provider": "github",
        "user": user,
        "session": {
            "id": session_id,
            "token_type": "Bearer",
            "expires_at": expires_at,
        },
    }
    if broker_url:
        data["broker_url"] = broker_url
    if scopes:
        data["scopes"] = scopes

    resolved.write_text(json.dumps(data, indent=2, default=str) + "\n")
    # Restrict permissions to owner-only
    resolved.chmod(0o600)
    return resolved


def delete_session(path: Optional[Path] = None) -> bool:
    """Delete the session file. Returns True if a file was removed."""
    resolved = Path(path).expanduser() if path else default_session_path()
    if resolved.exists():
        resolved.unlink()
        return True
    return False


def load_session_or_none(path: Optional[Path] = None) -> Optional[AgenticPlugSession]:
    try:
        return load_session(path)
    except AgenticPlugSessionError as exc:
        if "not found" in str(exc):
            return None
        raise
