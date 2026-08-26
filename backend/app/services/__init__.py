from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import (
    UserRepository, TaskRepository, StudySessionRepository,
    JournalRepository, XPRepository, UserStatsRepository
)
from app.models import User, Task, StudySession, JournalEntry, XPEvent, TaskStatus, XPSource
from app.schemas import TaskCreate, TaskUpdate, StudySessionCreate, JournalEntryCreate
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token


XP_VALUES = {
    XPSource.TASK: 10,
    XPSource.POMODORO: 15,
    XPSource.JOURNAL: 5,
}

XP_PER_LEVEL = 100


class AuthService:
    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)
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
        return await self.user_repo.create(user)

    async def login(self, email: str, password: str) -> Optional[dict]:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            return None

        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user,
        }

    async def refresh_token(self, refresh_token: str) -> Optional[dict]:
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
        return {"access_token": access_token, "refresh_token": new_refresh}


class TaskService:
    def __init__(self, db: AsyncSession):
        self.task_repo = TaskRepository(db)
        self.db = db

    async def create(self, user_id: int, data: TaskCreate) -> Task:
        max_pos_result = await self.db.execute(
            select(func.max(Task.position)).where(and_(Task.user_id == user_id, Task.status == TaskStatus.BACKLOG))
        )
        max_pos = max_pos_result.scalar() or -1

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

    async def get_by_id(self, task_id: int, user_id: int) -> Optional[Task]:
        return await self.task_repo.get_by_id(task_id, user_id)

    async def update(self, task: Task, data: TaskUpdate) -> Task:
        return await self.task_repo.update(task, data)

    async def delete(self, task: Task) -> None:
        await self.task_repo.delete(task)

    async def reorder_by_status(self, user_id: int, status: TaskStatus, task_ids: list[int]) -> list[Task]:
        tasks = []
        for i, task_id in enumerate(task_ids):
            task = await self.task_repo.get_by_id(task_id, user_id)
            if task and task.status == status:
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

        session.ended_at = datetime.now(timezone.utc)
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

        await self.stats_repo.update_streak(user_id)
        await self._update_level(user_id)

        return session

    async def get_recent(self, user_id: int, limit: int = 10) -> list[StudySession]:
        return await self.session_repo.get_recent_by_user(user_id, limit)

    async def get_weekly_minutes(self, user_id: int) -> int:
        return await self.session_repo.get_weekly_minutes(user_id)

    async def _update_level(self, user_id: int) -> None:
        total_xp = await self.xp_repo.get_total_xp(user_id)
        stats = await self.stats_repo.get_or_create(user_id)
        new_level = (total_xp // XP_PER_LEVEL) + 1
        if new_level != stats.level:
            stats.level = new_level
            await self.db.commit()


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


from sqlalchemy import select, func, and_