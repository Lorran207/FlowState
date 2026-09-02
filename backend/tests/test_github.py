from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient

from app.core.config import Settings, get_settings
from app.core.security import create_oauth_state
from app.main import app

GH_USER = {
    "id": 12345,
    "login": "octocat",
    "name": "Octo Cat",
    "email": "octo@example.com",
}

PUSH_EVENTS = [
    {
        "type": "PushEvent",
        "repo": {"name": "octocat/gymnutri"},
        "created_at": "2026-09-02T10:00:00Z",
        "payload": {
            "commits": [
                {"sha": "a" * 40, "message": "feat: adiciona treino semanal"},
                {"sha": "b" * 40, "message": "fix: corrige cálculo de IMC"},
            ]
        },
    },
    {"type": "WatchEvent", "repo": {"name": "octocat/ops"}, "created_at": "2026-09-02T11:00:00Z"},
]


@pytest.fixture
def github_settings():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        github_client_id="test-client-id",
        github_client_secret="test-client-secret",
        github_callback_url="http://localhost:8000/auth/github/callback",
        frontend_url="http://localhost:5173",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    yield settings
    app.dependency_overrides.pop(get_settings, None)


@pytest.fixture
def mock_github_oauth(monkeypatch):
    async def fake_exchange_code(code: str, settings: Settings) -> str | None:
        return "gh-token-123"

    async def fake_fetch_user(access_token: str) -> dict | None:
        return GH_USER

    async def fake_fetch_primary_email(access_token: str) -> str | None:
        return GH_USER["email"]

    monkeypatch.setattr("app.services.github_exchange_code", fake_exchange_code)
    monkeypatch.setattr("app.services.github_fetch_user", fake_fetch_user)
    monkeypatch.setattr("app.services.github_fetch_primary_email", fake_fetch_primary_email)


@pytest.fixture
def mock_github_events(monkeypatch):
    async def fake_fetch_events(username: str, access_token: str, per_page: int = 100):
        return PUSH_EVENTS

    monkeypatch.setattr("app.services.github_fetch_events", fake_fetch_events)


async def _create_oauth_user(client: AsyncClient) -> dict:
    """Cria usuário via fluxo OAuth completo (mockado) e retorna tokens."""
    res = await client.get(
        "/auth/github/callback",
        params={"code": "fake-code", "state": create_oauth_state()},
    )
    assert res.status_code == 302
    location = res.headers["location"]
    params = parse_qs(urlparse(location).query)
    assert "access_token" in params
    return {k: v[0] for k, v in params.items()}


