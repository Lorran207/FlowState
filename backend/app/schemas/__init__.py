from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models import TaskStatus, XPSource


class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse | None = None


class TokenData(BaseModel):
    user_id: int | None = None


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus | None = None
    position: int | None = None


class TaskResponse(TaskBase):
    id: int
    user_id: int
    status: TaskStatus
    position: int
    created_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class StudySessionBase(BaseModel):
    task_id: int | None = None


class StudySessionCreate(StudySessionBase):
    pass


class StudySessionComplete(BaseModel):
    duration_min: int = Field(ge=1)


class StudySessionResponse(StudySessionBase):
    id: int
    user_id: int
    started_at: datetime
    ended_at: datetime | None = None
    duration_min: int | None = None
    completed: bool

    class Config:
        from_attributes = True


class JournalEntryBase(BaseModel):
    content: str = Field(min_length=1, max_length=280)


class JournalEntryCreate(JournalEntryBase):
    session_id: int


class JournalEntryResponse(JournalEntryBase):
    id: int
    user_id: int
    session_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class XPEventResponse(BaseModel):
    id: int
    user_id: int
    amount: int
    source: XPSource
    created_at: datetime

    class Config:
        from_attributes = True


class UserStatsResponse(BaseModel):
    xp_total: int
    level: int
    streak: int
    longest_streak: int
    last_active_date: datetime | None = None


class DashboardResponse(BaseModel):
    stats: UserStatsResponse
    recent_sessions: list[StudySessionResponse]
    recent_tasks: list[TaskResponse]
    weekly_minutes: int
