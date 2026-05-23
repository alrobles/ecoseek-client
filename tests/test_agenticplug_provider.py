"""Tests for the AgenticPlug client provider.

Uses httpx mocks — no real network calls.
"""

from __future__ import annotations

import json
import os
from unittest import mock

import pytest
from pytest_httpx import HTTPXMock

from ecoseek_client.providers.agenticplug import (
    AgenticPlugAuthError,
    AgenticPlugClient,
    AgenticPlugError,
    ConnectorInfo,
    resolve_connector,
)
from ecoseek_client.session import Session, SessionError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Return a client pointed at a fake gateway with no auth."""
    return AgenticPlugClient(base_url="http://127.0.0.1:9999", token=None, timeout=5.0)


@pytest.fixture
def auth_client():
    """Return a client with a fake auth token."""
    return AgenticPlugClient(
        base_url="http://127.0.0.1:9999",
        token="test-token-123",
        timeout=5.0,
    )


@pytest.fixture
def mock_connectors():
    """Sample connector list from the gateway."""
    return {
        "connectors": [
            {
                "connector_id": "reumanlab",
                "display_name": "Reuman Lab",
                "owner": "alrobles",
                "version": "0.7.0",
                "connector_type": "local",
                "health": "online",
                "capabilities": {"hpc": True, "read": True, "write": False},
                "tools": [
                    {"name": "remote.health", "enabled": True, "risk_level": "read"},
                    {"name": "hpc.status", "enabled": True, "risk_level": "read"},
                    {"name": "hpc.queue", "enabled": True, "risk_level": "read"},
                ],
            },
            {
                "connector_id": "ku-hpc",
                "display_name": "KU HPC",
                "owner": "alrobles",
                "version": "0.5.0",
                "connector_type": "remote",
                "health": "stale",
                "capabilities": {"hpc": True, "read": True},
                "tools": [],
            },
        ]
    }


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_ok(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://127.0.0.1:9999/health", json={"status": "ok"})
    result = client.health()
    assert result["status"] == "ok"


def test_health_unreachable(client):
    # No mock — httpx will fail to connect
    result = client.health()
    assert result["status"] == "unreachable"


# ---------------------------------------------------------------------------
# whoami (no network)
# ---------------------------------------------------------------------------


def test_whoami_no_session(client, tmp_path, monkeypatch):
    # Point AGENTICPLUG_SESSION_FILE to a nonexistent file
    monkeypatch.setenv("AGENTICPLUG_SESSION_FILE", str(tmp_path / "nonexistent.json"))
    c = AgenticPlugClient(base_url="http://127.0.0.1:9999", timeout=5.0)
    info = c.whoami()
    assert info.login is None


def test_whoami_with_session(client, tmp_path, monkeypatch):
    session_path = tmp_path / "session.json"
    session_path.write_text(json.dumps({
        "token": "gh_token",
        "user": {"login": "alrobles", "name": "Alex"},
        "scopes": ["read:user"],
        "default_cluster": "reumanlab",
    }))
    monkeypatch.setenv("AGENTICPLUG_SESSION_FILE", str(session_path))
    # Re-create client so it picks up env
    c = AgenticPlugClient(base_url="http://127.0.0.1:9999", timeout=5.0)
    info = c.whoami()
    assert info.login == "alrobles"
    assert info.name == "Alex"
    assert "read:user" in info.scopes
    assert info.default_cluster == "reumanlab"


# ---------------------------------------------------------------------------
# List connectors
# ---------------------------------------------------------------------------


def test_list_connectors(client, httpx_mock: HTTPXMock, mock_connectors):
    httpx_mock.add_response(
        url="http://127.0.0.1:9999/v1/connectors",
        json=mock_connectors,
    )
    result = client.list_connectors()
    assert len(result) == 2
    assert result[0].connector_id == "reumanlab"
    assert result[0].is_online is True
    assert result[1].is_online is False


def test_list_connectors_empty(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://127.0.0.1:9999/v1/connectors",
        json={"connectors": []},
    )
    result = client.list_connectors()
    assert result == []


def test_list_connectors_503(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://127.0.0.1:9999/v1/connectors",
        status_code=503,
    )
    with pytest.raises(AgenticPlugError, match="503"):
        client.list_connectors()


# ---------------------------------------------------------------------------
# Get single connector
# ---------------------------------------------------------------------------


def test_get_connector(client, httpx_mock: HTTPXMock, mock_connectors):
    httpx_mock.add_response(
        url="http://127.0.0.1:9999/v1/connectors/reumanlab",
        json={"connector": mock_connectors["connectors"][0]},
    )
    c = client.get_connector("reumanlab")
    assert c.connector_id == "reumanlab"
    assert c.health == "online"


def test_get_connector_404(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://127.0.0.1:9999/v1/connectors/nonexistent",
        status_code=404,
    )
    with pytest.raises(AgenticPlugError, match="not found"):
        client.get_connector("nonexistent")


# ---------------------------------------------------------------------------
# Send task
# ---------------------------------------------------------------------------


def test_send_task_no_auth(client):
    with pytest.raises(AgenticPlugAuthError, match="Not authenticated"):
        client.send_task("hello")


def test_send_task_ok(auth_client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://127.0.0.1:9999/tasks",
        json={"task_id": "task_001", "status": "accepted"},
    )
    result = auth_client.send_task("remote.health")
    assert result.status == "accepted"
    assert result.task_id == "task_001"


def test_send_task_401(auth_client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://127.0.0.1:9999/tasks", status_code=401)
    result = auth_client.send_task("remote.health")
    assert result.status == "failed"
    assert "Authentication failed" in (result.error or "")


# ---------------------------------------------------------------------------
# Get task status
# ---------------------------------------------------------------------------


def test_get_task_status(auth_client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://127.0.0.1:9999/tasks/task_001",
        json={"status": "completed", "output": "all good"},
    )
    result = auth_client.get_task_status("task_001")
    assert result.status == "completed"
    assert result.output == "all good"


def test_get_task_status_404(auth_client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://127.0.0.1:9999/tasks/task_missing",
        status_code=404,
    )
    result = auth_client.get_task_status("task_missing")
    assert result.status == "unknown"


# ---------------------------------------------------------------------------
# resolve_connector
# ---------------------------------------------------------------------------


def test_resolve_connector_explicit_env(monkeypatch):
    monkeypatch.setenv("ECOSEEK_REMOTE_CONNECTOR", "ku-hpc")
    assert resolve_connector() == "ku-hpc"


def test_resolve_connector_fallback():
    # No env, no session → returns default
    assert resolve_connector() == "reumanlab"


# ---------------------------------------------------------------------------
# Token safety — no leaks
# ---------------------------------------------------------------------------


def test_token_not_printed(auth_client):
    """Verify that str() and repr() on the client don't expose the token."""
    s = str(auth_client)
    assert "test-token-123" not in s
    r = repr(auth_client)
    assert "test-token-123" not in r
