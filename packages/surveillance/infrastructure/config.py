from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="SURVEILLANCE_", extra="ignore"
    )

    app_name: str = "Agentic Surveillance Platform"
    environment: str = "development"
    database_url: str = "sqlite:///./surveillance.db"
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    upload_directory: Path = Path("uploads")
    policy_directory: Path = Path("policies")
    report_directory: Path = Path("reports")
    twilio_enabled: bool = False
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_api_key_sid: str = ""
    twilio_api_key_secret: str = ""
    twilio_from_number: str = ""
    twilio_live_validated: bool = False
    max_video_size_mb: int = Field(default=250, ge=1, le=2048)
    frame_sample_fps: float = Field(default=2, gt=0, le=30)
    playback_speed: float = Field(default=4, ge=0, le=32)
    temporal_cluster_gap_seconds: float = Field(default=5, gt=0, le=300)
    accident_model_path: Path | None = None
    accident_confidence_threshold: float = Field(default=0.5, ge=0, le=1)
    force_accept_verification: bool = True
    session_ttl_hours: int = Field(default=12, ge=1, le=720)
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_max_retries: int = Field(default=2, ge=0, le=5)


@lru_cache
def get_settings() -> Settings:
    return Settings()
