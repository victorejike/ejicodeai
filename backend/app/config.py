"""Configuration module using Pydantic Settings."""
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, env_ignore_empty=True)

    # Database
    database_url: str = "sqlite+aiosqlite:///./dev.db"
    db_user: str = "dev"
    db_password: str = "dev"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_password: str = "dev"

    # ChromaDB
    chroma_url: str = "http://localhost:8000"
    chroma_token: Optional[str] = None

    # FastAPI
    api_url: str = "http://localhost:8000"
    app_debug: bool = False
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_hours: int = 4
    refresh_token_expire_days: int = 30
    dev_username: str = "admin"
    dev_password: str = "admin"
    dev_user_roles: list[str] = ["admin"]

    # SMTP Configuration
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_user: str = "user"
    smtp_password: str = "password"
    smtp_from_email: str = "noreply@ejicode.com"
    smtp_from_name: str = "Ejicode BD Platform"

    # IMAP Configuration
    imap_host: Optional[str] = None
    imap_port: int = 993
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    imap_folder: str = "INBOX"

    # AI provider configuration
    gemini_api_key: str = ""
    gemini_base_url: str = "https://gemini.googleapis.com/v1"
    gemini_model: str = "gemini-2.5-flash"

    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://api.nvidia.com/v1"
    nvidia_model: str = "nim-1.0"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "deepseek-r1:8b"

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "google/gemma-4-31b-it:free"
    openrouter_reasoning_model: str = "google/gemma-4-31b-it:free"

    # Third-party APIs
    hunter_io_api_key: Optional[str] = None
    apify_api_token: Optional[str] = None
    apify_google_maps_actor_id: str = "compass/crawler-google-places"
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None

    # Monitoring
    grafana_password: str = "admin"
    prometheus_retention_days: int = 15

    # Deployment
    environment: str = "development"
    log_level: str = "INFO"

    # Feature flags
    enable_proposal_auto_generation: bool = True
    enable_automated_outreach: bool = False
    enable_reply_monitoring: bool = False

    # Rate limits
    max_emails_per_day: int = 50
    min_send_interval_minutes: int = 5
    follow_up_interval_days: int = 5
    max_follow_ups: int = 3

    # Rate Limiting
    rate_limit_max_requests: int = 200
    rate_limit_window_seconds: int = 60


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
