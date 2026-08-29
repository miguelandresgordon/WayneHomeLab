"""Runtime settings. Secrets stay in the environment, never in git."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    job_finder_version: str = "0.1.0"
    log_level: str = "info"
    job_finder_host: str = "0.0.0.0"
    job_finder_port: int = 8473
    job_finder_database_url: str = "sqlite:///./data/jobfinder.db"
    tz: str = "Europe/Madrid"

    job_finder_secret_key: str = "dev-only-change-me"
    job_finder_session_hours: int = 12
    job_finder_cookie_secure: bool = False
    job_finder_login_rate_limit: int = 10
    job_finder_login_rate_window_seconds: int = 900

    job_finder_argon2_time_cost: int = 2
    job_finder_argon2_memory_cost: int = 19456
    job_finder_argon2_parallelism: int = 1

    job_finder_resumes_dir: str = "./data/resumes"
    job_finder_resume_max_bytes: int = 5_242_880  # 5 MiB

    job_finder_user_a_email: str | None = None
    job_finder_user_a_password: str | None = None
    job_finder_user_b_email: str | None = None
    job_finder_user_b_password: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
