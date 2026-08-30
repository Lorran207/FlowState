import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_empty_dashboard(client: AsyncClient, auth_headers: dict):
    res = await client.get("/dashboard", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "stats" in data
    assert data["stats"]["xp_total"] == 0
    assert data["stats"]["level"] == 1
    assert data["stats"]["streak"] == 0
    assert data["weekly_minutes"] == 0
    assert data["recent_sessions"] == []
    assert data["recent_tasks"] == []
