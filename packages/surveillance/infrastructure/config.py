from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SURVEILLANCE_", extra="ignore")

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
    execution_mode: Literal["live", "simulate", "hybrid"] = "live"
    twilio_enabled: bool = False
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_api_key_sid: str = ""
    twilio_api_key_secret: str = ""
    twilio_from_number: str = ""
    twilio_live_validated: bool = False
    twilio_whatsapp_enabled: bool = False
    twilio_whatsapp_from_number: str = ""
    twilio_whatsapp_live_validated: bool = False
    vonage_whatsapp_enabled: bool = False
    vonage_api_key: str = ""
    vonage_api_secret: str = ""
    vonage_whatsapp_from_number: str = ""
    vonage_messages_url: str = "https://messages-sandbox.nexmo.com/v1/messages"
    public_base_url: str = ""
    report_link_secret: str = ""
    max_video_size_mb: int = Field(default=250, ge=1, le=2048)
    frame_sample_fps: float = Field(default=2, gt=0, le=30)
    playback_speed: float = Field(default=4, ge=0, le=32)
    temporal_cluster_gap_seconds: float = Field(default=5, gt=0, le=300)
    accident_model_path: Path | None = None
    accident_confidence_threshold: float = Field(default=0.5, ge=0, le=1)
    force_accept_verification: bool = False
    verification_threshold: float = Field(default=0.68, ge=0, le=1)
    adaptive_threshold_minimum: float = Field(default=0.60, ge=0, le=1)
    adaptive_threshold_maximum: float = Field(default=0.76, ge=0, le=1)
    adaptive_threshold_maximum_adjustment: float = Field(default=0.08, ge=0, le=0.25)
    adaptive_threshold_stabilizer: float = Field(default=3.0, gt=0, le=100)
    adaptive_threshold_recency_half_life_days: float = Field(default=90.0, gt=0, le=3650)
    sensor_override_probability: float = Field(default=0.92, ge=0, le=1)
    sensor_override_reliability: float = Field(default=0.8, ge=0, le=1)
    visual_override_impact: float = Field(default=0.9, ge=0, le=1)
    visual_override_confidence: float = Field(default=0.75, ge=0, le=1)
    sensor_candidate_probability: float = Field(default=0.7, ge=0, le=1)
    sensor_candidate_reliability: float = Field(default=0.5, ge=0, le=1)
    session_ttl_hours: int = Field(default=12, ge=1, le=720)
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_max_retries: int = Field(default=2, ge=0, le=5)
    geocoding_base_url: str = "https://nominatim.openstreetmap.org"
    geocoding_user_agent: str = "Sentrix-Surveillance-Demo/1.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
