"""Configuration loader for ecoseek-client.

Reads environment variables and optional .env files. All secrets stay local;
nothing is hardcoded or committed.

Broker URL resolution order:
1. AGENTICPLUG_URL env var (explicit override)
2. broker_url from session file (~/.config/agenticplug/session.json)
3. REMOTE_BROKER_URL (https://broker.ecoseek.org) — public remote broker
4. LOCAL_FALLBACK_URL (http://127.0.0.1:3100) — local connector
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Module-level constants (imported by providers)
# ---------------------------------------------------------------------------

LOCAL_FALLBACK_URL: str = "http://127.0.0.1:3100"
REMOTE_BROKER_URL: str = "https://broker.ecoseek.org"
DEFAULT_AGENTICPLUG_URL: str = LOCAL_FALLBACK_URL
DEFAULT_SESSION_RELATIVE: Path = Path(".config") / "agenticplug" / "session.json"

# Resolved once at import time
AGENTICPLUG_URL: str = os.getenv("AGENTICPLUG_URL", DEFAULT_AGENTICPLUG_URL).rstrip("/")
AGENTICPLUG_TIMEOUT: int = int(os.getenv("AGENTICPLUG_TIMEOUT", "30"))
AGENTICPLUG_VERIFY_SSL: bool = os.getenv("AGENTICPLUG_VERIFY_SSL", "1").lower() not in ("0", "false", "no", "off")
ECOSEEK_REMOTE_CONNECTOR: Optional[str] = os.getenv("ECOSEEK_REMOTE_CONNECTOR")

# ---------------------------------------------------------------------------
# Env-loading (lightweight — no external dotenv dependency)
# ---------------------------------------------------------------------------


def _load_dotenv(path: Optional[Path] = None) -> None:
    """Minimal .env loader."""
    target = path or Path.cwd() / ".env"
    if not target.exists():
        return
    for line in target.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()
# Also try ~/.ecoseek/.env
_ecoseek_env = Path.home() / ".ecoseek" / ".env"
if _ecoseek_env.exists():
    _load_dotenv(_ecoseek_env)


# ---------------------------------------------------------------------------
# Token resolution
# ---------------------------------------------------------------------------


def agenticplug_token() -> Optional[str]:
    """Resolve the AgenticPlug bearer token from environment.

    Checks AGENTICPLUG_SESSION first, then CONNECTOR_TOKEN.
    """
    return os.getenv("AGENTICPLUG_SESSION") or os.getenv("CONNECTOR_TOKEN")


def has_agenticplug_auth() -> bool:
    """True if we have at least one auth mechanism configured."""
    return agenticplug_token() is not None


# ---------------------------------------------------------------------------
# Public config accessors
# ---------------------------------------------------------------------------


def _broker_url_from_session() -> Optional[str]:
    """Read broker_url from the session file without importing session module."""
    session_path = Path.home() / DEFAULT_SESSION_RELATIVE
    if not session_path.exists():
        return None
    try:
        data = json.loads(session_path.read_text())
        url = data.get("broker_url") or data.get("base_url")
        if url and isinstance(url, str):
            return url.rstrip("/")
    except (json.JSONDecodeError, OSError):
        pass
    return None


def get_agenticplug_url() -> str:
    """Resolve the AgenticPlug gateway URL.

    Resolution order:
    1. AGENTICPLUG_URL env var (explicit override)
    2. broker_url from session file
    3. https://broker.ecoseek.org (remote default)
    """
    env_url = os.getenv("AGENTICPLUG_URL")
    if env_url:
        return env_url.rstrip("/")

    session_url = _broker_url_from_session()
    if session_url:
        return session_url

    return REMOTE_BROKER_URL


def get_agenticplug_session() -> Optional[str]:
    """Return the AGENTICPLUG_SESSION token if set."""
    return os.getenv("AGENTICPLUG_SESSION")


def get_agenticplug_session_file() -> Path:
    """Path to the AgenticPlug session JSON file."""
    override = os.getenv("AGENTICPLUG_SESSION_FILE")
    if override:
        return Path(override).expanduser()
    return Path.home() / DEFAULT_SESSION_RELATIVE


def get_remote_connector() -> Optional[str]:
    """Return the ECOSEEK_REMOTE_CONNECTOR if set."""
    return os.getenv("ECOSEEK_REMOTE_CONNECTOR")


def is_hpc_available() -> bool:
    """True if HPC environment variables are present."""
    return bool(os.getenv("HPC_HOST") or os.getenv("SLURM_CLUSTER_NAME"))
