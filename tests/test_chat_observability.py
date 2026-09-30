from __future__ import annotations

import json
import asyncio
import re
from pathlib import Path

import httpx

from app import logging_config
from app.main import app
from app.pii import hash_user_id


def test_chat_response_log_exposes_quality_for_dashboard(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/chat",
                json={
                    "user_id": "student-01",
                    "session_id": "session-01",
                    "feature": "qa",
                    "message": "Explain observability",
                },
            )

    response = asyncio.run(send_request())

    assert response.status_code == 200
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    response_event = next(event for event in events if event["event"] == "response_sent")
    assert response_event["quality_score"] == response.json()["quality_score"]
    assert response_event["ttft_ms"] == response.json()["ttft_ms"]
    assert response_event["tool_name"] == "retrieval"
    assert response_event["tool_success"] is True


def test_request_context_headers_and_pii(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)
    monkeypatch.setenv("APP_ENV", "test")

    async def send_requests():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            responses = []
            for index in range(2):
                responses.append(await client.post(
                    "/chat",
                    headers={"x-request-id": "req-1234abcd"} if index == 0 else {},
                    json={
                        "user_id": f"student-{index}",
                        "session_id": f"session-{index}",
                        "feature": "qa",
                        "message": "student@example.com 012345678901 4111-1111-1111-1111",
                    },
                ))
            return responses

    responses = asyncio.run(send_requests())
    contents = log_path.read_text(encoding="utf-8")
    events = [json.loads(line) for line in contents.splitlines()]
    ids = []
    for index, response in enumerate(responses):
        assert response.status_code == 200
        request_id = response.headers["x-request-id"]
        ids.append(request_id)
        assert re.fullmatch(r"req-[0-9a-f]{8}", request_id)
        assert response.json()["correlation_id"] == request_id
        assert float(response.headers["x-response-time-ms"]) >= 0
        request_events = [event for event in events if event.get("correlation_id") == request_id]
        assert {event["event"] for event in request_events} >= {"request_received", "response_sent"}
        for event in request_events:
            assert event["user_id_hash"] == hash_user_id(f"student-{index}")
            assert event["session_id"] == f"session-{index}"
            assert event["feature"] == "qa"
            assert event["model"]
            assert event["env"] == "test"
    assert ids[0] == "req-1234abcd"
    assert ids[0] != ids[1]
    for pii in ("student@example.com", "012345678901", "4111-1111-1111-1111"):
        assert pii not in contents
