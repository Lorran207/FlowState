import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Register
    res = await client.post(
        "/auth/register",
        json={"email": "user1@example.com", "name": "User One", "password": "password123"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "user1@example.com"
    assert data["name"] == "User One"
    assert "id" in data

    # Login
    login_res = await client.post(
        "/auth/login",
        json={"email": "user1@example.com", "password": "password123"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data
    assert login_data["user"]["email"] == "user1@example.com"

    # Get Me
    token = login_data["access_token"]
    me_res = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "User One"


@pytest.mark.asyncio
async def test_duplicate_register(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={"email": "dupe@example.com", "name": "Dupe", "password": "password123"},
    )
    res = await client.post(
        "/auth/register",
        json={"email": "dupe@example.com", "name": "Dupe", "password": "password123"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={"email": "refresh@example.com", "name": "Refresh", "password": "password123"},
    )
    login_res = await client.post(
        "/auth/login",
        json={"email": "refresh@example.com", "password": "password123"},
    )
    refresh_token = login_res.json()["refresh_token"]

    ref_res = await client.post(f"/auth/refresh?refresh_token={refresh_token}")
    assert ref_res.status_code == 200
    assert "access_token" in ref_res.json()
