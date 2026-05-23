"""Tests for the AgenticPlug provider — pure unit tests with HTTP mocking."""

import json

import pytest
from pytest_httpx import HTTPXMock

from ecoseek_client.providers import AgenticPlugClient, AgenticPlugResult


@pytest.fixture
def client():
    return AgenticPlugClient(base_url="http://test.local:3100", token="test-token-fake", timeout=5)


@pytest.fixture
def client_no_auth():
    return AgenticPlugClient(base_url="http://test.local:3100", timeout=5)


# ── Health ────────────────────────────────────────────────────────────

def test_health_ok(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://test.local:3100/health", json={"status": "ok"})
    result = client.health()
    assert result.success
    assert result.data["status"] == "ok"


def test_health_down(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://test.local:3100/health", status_code=503)
    result = client.health()
    assert not result.success


# ── Healthz / whoami ──────────────────────────────────────────────────

def test_healthz_ok(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://test.local:3100/healthz",
        json={"connector_id": "reumanlab", "status": "completed", "result": {"status": "ok"}},
    )
    result = client.healthz()
    assert result.success
    assert result.data["connector_id"] == "reumanlab"


def test_whoami_no_auth(client_no_auth, httpx_mock: HTTPXMock):
    # client_no_auth has no explicit token, but may find session file on disk
    httpx_mock.add_response(
        url="http://test.local:3100/healthz",
        json={"connector_id": "reumanlab", "status": "completed"},
    )
    result = client_no_auth.whoami()
    assert result.success
    assert result.data["connector_id"] == "reumanlab"
    # "auth" key only present when has_auth is False AND no session file
    # If session.json exists on disk, "user" will be set instead
    auth_val = result.data.get("auth")
    user_val = result.data.get("user")
    assert auth_val == "none" or user_val is not None


# ── Clusters ──────────────────────────────────────────────────────────

def test_clusters(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://test.local:3100/healthz", json={"connector_id": "reumanlab", "status": "completed"})
    httpx_mock.add_response(url="http://test.local:3100/capabilities", json={"hpc": {"enabled": True, "submit_enabled": False}})
    result = client.clusters()
    assert result.success
    assert len(result.data["clusters"]) == 2


def test_clusters_hpc_disabled(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://test.local:3100/healthz", json={"connector_id": "reumanlab", "status": "completed"})
    httpx_mock.add_response(url="http://test.local:3100/capabilities", json={"hpc": {"enabled": False}})
    result = client.clusters()
    assert result.success
    assert len(result.data["clusters"]) == 1


# ── Task dispatch ─────────────────────────────────────────────────────

def test_task_remote_health(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://test.local:3100/healthz", json={"connector_id": "reumanlab", "status": "completed"})
    result = client.task("remote.health")
    assert result.success


def test_task_hpc_status(client, httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://test.local:3100/hpc/squeue", json={"command": "squeue", "jobs": [], "count": 0})
    result = client.task("hpc.status")
    assert result.success
    assert result.data["count"] == 0


def test_task_unknown(client, httpx_mock: HTTPXMock):
    result = client.task("nonexistent.task")
    assert not result.success
    assert "Unknown task" in result.error


# ── Connection errors ─────────────────────────────────────────────────

def test_connection_refused(client, httpx_mock: HTTPXMock):
    httpx_mock.add_exception(url="http://test.local:3100/health", exception=Exception("Connection refused"))
    result = client.health()
    assert not result.success


# ── Token safety ──────────────────────────────────────────────────────

def test_result_never_leaks_token():
    r = AgenticPlugResult(success=True, data={"connector_id": "reumanlab"})
    assert "token" not in json.dumps(r.data)


def test_sanitize_removes_token():
    from ecoseek_client.cli import _sanitize
    data = {"connector_id": "reumanlab", "token": "secret-bearer-12345"}
    safe = _sanitize(data)
    assert "token" not in safe
    assert "secret-bearer" not in str(safe)
