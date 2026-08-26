from typing import Optional, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import User, Task, StudySession, JournalEntry, XPEvent, UserStats, TaskStatus
from app.schemas import TaskCreate, TaskUpdate, StudySessionCreate, JournalEntryCreate


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, task: Task) -> Task:
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_by_id(self, task_id: int, user_id: int) -> Optional[Task]:
        result = await self.db.execute(
            select(Task).where(and_(Task.id == task_id, Task.user_id == user_id))
        )
        return result.scalar_one_or_none()

    async def get_all_by_user(self, user_id: int) -> List[Task]:
        result = await self.db.execute(
            select(Task).where(Task.user_id == user_id).order_by(Task.status, Task.position)
        )
        return list(result.scalars().all())

    async def get_by_status(self, user_id: int, status: TaskStatus) -> List[Task]:
        result = await self.db.execute(
            select(Task).where(and_(Task.user_id == user_id, Task.status == status)).order_by(Task.position)
        )
        return list(result.scalars().all())

    async def update(self, task: Task, data: TaskUpdate) -> Task:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(task, field, value)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        await self.db.delete(task)
        await self.db.commit()

    async def reorder(self, tasks: List[Task]) -> None:
        for i, task in enumerate(tasks):
            task.position = i
        await self.db.commit()


class StudySessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, session: StudySession) -> StudySession:
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_by_id(self, session_id: int, user_id: int) -> Optional[StudySession]:
        result = await self.db.execute(
            select(StudySession).where(and_(StudySession.id == session_id, StudySession.user_id == user_id))
        )
        return result.scalar_one_or_none()

    async def get_active_by_user(self, user_id: int) -> Optional[StudySession]:
        result = await self.db.execute(
            select(StudySession)
            .where(and_(StudySession.user_id == user_id, StudySession.completed == False))
            .order_by(StudySession.started_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_recent_by_user(self, user_id: int, limit: int = 10) -> List[StudySession]:
        result = await self.db.execute(
            select(StudySession)
            .where(StudySession.user_id == user_id)
            .order_by(StudySession.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_weekly_minutes(self, user_id: int) -> int:
        from datetime import datetime, timedelta, timezone
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        result = await self.db.execute(
            select(func.coalesce(func.sum(StudySession.duration_min), 0))
            .where(and_(
                StudySession.user_id == user_id,
                StudySession.completed == True,
                StudySession.started_at >= week_ago
            ))
        )
        return result.scalar() or 0


class JournalRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, entry: JournalEntry) -> JournalEntry:
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def get_by_session(self, session_id: int) -> Optional[JournalEntry]:
        result = await self.db.execute(
            select(JournalEntry).where(JournalEntry.session_id == session_id)
        )
        return result.scalar_one_or_none()


class XPRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, event: XPEvent) -> XPEvent:
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_total_xp(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.sum(XPEvent.amount), 0)).where(XPEvent.user_id == user_id)
        )
        return result.scalar() or 0


class UserStatsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, user_id: int) -> UserStats:
        result = await self.db.execute(select(UserStats).where(UserStats.user_id == user_id))
        stats = result.scalar_one_or_none()
        if not stats:
            stats = UserStats(user_id=user_id)
            self.db.add(stats)
            await self.db.commit()
            await self.db.refresh(stats)
        return stats

    async def update_streak(self, user_id: int) -> UserStats:
        from datetime import datetime, timezone
        stats = await self.get_or_create(user_id)
        today = datetime.now(timezone.utc).date()

        if stats.last_active_date:
            last_date = stats.last_active_date.date()
            if last_date == today:
                return stats
            elif last_date == today - datetime.resolution:
                stats.streak += 1
            else:
                stats.streak = 1
            stats.longest_streak = max(stats.longest_streak, stats.streak)
        else:
            stats.streak = 1
            stats.longest_streak = 1

        stats.last_active_date = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(stats)
        return stats