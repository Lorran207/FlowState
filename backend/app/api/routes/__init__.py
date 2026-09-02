from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models import User
from app.repositories import CommitRepository, UserRepository
from app.schemas import (
    AuthorizeUrlResponse,
    CommitResponse,
    DashboardResponse,
    FeedItem,
    GitHubStatusResponse,
    HeatmapDay,
    JournalEntryCreate,
    JournalEntryResponse,
    StudySessionComplete,
    StudySessionCreate,
    StudySessionResponse,
    SyncResultResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services import (
    ActivityService,
    AuthService,
    CommitSyncService,
    DashboardService,
    GitHubOAuthService,
    JournalService,
    StudySessionService,
    TaskService,
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = int(payload.get("sub", 0))
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        user = await auth_service.register(data.email, data.name, data.password)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    result = await auth_service.login(data.email, data.password)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "token_type": "bearer",
        "user": result["user"],
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    result = await auth_service.refresh_token(refresh_token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    return {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "token_type": "bearer",
        "user": result.get("user"),
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/github/authorize", response_model=AuthorizeUrlResponse)
async def github_authorize(
    t: str | None = None,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """Retorna a URL de autorização do GitHub (OAuth2).

    Aceita um `t` (access token JWT) opcional para vincular o GitHub à conta
    logada em vez de criar/entrar por e-mail.
    """
    user_id: int | None = None
    if t:
        payload = decode_token(t)
        if payload and payload.get("type") == "access" and payload.get("sub"):
            user_id = int(payload["sub"])

    service = GitHubOAuthService(db, settings)
    try:
        url = service.build_authorize_url(user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    return AuthorizeUrlResponse(url=url)


@router.get("/github/callback")
async def github_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Callback do GitHub: troca o code por tokens e redireciona ao frontend."""
    service = GitHubOAuthService(db, settings)
    try:
        result = await service.handle_callback(code, state)
    except ValueError as e:
        return RedirectResponse(
            f"{settings.frontend_url}/auth/callback?{urlencode({'error': str(e)})}",
            status_code=status.HTTP_302_FOUND,
        )

    params = urlencode(
        {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
        }
    )
    return RedirectResponse(
        f"{settings.frontend_url}/auth/callback?{params}",
        status_code=status.HTTP_302_FOUND,
    )


task_router = APIRouter(prefix="/tasks", tags=["tasks"])


@task_router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.create(current_user.id, data)


@task_router.get("", response_model=list[TaskResponse])
async def list_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.get_all(current_user.id)


@task_router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    task = await service.get_by_id(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@task_router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    task = await service.get_by_id(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return await service.update(task, data)


@task_router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    task = await service.get_by_id(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    await service.delete(task)


@task_router.post("/reorder/{column_status}", response_model=list[TaskResponse])
async def reorder_tasks(
    column_status: str,
    task_ids: list[int],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.models import TaskStatus

    try:
        task_status = TaskStatus(column_status)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    service = TaskService(db)
    return await service.reorder_by_status(current_user.id, task_status, task_ids)


session_router = APIRouter(prefix="/sessions", tags=["sessions"])


@session_router.post("", response_model=StudySessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    data: StudySessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StudySessionService(db)
    try:
        return await service.start(current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@session_router.post("/{session_id}/complete", response_model=StudySessionResponse)
async def complete_session(
    session_id: int,
    data: StudySessionComplete,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StudySessionService(db)
    try:
        return await service.complete(session_id, current_user.id, data.duration_min)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@session_router.get("", response_model=list[StudySessionResponse])
async def list_sessions(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StudySessionService(db)
    return await service.get_recent(current_user.id, limit)


journal_router = APIRouter(prefix="/journal", tags=["journal"])


@journal_router.post("", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_journal(
    data: JournalEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = JournalService(db)
    try:
        return await service.create(current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@dashboard_router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    return await service.get_dashboard(current_user.id)


github_router = APIRouter(prefix="/github", tags=["github"])


@github_router.get("/status", response_model=GitHubStatusResponse)
async def github_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    commit_count = await CommitRepository(db).count_by_user(current_user.id)
    return GitHubStatusResponse(
        connected=current_user.github_id is not None,
        username=current_user.github_username,
        commit_count=commit_count,
    )


@github_router.post("/sync", response_model=SyncResultResponse)
async def github_sync(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Sincroniza commits na hora (além do job em background do APScheduler)."""
    if not current_user.github_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub não conectado"
        )
    service = CommitSyncService(db, settings)
    new_commits = await service.sync_user(current_user)
    total = await CommitRepository(db).count_by_user(current_user.id)
    return SyncResultResponse(new_commits=new_commits, total_commits=total)


@github_router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def github_disconnect(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    service = GitHubOAuthService(db, settings)
    try:
        await service.disconnect(current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@github_router.get("/commits", response_model=list[CommitResponse])
async def github_commits(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CommitRepository(db).get_recent(current_user.id, min(limit, 100))


activity_router = APIRouter(prefix="/activity", tags=["activity"])


@activity_router.get("/feed", response_model=list[FeedItem])
async def activity_feed(
    days: int = 14,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ActivityService(db)
    return await service.get_feed(current_user.id, days=min(max(days, 1), 90), limit=limit)


@activity_router.get("/heatmap", response_model=list[HeatmapDay])
async def activity_heatmap(
    days: int = 365,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ActivityService(db)
    return await service.get_heatmap(current_user.id, days=min(max(days, 1), 730))
