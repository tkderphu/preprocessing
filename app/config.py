"""
config.py
---------
All application settings loaded from environment variables / .env file.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_title: str = "Document Intelligence API"
    app_version: str = "1.0.0"
    debug: bool = False
    upload_dir: Path = Path("app/storage/uploads")

    # ── RabbitMQ / Celery ─────────────────────────────────────────────────────
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672//"
    celery_broker_url: str = "amqp://guest:guest@rabbitmq:5672//"
    celery_result_backend: str = "redis://redis:6379/0"
    celery_queue_name: str = "document_jobs"

    # ── Audio (Whisper + pyannote) ────────────────────────────────────────────
    whisper_model_size: str = "base"           # tiny | base | small | medium | large-v3
    whisper_device: str = "cpu"               # cpu | cuda
    whisper_compute_type: str = "int8"        # int8 | float16 | float32
    huggingface_token: str = Field(default="", alias="HF_TOKEN")

    # ── Unstructured API ──────────────────────────────────────────────────────
    unstructured_url: str = "http://unstructured:8000"

    # ── Groq ──────────────────────────────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "llama3-8b-8192" # default fast model on Groq
    groq_chunk_size: int = 6000        # max characters per chunk sent to Groq

    # ── Email (SMTP) ──────────────────────────────────────────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = ""
    mail_to: str = ""          # default recipient; overridden per-job if provided

    # ── GitHub ────────────────────────────────────────────────────────────────
    github_token: str = ""
    github_repo: str = ""      # format: "owner/repo-name"
    github_branch: str = "main"
    github_output_path: str = "outputs"   # folder inside repo


@lru_cache
def get_settings() -> Settings:
    return Settings()
