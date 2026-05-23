"""Configuration loader for ecoseek-client.

Reads environment variables and optional .env file.
Never stores secrets — all sensitive values come from the environment.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_AGENTICPLUG_URL = "http://127.0.0.1:3100"
DEFAULT_SESSION_RELATIVE = Path(".config") / "agenticplug" / "session.json"

# ---------------------------------------------------------------------------
# Env-loading (no dotenv dependency — lightweight)
# ---------------------------------------------------------------------------


def _load_dotenv(path: Optional[Path] = None) -> None:
    """Minimal .env loader — no external dependency needed."""
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


# ---------------------------------------------------------------------------
# Public config accessors
# ---------------------------------------------------------------------------


def get_agenticplug_url() -> str:
    """Resolve the AgenticPlug gateway URL."""
    return os.getenv("AGENTICPLUG_URL", DEFAULT_AGENTICPLUG_URL).rstrip("/")


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
