from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Commit,
    JournalEntry,
    StudySession,
    Task,
    TaskStatus,
    User,
    UserStats,
    XPEvent,
)
from app.schemas import TaskUpdate


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_github_id(self, github_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.github_id == github_id))
        return result.scalar_one_or_none()

    async def get_github_connected(self) -> list[User]:
        result = await self.db.execute(
            select(User).where(
                User.github_access_token.is_not(None),
                User.github_username.is_not(None),
            )
        )
        return list(result.scalars().all())

    async def update(self, user: User) -> User:
        await self.db.commit()
        await self.db.refresh(user)
        return user


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, task: Task) -> Task:
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_by_id(self, task_id: int, user_id: int) -> Task | None:
        result = await self.db.execute(
            select(Task).where(and_(Task.id == task_id, Task.user_id == user_id))
        )
        return result.scalar_one_or_none()

    async def get_all_by_user(self, user_id: int) -> list[Task]:
        result = await self.db.execute(
            select(Task).where(Task.user_id == user_id).order_by(Task.status, Task.position)
        )
        return list(result.scalars().all())

    async def get_by_status(self, user_id: int, status: TaskStatus) -> list[Task]:
        result = await self.db.execute(
            select(Task)
            .where(and_(Task.user_id == user_id, Task.status == status))
            .order_by(Task.position)
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

    async def reorder(self, tasks: list[Task]) -> None:
        for i, task in enumerate(tasks):
            task.position = i
        await self.db.commit()

    async def get_daily_completed_counts(
        self, user_id: int, since: datetime
    ) -> list[tuple[str, int]]:
        day = func.date(Task.completed_at)
        result = await self.db.execute(
            select(day, func.count(Task.id))
            .where(
                and_(
                    Task.user_id == user_id,
                    Task.completed_at.is_not(None),
                    Task.completed_at >= since,
                )
            )
            .group_by(day)
        )
        return [(str(row[0]), int(row[1])) for row in result.all()]


class StudySessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, session: StudySession) -> StudySession:
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_by_id(self, session_id: int, user_id: int) -> StudySession | None:
        result = await self.db.execute(
            select(StudySession).where(
                and_(StudySession.id == session_id, StudySession.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_active_by_user(self, user_id: int) -> StudySession | None:
        result = await self.db.execute(
            select(StudySession)
            .where(and_(StudySession.user_id == user_id, StudySession.completed == False))
            .order_by(StudySession.started_at.desc())
        )
        return result.scalar_one_or_none()

    async def get_recent_by_user(self, user_id: int, limit: int = 10) -> list[StudySession]:
        result = await self.db.execute(
            select(StudySession)
            .where(StudySession.user_id == user_id)
            .order_by(StudySession.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_weekly_minutes(self, user_id: int) -> int:
        week_ago = datetime.now(UTC) - timedelta(days=7)
        result = await self.db.execute(
            select(func.coalesce(func.sum(StudySession.duration_min), 0)).where(
                and_(
                    StudySession.user_id == user_id,
                    StudySession.completed == True,
                    StudySession.started_at >= week_ago,
                )
            )
        )
        return result.scalar() or 0

    async def get_daily_stats(self, user_id: int, since: datetime) -> list[tuple[str, int, int]]:
        """Retorna (dia, nº de sessões, minutos) das sessões concluídas desde `since`."""
        day = func.date(StudySession.ended_at)
        result = await self.db.execute(
            select(
                day,
                func.count(StudySession.id),
                func.coalesce(func.sum(StudySession.duration_min), 0),
            )
            .where(
                and_(
                    StudySession.user_id == user_id,
                    StudySession.completed == True,
                    StudySession.ended_at >= since,
                )
            )
            .group_by(day)
        )
        return [(str(row[0]), int(row[1]), int(row[2] or 0)) for row in result.all()]

    async def get_in_period(
        self, user_id: int, since: datetime, limit: int = 50
    ) -> list[StudySession]:
        result = await self.db.execute(
            select(StudySession)
            .where(
                and_(
                    StudySession.user_id == user_id,
                    StudySession.completed == True,
                    StudySession.ended_at >= since,
                )
            )
            .order_by(StudySession.ended_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class JournalRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, entry: JournalEntry) -> JournalEntry:
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def get_by_session(self, session_id: int) -> JournalEntry | None:
        result = await self.db.execute(
            select(JournalEntry).where(JournalEntry.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_daily_counts(self, user_id: int, since: datetime) -> list[tuple[str, int]]:
        day = func.date(JournalEntry.created_at)
        result = await self.db.execute(
            select(day, func.count(JournalEntry.id))
            .where(and_(JournalEntry.user_id == user_id, JournalEntry.created_at >= since))
            .group_by(day)
        )
        return [(str(row[0]), int(row[1])) for row in result.all()]

    async def get_in_period(
        self, user_id: int, since: datetime, limit: int = 50
    ) -> list[JournalEntry]:
        result = await self.db.execute(
            select(JournalEntry)
            .where(and_(JournalEntry.user_id == user_id, JournalEntry.created_at >= since))
            .order_by(JournalEntry.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


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


class CommitRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_existing_shas(self, user_id: int, shas: list[str]) -> set[str]:
        if not shas:
            return set()
        result = await self.db.execute(
            select(Commit.sha).where(and_(Commit.user_id == user_id, Commit.sha.in_(shas)))
        )
        return set(result.scalars().all())

    async def create_many(self, commits: list[Commit]) -> list[Commit]:
        self.db.add_all(commits)
        await self.db.commit()
        for commit in commits:
            await self.db.refresh(commit)
        return commits

    async def count_by_user(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count(Commit.id)).where(Commit.user_id == user_id)
        )
        return result.scalar() or 0

    async def get_recent(self, user_id: int, limit: int = 10) -> list[Commit]:
        result = await self.db.execute(
            select(Commit)
            .where(Commit.user_id == user_id)
            .order_by(Commit.committed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_daily_counts(self, user_id: int, since: datetime) -> list[tuple[str, int]]:
        day = func.date(Commit.committed_at)
        result = await self.db.execute(
            select(day, func.count(Commit.id))
            .where(and_(Commit.user_id == user_id, Commit.committed_at >= since))
            .group_by(day)
        )
        return [(str(row[0]), int(row[1])) for row in result.all()]

    async def get_in_period(
        self, user_id: int, since: datetime, limit: int = 50
    ) -> list[Commit]:
        result = await self.db.execute(
            select(Commit)
            .where(and_(Commit.user_id == user_id, Commit.committed_at >= since))
            .order_by(Commit.committed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class UserStatsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, user_id: int) -> UserStats:
        result = await self.db.execute(select(UserStats).where(UserStats.user_id == user_id))
        stats = result.scalar_one_or_none()
        if not stats:
            stats = UserStats(user_id=user_id, xp_total=0, level=1, streak=0, longest_streak=0)
            self.db.add(stats)
            await self.db.commit()
            await self.db.refresh(stats)
        return stats

    async def add_xp(self, user_id: int, amount: int) -> UserStats:
        stats = await self.get_or_create(user_id)
        stats.xp_total += amount
        stats.level = (stats.xp_total // 100) + 1
        await self.db.commit()
        await self.db.refresh(stats)
        return stats

    async def update_streak(self, user_id: int) -> UserStats:
        stats = await self.get_or_create(user_id)
        now_dt = datetime.now(UTC)
        today = now_dt.date()

        if stats.last_active_date:
            last_date = stats.last_active_date.date()
            if last_date == today:
                return stats
            elif last_date == today - timedelta(days=1):
                stats.streak += 1
            else:
                stats.streak = 1
            stats.longest_streak = max(stats.longest_streak, stats.streak)
        else:
            stats.streak = 1
            stats.longest_streak = 1

        stats.last_active_date = now_dt
        await self.db.commit()
        await self.db.refresh(stats)
        return stats
