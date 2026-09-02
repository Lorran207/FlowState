from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    activity_router,
    dashboard_router,
    github_router,
    journal_router,
    session_router,
    task_router,
)
from app.api.routes import router as auth_router
from app.core.config import get_settings
from app.core.database import async_session_maker, init_db
from app.services import CommitSyncService

settings = get_settings()


async def sync_all_users_commits() -> None:
    """Job em background: sincroniza commits do GitHub de todos os usuários conectados."""
    try:
        async with async_session_maker() as db:
            await CommitSyncService(db, settings).sync_all_users()
    except Exception:
        pass  # sync é best-effort; falhas não derrubam a API


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        sync_all_users_commits,
        "interval",
        minutes=settings.github_sync_interval_minutes,
        id="github_commit_sync",
        replace_existing=True,
    )
    scheduler.start()

    yield

    scheduler.shutdown(wait=False)


app = FastAPI(title="FlowState API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(task_router)
app.include_router(session_router)
app.include_router(journal_router)
app.include_router(dashboard_router)
app.include_router(github_router)
app.include_router(activity_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
