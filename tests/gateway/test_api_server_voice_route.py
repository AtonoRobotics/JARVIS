"""Tests for /v1/voice/route Home Assistant voice ingress."""

from unittest.mock import AsyncMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gateway.config import PlatformConfig
from gateway.platforms.api_server import (
    APIServerAdapter,
    cors_middleware,
    security_headers_middleware,
)


def _make_adapter(api_key: str = "sk-secret") -> APIServerAdapter:
    return APIServerAdapter(PlatformConfig(enabled=True, extra={"key": api_key}))


def _create_voice_app(adapter: APIServerAdapter) -> web.Application:
    mws = [mw for mw in (cors_middleware, security_headers_middleware) if mw is not None]
    app = web.Application(middlewares=mws)
    app.router.add_post("/v1/voice/route", adapter._handle_voice_route)
    return app


def _auth_headers(extra: dict | None = None) -> dict:
    headers = {"Authorization": "Bearer sk-secret"}
    if extra:
        headers.update(extra)
    return headers


@pytest.mark.asyncio
async def test_voice_route_requires_auth():
    adapter = _make_adapter()
    app = _create_voice_app(adapter)

    async with TestClient(TestServer(app)) as cli:
        resp = await cli.post("/v1/voice/route", json={"transcript": "hello"})

    assert resp.status == 401


@pytest.mark.asyncio
async def test_voice_route_rejects_missing_transcript():
    adapter = _make_adapter()
    app = _create_voice_app(adapter)

    async with TestClient(TestServer(app)) as cli:
        resp = await cli.post(
            "/v1/voice/route",
            json={"device_id": "dev-1"},
            headers=_auth_headers(),
        )
        assert resp.status == 400
        data = await resp.json()

    assert "transcript" in data["error"]["message"]


@pytest.mark.asyncio
async def test_voice_route_returns_ha_native_decision():
    adapter = _make_adapter()
    app = _create_voice_app(adapter)

    async with TestClient(TestServer(app)) as cli:
        resp = await cli.post(
            "/v1/voice/route",
            json={"transcript": "what time is it", "device_id": "dev-1"},
            headers=_auth_headers({"X-Hermes-Session-Key": "ha-voice:dev-1"}),
        )
        assert resp.status == 200
        data = await resp.json()

    assert data["object"] == "hermes.voice_route"
    assert data["route"] == "ha_native"
    assert data["native_handoff"] is True
    assert data["speech"] == ""
    assert data["session_key"] == "ha-voice:dev-1"


@pytest.mark.asyncio
async def test_voice_route_kanban_creates_orchestrator_assigned_task(tmp_path, monkeypatch):
    db_path = tmp_path / "kanban.db"
    monkeypatch.setenv("HERMES_KANBAN_DB", str(db_path))

    adapter = _make_adapter()
    monkeypatch.setattr(
        adapter,
        "_voice_kanban_orchestrator_assignee",
        lambda: "kanban-orchestrator",
    )
    app = _create_voice_app(adapter)

    async with TestClient(TestServer(app)) as cli:
        resp = await cli.post(
            "/v1/voice/route",
            json={
                "transcript": "investigate why Voice PE latency is high and fix it",
                "device_id": "voice-dev",
            },
            headers=_auth_headers({"X-Hermes-Session-Key": "ha-voice:voice-dev"}),
        )
        assert resp.status == 200
        data = await resp.json()

    assert data["route"] == "kanban"
    assert data["task_id"]
    assert "background" in data["speech"].lower()

    from hermes_cli import kanban_db as kb

    conn = kb.connect(db_path=db_path)
    try:
        task = kb.get_task(conn, data["task_id"])
        assert task is not None
        assert task.status == "ready"
        assert task.assignee == "kanban-orchestrator"
        assert "Voice PE" in task.body
        assert "Original transcript" in task.body
        assert "ha-voice:voice-dev" in task.body
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_voice_route_kanban_without_orchestrator_falls_back_to_triage(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "kanban.db"
    monkeypatch.setenv("HERMES_KANBAN_DB", str(db_path))

    adapter = _make_adapter()
    monkeypatch.setattr(adapter, "_voice_kanban_orchestrator_assignee", lambda: None)
    app = _create_voice_app(adapter)

    async with TestClient(TestServer(app)) as cli:
        resp = await cli.post(
            "/v1/voice/route",
            json={
                "transcript": "investigate why Voice PE latency is high and fix it",
                "device_id": "voice-dev",
            },
            headers=_auth_headers({"X-Hermes-Session-Key": "ha-voice:voice-dev"}),
        )
        assert resp.status == 200
        data = await resp.json()

    from hermes_cli import kanban_db as kb

    conn = kb.connect(db_path=db_path)
    try:
        task = kb.get_task(conn, data["task_id"])
        assert task is not None
        assert task.status == "triage"
        assert task.assignee is None
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_voice_route_hil_records_blocked_task_without_execution(tmp_path, monkeypatch):
    db_path = tmp_path / "kanban.db"
    monkeypatch.setenv("HERMES_KANBAN_DB", str(db_path))

    adapter = _make_adapter()
    adapter._run_agent = AsyncMock()  # must not be called for HIL route
    app = _create_voice_app(adapter)

    async with TestClient(TestServer(app)) as cli:
        resp = await cli.post(
            "/v1/voice/route",
            json={"transcript": "delete the production database"},
            headers=_auth_headers({"X-Hermes-Session-Key": "ha-voice:danger"}),
        )
        assert resp.status == 200
        data = await resp.json()

    assert data["route"] == "hil"
    assert data["requires_hil"] is True
    assert data["task_id"]
    adapter._run_agent.assert_not_called()

    from hermes_cli import kanban_db as kb

    conn = kb.connect(db_path=db_path)
    try:
        task = kb.get_task(conn, data["task_id"])
        assert task is not None
        assert task.status == "blocked"
        assert "No external/destructive/authority-sensitive action was executed" in task.body
        kb.recompute_ready(conn)
        task = kb.get_task(conn, data["task_id"])
        assert task is not None
        assert task.status == "blocked"
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_voice_route_fast_agent_returns_agent_speech(monkeypatch):
    adapter = _make_adapter()

    async def fake_run_agent(**kwargs):
        assert kwargs["user_message"] == "explain latency simply"
        assert kwargs["gateway_session_key"] == "ha-voice:test"
        return (
            {"final_response": "Latency is the delay before a system responds."},
            {"total_tokens": 7},
        )

    monkeypatch.setattr(adapter, "_run_agent", fake_run_agent)
    app = _create_voice_app(adapter)

    async with TestClient(TestServer(app)) as cli:
        resp = await cli.post(
            "/v1/voice/route",
            json={"transcript": "explain latency simply", "conversation_id": "conv-1"},
            headers=_auth_headers({"X-Hermes-Session-Key": "ha-voice:test"}),
        )
        assert resp.status == 200
        data = await resp.json()

    assert data["route"] == "fast_agent"
    assert data["speech"] == "Latency is the delay before a system responds."
    assert data["usage"] == {"total_tokens": 7}
