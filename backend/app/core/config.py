from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://flowstate:flowstate@localhost:5432/flowstate"
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # GitHub OAuth (V0.2)
    github_client_id: str = ""
    github_client_secret: str = ""
    github_callback_url: str = "http://localhost:8000/auth/github/callback"
    frontend_url: str = "http://localhost:5173"
    github_sync_interval_minutes: int = 30
    daily_goal_minutes: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()
