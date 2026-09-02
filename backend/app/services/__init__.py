from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import (
    create_access_token,
    create_oauth_state,
    create_refresh_token,
    get_password_hash,
    verify_oauth_state,
    verify_password,
)
from app.models import (
    Commit,
    JournalEntry,
    StudySession,
    Task,
    TaskStatus,
    User,
    XPEvent,
    XPSource,
)
from app.repositories import (
    CommitRepository,
    JournalRepository,
    StudySessionRepository,
    TaskRepository,
    UserRepository,
    UserStatsRepository,
    XPRepository,
)
from app.schemas import JournalEntryCreate, StudySessionCreate, TaskCreate, TaskUpdate

XP_VALUES = {
    XPSource.TASK: 10,
    XPSource.POMODORO: 15,
    XPSource.JOURNAL: 5,
}

XP_PER_LEVEL = 100

GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"


def _gh_headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def github_exchange_code(code: str, settings: Settings) -> str | None:
    """Troca o `code` do OAuth por um access token do GitHub."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": settings.github_callback_url,
                },
                headers={"Accept": "application/json"},
            )
        if resp.status_code != 200:
            return None
        token = resp.json().get("access_token")
        return str(token) if token else None
    except Exception:
        return None


async def github_fetch_user(access_token: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(f"{GITHUB_API_URL}/user", headers=_gh_headers(access_token))
        if resp.status_code != 200:
            return None
        return dict(resp.json())
    except Exception:
        return None


async def github_fetch_primary_email(access_token: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{GITHUB_API_URL}/user/emails", headers=_gh_headers(access_token)
            )
        if resp.status_code != 200:
            return None
        emails = resp.json()
        for entry in emails:
            if entry.get("primary") and entry.get("verified"):
                return str(entry.get("email"))
        return str(emails[0].get("email")) if emails else None
    except Exception:
        return None


async def github_fetch_events(
    username: str, access_token: str, per_page: int = 100
) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{GITHUB_API_URL}/users/{username}/events",
                params={"per_page": per_page},
                headers=_gh_headers(access_token),
            )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return list(data) if isinstance(data, list) else []
    except Exception:
        return []


def _parse_gh_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)
        self.stats_repo = UserStatsRepository(db)
        self.db = db

    async def register(self, email: str, name: str, password: str) -> User:
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ValueError("Email already registered")

        user = User(
            email=email,
            name=name,
            password_hash=get_password_hash(password),
        )
        created_user = await self.user_repo.create(user)
        await self.stats_repo.get_or_create(created_user.id)
        return created_user

    async def login(self, email: str, password: str) -> dict | None:
        user = await self.user_repo.get_by_email(email)
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            return None

        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user,
        }

    async def refresh_token(self, refresh_token: str) -> dict | None:
        from app.core.security import decode_token

        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        user_id = int(payload.get("sub", 0))
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        access_token = create_access_token({"sub": str(user.id)})
        new_refresh = create_refresh_token({"sub": str(user.id)})
        return {"access_token": access_token, "refresh_token": new_refresh, "user": user}


class TaskService:
    def __init__(self, db: AsyncSession):
        self.task_repo = TaskRepository(db)
        self.xp_repo = XPRepository(db)
        self.stats_repo = UserStatsRepository(db)
        self.db = db

    async def create(self, user_id: int, data: TaskCreate) -> Task:
        max_pos_result = await self.db.execute(
            select(func.max(Task.position)).where(
                and_(Task.user_id == user_id, Task.status == TaskStatus.BACKLOG)
            )
        )
        max_pos = max_pos_result.scalar()
        if max_pos is None:
            max_pos = -1

        task = Task(
            user_id=user_id,
            title=data.title,
            description=data.description,
            status=TaskStatus.BACKLOG,
            position=max_pos + 1,
        )
        return await self.task_repo.create(task)

    async def get_all(self, user_id: int) -> list[Task]:
        return await self.task_repo.get_all_by_user(user_id)

    async def get_by_id(self, task_id: int, user_id: int) -> Task | None:
        return await self.task_repo.get_by_id(task_id, user_id)

    async def update(self, task: Task, data: TaskUpdate) -> Task:
        was_done = task.status == TaskStatus.DONE
        will_be_done = data.status == TaskStatus.DONE if data.status is not None else was_done

        if not was_done and will_be_done:
            task.completed_at = datetime.now(UTC)
            xp_event = XPEvent(
                user_id=task.user_id,
                amount=XP_VALUES[XPSource.TASK],
                source=XPSource.TASK,
            )
            await self.xp_repo.create(xp_event)
            await self.stats_repo.add_xp(task.user_id, XP_VALUES[XPSource.TASK])
            await self.stats_repo.update_streak(task.user_id)
        elif was_done and data.status is not None and data.status != TaskStatus.DONE:
            task.completed_at = None

        return await self.task_repo.update(task, data)

    async def delete(self, task: Task) -> None:
        await self.task_repo.delete(task)

    async def reorder_by_status(
        self, user_id: int, status: TaskStatus, task_ids: list[int]
    ) -> list[Task]:
        tasks = []
        for i, task_id in enumerate(task_ids):
            task = await self.task_repo.get_by_id(task_id, user_id)
            if task:
                task.status = status
                task.position = i
                tasks.append(task)
        await self.db.commit()
        for task in tasks:
            await self.db.refresh(task)
        return tasks


class StudySessionService:
    def __init__(self, db: AsyncSession):
        self.session_repo = StudySessionRepository(db)
        self.xp_repo = XPRepository(db)
        self.stats_repo = UserStatsRepository(db)
        self.task_repo = TaskRepository(db)
        self.db = db

    async def start(self, user_id: int, data: StudySessionCreate) -> StudySession:
        active = await self.session_repo.get_active_by_user(user_id)
        if active:
            raise ValueError("Already have an active session")

        session = StudySession(
            user_id=user_id,
            task_id=data.task_id,
        )
        return await self.session_repo.create(session)

    async def complete(self, session_id: int, user_id: int, duration_min: int) -> StudySession:
        session = await self.session_repo.get_by_id(session_id, user_id)
        if not session:
            raise ValueError("Session not found")
        if session.completed:
            raise ValueError("Session already completed")

        session.ended_at = datetime.now(UTC)
        session.duration_min = duration_min
        session.completed = True

        await self.db.commit()
        await self.db.refresh(session)

        xp_event = XPEvent(
            user_id=user_id,
            amount=XP_VALUES[XPSource.POMODORO],
            source=XPSource.POMODORO,
        )
        await self.xp_repo.create(xp_event)
        await self.stats_repo.add_xp(user_id, XP_VALUES[XPSource.POMODORO])
        await self.stats_repo.update_streak(user_id)

        return session

    async def get_recent(self, user_id: int, limit: int = 10) -> list[StudySession]:
        return await self.session_repo.get_recent_by_user(user_id, limit)

    async def get_weekly_minutes(self, user_id: int) -> int:
        return await self.session_repo.get_weekly_minutes(user_id)


class JournalService:
    def __init__(self, db: AsyncSession):
        self.journal_repo = JournalRepository(db)
        self.session_repo = StudySessionRepository(db)
        self.xp_repo = XPRepository(db)
        self.stats_repo = UserStatsRepository(db)
        self.db = db

    async def create(self, user_id: int, data: JournalEntryCreate) -> JournalEntry:
        session = await self.session_repo.get_by_id(data.session_id, user_id)
        if not session:
            raise ValueError("Session not found")
        if not session.completed:
            raise ValueError("Can only journal on completed sessions")

        existing = await self.journal_repo.get_by_session(data.session_id)
        if existing:
            raise ValueError("Journal entry already exists for this session")

        entry = JournalEntry(
            user_id=user_id,
            session_id=data.session_id,
            content=data.content,
        )
        await self.journal_repo.create(entry)

        xp_event = XPEvent(
            user_id=user_id,
            amount=XP_VALUES[XPSource.JOURNAL],
            source=XPSource.JOURNAL,
        )
        await self.xp_repo.create(xp_event)
        await self.stats_repo.add_xp(user_id, XP_VALUES[XPSource.JOURNAL])
        await self.stats_repo.update_streak(user_id)

        return entry


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.stats_repo = UserStatsRepository(db)
        self.session_repo = StudySessionRepository(db)
        self.task_repo = TaskRepository(db)
        self.xp_repo = XPRepository(db)
        self.db = db

    async def get_dashboard(self, user_id: int) -> dict:
        stats = await self.stats_repo.get_or_create(user_id)
        recent_sessions = await self.session_repo.get_recent_by_user(user_id, 5)
        recent_tasks = await self.task_repo.get_by_status(user_id, TaskStatus.DOING)
        weekly_minutes = await self.session_repo.get_weekly_minutes(user_id)

        return {
            "stats": {
                "xp_total": stats.xp_total,
                "level": stats.level,
                "streak": stats.streak,
                "longest_streak": stats.longest_streak,
                "last_active_date": stats.last_active_date,
            },
            "recent_sessions": recent_sessions,
            "recent_tasks": recent_tasks[:5],
            "weekly_minutes": weekly_minutes,
        }


class GitHubOAuthService:
    """Login/cadastro via OAuth2 do GitHub e vínculo de conta existente."""

    def __init__(self, db: AsyncSession, settings: Settings | None = None):
        self.user_repo = UserRepository(db)
        self.stats_repo = UserStatsRepository(db)
        self.db = db
        self.settings = settings or get_settings()

    def build_authorize_url(self, user_id: int | None = None) -> str:
        if not self.settings.github_client_id:
            raise ValueError("GitHub OAuth não configurado") from None
        params = {
            "client_id": self.settings.github_client_id,
            "redirect_uri": self.settings.github_callback_url,
            "scope": "read:user user:email",
            "state": create_oauth_state(user_id),
        }
        return f"https://github.com/login/oauth/authorize?{urlencode(params)}"

    async def handle_callback(self, code: str, state: str) -> dict:
        user_id = verify_oauth_state(state)

        gh_token = await github_exchange_code(code, self.settings)
        if not gh_token:
            raise ValueError("Falha ao trocar código por token do GitHub")

        gh_user = await github_fetch_user(gh_token)
        if not gh_user or not gh_user.get("id"):
            raise ValueError("Não foi possível obter o usuário do GitHub")

        github_id = str(gh_user["id"])
        username = gh_user.get("login") or ""
        email = gh_user.get("email") or await github_fetch_primary_email(gh_token)
        name = gh_user.get("name") or username

        existing_gh_user = await self.user_repo.get_by_github_id(github_id)

        if user_id is not None:
            # Fluxo "Conectar GitHub": usuário logado vinculando a própria conta
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                raise ValueError("Usuário da sessão não encontrado")
            if existing_gh_user and existing_gh_user.id != user.id:
                raise ValueError("Esta conta do GitHub já está vinculada a outro usuário")
            user.github_id = github_id
            user.github_username = username
            user.github_access_token = gh_token
            await self.user_repo.update(user)
        elif existing_gh_user:
            user = existing_gh_user
            user.github_username = username
            user.github_access_token = gh_token
            await self.user_repo.update(user)
        else:
            user_by_email = await self.user_repo.get_by_email(email) if email else None
            if user_by_email:
                user = user_by_email
                user.github_id = github_id
                user.github_username = username
                user.github_access_token = gh_token
                await self.user_repo.update(user)
            else:
                if not email:
                    raise ValueError("Conta do GitHub sem e-mail verificado disponível")
                user = User(
                    email=email,
                    name=name,
                    password_hash=None,
                    github_id=github_id,
                    github_username=username,
                    github_access_token=gh_token,
                )
                user = await self.user_repo.create(user)
                await self.stats_repo.get_or_create(user.id)

        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user,
        }

    async def disconnect(self, user: User) -> None:
        if not user.password_hash:
            raise ValueError("Defina uma senha antes de desconectar o GitHub")
        user.github_id = None
        user.github_username = None
        user.github_access_token = None
        await self.user_repo.update(user)


class CommitSyncService:
    """Busca commits no GitHub e persiste os novos (deduplicados por SHA)."""

    def __init__(self, db: AsyncSession, settings: Settings | None = None):
        self.commit_repo = CommitRepository(db)
        self.user_repo = UserRepository(db)
        self.db = db
        self.settings = settings or get_settings()

    async def sync_user(self, user: User) -> int:
        if not user.github_username or not user.github_access_token:
            return 0

        events = await github_fetch_events(user.github_username, user.github_access_token)
        candidates: dict[str, Commit] = {}
        for event in events:
            if event.get("type") != "PushEvent":
                continue
            repo_name = event.get("repo", {}).get("name", "")
            committed_at = _parse_gh_datetime(event.get("created_at"))
            for raw in event.get("payload", {}).get("commits", []):
                sha = raw.get("sha")
                if not sha or sha in candidates:
                    continue
                message = (raw.get("message") or "").splitlines()[0]
                candidates[sha] = Commit(
                    user_id=user.id,
                    sha=sha,
                    message=message,
                    repo_name=repo_name,
                    url=f"https://github.com/{repo_name}/commit/{sha}",
                    committed_at=committed_at,
                )

        if not candidates:
            return 0

        existing = await self.commit_repo.get_existing_shas(user.id, list(candidates.keys()))
        new_commits = [c for sha, c in candidates.items() if sha not in existing]
        if new_commits:
            await self.commit_repo.create_many(new_commits)
        return len(new_commits)

    async def sync_all_users(self) -> int:
        users = await self.user_repo.get_github_connected()
        total = 0
        for user in users:
            total += await self.sync_user(user)
        return total


class ActivityService:
    """Feed de atividades e heatmap unificando pomodoros, journals, tarefas e commits."""

    def __init__(self, db: AsyncSession, settings: Settings | None = None):
        self.session_repo = StudySessionRepository(db)
        self.journal_repo = JournalRepository(db)
        self.task_repo = TaskRepository(db)
        self.commit_repo = CommitRepository(db)
        self.db = db
        self.settings = settings or get_settings()

    async def get_feed(self, user_id: int, days: int = 14, limit: int = 50) -> list[dict]:
        since = datetime.now(UTC) - timedelta(days=days)
        items: list[dict] = []

        for session in await self.session_repo.get_in_period(user_id, since, limit):
            items.append(
                {
                    "type": "pomodoro",
                    "title": f"Pomodoro de {session.duration_min or 0} min concluído",
                    "description": None,
                    "url": None,
                    "timestamp": session.ended_at,
                }
            )
        for entry in await self.journal_repo.get_in_period(user_id, since, limit):
            items.append(
                {
                    "type": "journal",
                    "title": "Registro de aprendizado",
                    "description": entry.content,
                    "url": None,
                    "timestamp": entry.created_at,
                }
            )
        for commit in await self.commit_repo.get_in_period(user_id, since, limit):
            items.append(
                {
                    "type": "commit",
                    "title": f"Commit em {commit.repo_name}",
                    "description": commit.message,
                    "url": commit.url,
                    "timestamp": commit.committed_at,
                }
            )

        epoch = datetime.min.replace(tzinfo=UTC)
        items.sort(key=lambda item: item["timestamp"] or epoch, reverse=True)
        return items[:limit]

    async def get_heatmap(self, user_id: int, days: int = 365) -> list[dict]:
        since = datetime.now(UTC) - timedelta(days=days)
        by_day: dict[str, dict] = {}

        for day, count, minutes in await self.session_repo.get_daily_stats(user_id, since):
            entry = by_day.setdefault(day, {"count": 0, "minutes": 0})
            entry["count"] += count
            entry["minutes"] += minutes
        for day, count in await self.journal_repo.get_daily_counts(user_id, since):
            by_day.setdefault(day, {"count": 0, "minutes": 0})["count"] += count
        for day, count in await self.task_repo.get_daily_completed_counts(user_id, since):
            by_day.setdefault(day, {"count": 0, "minutes": 0})["count"] += count
        for day, count in await self.commit_repo.get_daily_counts(user_id, since):
            by_day.setdefault(day, {"count": 0, "minutes": 0})["count"] += count

        today = datetime.now(UTC).date()
        result = []
        for offset in range(days - 1, -1, -1):
            day_key = str(today - timedelta(days=offset))
            info = by_day.get(day_key, {"count": 0, "minutes": 0})
            result.append(
                {"date": day_key, "count": int(info["count"]), "minutes": int(info["minutes"])}
            )
        return result
