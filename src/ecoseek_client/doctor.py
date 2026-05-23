"""Diagnostics for the local EcoSeek environment.

``ecoseek doctor`` checks Python, WSL, git, AgenticPlug connectivity,
and HPC availability — producing actionable output.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Tuple


def _check(ok: bool, msg: str) -> Tuple[bool, str]:
    status = "[OK]" if ok else "[!!]"
    return ok, f"{status} {msg}"


def _find_executable(name: str) -> bool:
    return shutil.which(name) is not None


def _is_wsl() -> bool:
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def run_doctor() -> int:
    """Run full environment diagnostics. Returns 0 on all-green, 1 on warnings."""
    all_ok = True

    def emit(ok: bool, msg: str) -> None:
        nonlocal all_ok
        if not ok:
            all_ok = False
        print(f"  {msg}")

    print("ecoseek doctor")
    print("=" * 50)
    print(f"  ecoseek-client version: 0.1.0")
    print(f"  timestamp: {__import__('datetime').datetime.now().isoformat()}")

    # Python
    ok, msg = _check(True, f"Python {sys.version}")
    emit(ok, msg)
    ok, msg = _check(sys.version_info >= (3, 10), "Python >= 3.10 required")
    emit(ok, msg)

    # OS
    is_wsl = _is_wsl()
    ok, msg = _check(True, f"OS: {platform.system()} {platform.release()} {'(WSL2)' if is_wsl else ''}")
    emit(ok, msg)

    # Git
    git_ok = _find_executable("git")
    ok, msg = _check(git_ok, "git: found" if git_ok else "git: NOT FOUND — install git")
    emit(ok, msg)

    # SSH
    ssh_ok = Path("~/.ssh/id_ed25519.pub").expanduser().exists() or Path("~/.ssh/id_rsa.pub").expanduser().exists()
    ok, msg = _check(ssh_ok, "ssh key: found" if ssh_ok else "ssh key: not found — generate with ssh-keygen")
    emit(ok, msg)

    # AgenticPlug
    from ecoseek_client.config import get_agenticplug_url
    ap_url = get_agenticplug_url()
    ok, msg = _check(bool(ap_url), f"AgenticPlug URL: {ap_url}")
    emit(ok, msg)

    # Session
    from ecoseek_client.session import load_session_or_none
    session = load_session_or_none()
    if session:
        ok, msg = _check(True, f"AgenticPlug session: {session.identity or '(loaded)'}")
        emit(ok, msg)
        if session.is_expired():
            ok, msg = _check(False, "Session is EXPIRED — run `agenticplug login`")
            emit(ok, msg)
        if session.default_cluster:
            ok, msg = _check(True, f"Default cluster: {session.default_cluster}")
            emit(ok, msg)
    else:
        ok, msg = _check(False, "AgenticPlug session: NOT FOUND")
        emit(ok, msg)
        print("    Run `agenticplug login` to authenticate.")

    # HPC
    from ecoseek_client.config import is_hpc_available
    hpc = is_hpc_available()
    ok, msg = _check(hpc, f"HPC: {'available' if hpc else 'not configured (env vars missing)'}")
    emit(ok, msg)

    # Docker
    docker_ok = _find_executable("docker")
    ok, msg = _check(docker_ok, "docker: found" if docker_ok else "docker: not found (optional)")
    emit(ok, msg)

    # Network
    import httpx
    try:
        r = httpx.get(f"{ap_url}/health", timeout=5.0)
        ok, msg = _check(r.status_code == 200, f"AgenticPlug health: HTTP {r.status_code}")
    except Exception as e:
        ok, msg = _check(False, f"AgenticPlug health: unreachable — {e}")
    emit(ok, msg)

    print("=" * 50)
    if all_ok:
        print("All checks passed.")
    else:
        print("Some checks failed. Review [!!] items above.")
    return 0 if all_ok else 1