@pytest.mark.asyncio
async def test_github_status_disconnected_and_sync_guard(client: AsyncClient, auth_headers: dict):
    res = await client.get("/github/status", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["connected"] is False
    assert data["username"] is None
    assert data["commit_count"] == 0

    sync_res = await client.post("/github/sync", headers=auth_headers)
    assert sync_res.status_code == 400


@pytest.mark.asyncio
async def test_github_authorize_url(client: AsyncClient, github_settings):
    res = await client.get("/auth/github/authorize")
    assert res.status_code == 200
    url = res.json()["url"]
    assert url.startswith("https://github.com/login/oauth/authorize?")
    params = parse_qs(urlparse(url).query)
    assert params["client_id"] == ["test-client-id"]
    assert "state" in params


@pytest.mark.asyncio
async def test_github_authorize_not_configured(client: AsyncClient):
    res = await client.get("/auth/github/authorize")
    assert res.status_code == 503


@pytest.mark.asyncio
async def test_github_callback_creates_user(
    client: AsyncClient, github_settings, mock_github_oauth
):
    tokens = await _create_oauth_user(client)

    me = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "octo@example.com"
    assert me.json()["github_username"] == "octocat"

    # Usuário criado via GitHub não tem senha -> login por senha falha
    login_res = await client.post(
        "/auth/login", json={"email": "octo@example.com", "password": "qualquer1"}
    )
    assert login_res.status_code == 401

    # E não pode desconectar sem ter senha
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    disconnect_res = await client.delete("/github/disconnect", headers=headers)
    assert disconnect_res.status_code == 400

    status_res = await client.get("/github/status", headers=headers)
    assert status_res.json()["connected"] is True
    assert status_res.json()["username"] == "octocat"


@pytest.mark.asyncio
async def test_github_callback_links_existing_email(
    client: AsyncClient, github_settings, mock_github_oauth
):
    await client.post(
        "/auth/register",
        json={"email": "octo@example.com", "name": "Octo", "password": "password123"},
    )
    login_res = await client.post(
        "/auth/login", json={"email": "octo@example.com", "password": "password123"}
    )
    user_id = login_res.json()["user"]["id"]

    tokens = await _create_oauth_user(client)
    me = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    # Mesmo usuário, agora com GitHub vinculado
    assert me.json()["id"] == user_id
    assert me.json()["github_username"] == "octocat"

    # Desconectar funciona porque a conta tem senha
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert (await client.delete("/github/disconnect", headers=headers)).status_code == 204
    assert (
        await client.get("/github/status", headers=headers)
    ).json()["connected"] is False


@pytest.mark.asyncio
async def test_github_connect_flow_with_logged_user(
    client: AsyncClient, github_settings, mock_github_oauth, auth_headers: dict
):
    # Usuário logado ("tester@example.com") conecta um GitHub com outro e-mail.
    # Como o redirect do navegador não carrega header Authorization, a rota
    # aceita o access token no query param `t` para embutir o uid no state.
    token = auth_headers["Authorization"].split(" ")[1]
    res = await client.get("/auth/github/authorize", params={"t": token})
    assert res.status_code == 200
    state = parse_qs(urlparse(res.json()["url"]).query)["state"][0]

    cb = await client.get(
        "/auth/github/callback", params={"code": "fake-code", "state": state}
    )
    assert cb.status_code == 302
    assert "access_token" in parse_qs(urlparse(cb.headers["location"]).query)

    status_res = await client.get("/github/status", headers=auth_headers)
    assert status_res.json()["connected"] is True
    assert status_res.json()["username"] == "octocat"


@pytest.mark.asyncio
async def test_github_callback_invalid_state(client: AsyncClient, github_settings):
    res = await client.get(
        "/auth/github/callback", params={"code": "x", "state": "state-ruim"}
    )
    assert res.status_code == 302
    assert "error" in parse_qs(urlparse(res.headers["location"]).query)


@pytest.mark.asyncio
async def test_commit_sync_dedupe_feed_and_heatmap(
    client: AsyncClient, github_settings, mock_github_oauth, mock_github_events
):
    tokens = await _create_oauth_user(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Primeiro sync importa 2 commits
    sync1 = await client.post("/github/sync", headers=headers)
    assert sync1.status_code == 200
    assert sync1.json() == {"new_commits": 2, "total_commits": 2}

    # Segundo sync não duplica (dedupe por SHA)
    sync2 = await client.post("/github/sync", headers=headers)
    assert sync2.json() == {"new_commits": 0, "total_commits": 2}

    commits = await client.get("/github/commits", headers=headers)
    assert commits.status_code == 200
    assert len(commits.json()) == 2
    assert commits.json()[0]["repo_name"] == "octocat/gymnutri"
    assert commits.json()[0]["url"].startswith("https://github.com/octocat/gymnutri/commit/")

    # Feed mostra o commit como evidência de estudo
    feed = await client.get("/activity/feed", headers=headers)
    assert feed.status_code == 200
    commit_items = [i for i in feed.json() if i["type"] == "commit"]
    assert len(commit_items) == 2
    assert commit_items[0]["description"]

    # Heatmap marca o dia com atividade
    heatmap = await client.get("/activity/heatmap?days=30", headers=headers)
    assert heatmap.status_code == 200
    days = heatmap.json()
    assert len(days) == 30
    day_2026_09_02 = next(d for d in days if d["date"] == "2026-09-02")
    assert day_2026_09_02["count"] == 2


@pytest.mark.asyncio
async def test_feed_mixed_activity_order(
    client: AsyncClient, github_settings, mock_github_oauth, mock_github_events
):
    tokens = await _create_oauth_user(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    await client.post("/github/sync", headers=headers)

    session = (
        await client.post("/sessions", json={}, headers=headers)
    ).json()
    await client.post(
        f"/sessions/{session['id']}/complete", json={"duration_min": 25}, headers=headers
    )
    await client.post(
        "/journal",
        json={"session_id": session["id"], "content": "Aprendi OAuth2 na prática"},
        headers=headers,
    )

    feed = (await client.get("/activity/feed", headers=headers)).json()
    types = [item["type"] for item in feed]
    assert "pomodoro" in types
    assert "journal" in types
    assert types.count("commit") == 2
    pomodoro = next(i for i in feed if i["type"] == "pomodoro")
    assert pomodoro["title"] == "Pomodoro de 25 min concluído"


@pytest.mark.asyncio
async def test_heatmap_empty_days_filled(client: AsyncClient, auth_headers: dict):
    res = await client.get("/activity/heatmap?days=7", headers=auth_headers)
    assert res.status_code == 200
    days = res.json()
    assert len(days) == 7
    assert all(d["count"] == 0 and d["minutes"] == 0 for d in days)
