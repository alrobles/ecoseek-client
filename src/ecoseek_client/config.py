"""Configuration loader for ecoseek-client.

Reads environment variables and optional .env files. All secrets stay local;
nothing is hardcoded or committed.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Auto-load .env from current directory and home directory
_load_paths = [Path.cwd() / ".env", Path.home() / ".ecoseek" / ".env"]
for _p in _load_paths:
    if _p.exists():
        load_dotenv(_p)


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# AgenticPlug
AGENTICPLUG_URL: str = _env("AGENTICPLUG_URL", "http://localhost:3100")
AGENTICPLUG_SESSION: str = _env("AGENTICPLUG_SESSION", "")
AGENTICPLUG_SESSION_FILE: str = _env(
    "AGENTICPLUG_SESSION_FILE",
    str(Path.home() / ".config" / "agenticplug" / "session.json"),
)
AGENTICPLUG_TIMEOUT: int = int(_env("AGENTICPLUG_TIMEOUT", "30"))
AGENTICPLUG_VERIFY_SSL: bool = _env("AGENTICPLUG_VERIFY_SSL", "true").lower() != "false"

# Connector
ECOSEEK_REMOTE_CONNECTOR: str = _env("ECOSEEK_REMOTE_CONNECTOR", "reumanlab")


def agenticplug_token() -> Optional[str]:
    """Return a bearer token, preferring AGENTICPLUG_SESSION over CONNECTOR_TOKEN."""
    token = AGENTICPLUG_SESSION
    if token:
        return token
    return os.getenv("CONNECTOR_TOKEN") or None


def has_agenticplug_auth() -> bool:
    """True if we have at least one auth mechanism configured."""
    return agenticplug_token() is not None
