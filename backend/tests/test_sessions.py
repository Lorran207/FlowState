import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_pomodoro_session_and_journal(client: AsyncClient, auth_headers: dict):
    # Start Session
    start_res = await client.post("/sessions", json={}, headers=auth_headers)
    assert start_res.status_code == 201
    session = start_res.json()
    assert session["completed"] is False
    session_id = session["id"]

    # Prevent starting multiple concurrent active sessions
    dup_res = await client.post("/sessions", json={}, headers=auth_headers)
    assert dup_res.status_code == 400

    # Complete Session (duration 25 min -> 15 XP)
    complete_res = await client.post(
        f"/sessions/{session_id}/complete",
        json={"duration_min": 25},
        headers=auth_headers,
    )
    assert complete_res.status_code == 200
    assert complete_res.json()["completed"] is True
    assert complete_res.json()["duration_min"] == 25

    # Create Journal entry (5 XP)
    journal_res = await client.post(
        "/journal",
        json={
            "session_id": session_id,
            "content": "Aprendi como estruturar camadas no FastAPI e SQLAlchemy.",
        },
        headers=auth_headers,
    )
    assert journal_res.status_code == 201
    assert journal_res.json()["session_id"] == session_id

    # Check Dashboard stats: 15 (pomodoro) + 5 (journal) = 20 XP
    dash_res = await client.get("/dashboard", headers=auth_headers)
    assert dash_res.status_code == 200
    stats = dash_res.json()["stats"]
    assert stats["xp_total"] == 20
    assert stats["streak"] == 1
    assert dash_res.json()["weekly_minutes"] == 25
