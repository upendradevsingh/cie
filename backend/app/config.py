from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "CIE"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://cie:cie@localhost:5432/cie"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT validation (shared secret from calling service)
    JWT_SECRET: str  # required — app will fail to start without this
    JWT_ALGORITHM: str = "HS256"

    # Transcription
    DEEPGRAM_API_KEY: str = ""
    TRANSCRIPTION_PROVIDER: str = "deepgram"

    # LLM
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-5-mini"
    LLM_FALLBACK_MODEL: str = "gpt-4o"

    # Storage
    UPLOAD_DIR: str = "/app/uploads"
    MAX_FILE_SIZE_MB: int = 100
    S3_BUCKET: str = ""
    S3_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Profiles
    PROFILES_DIR: str = str(Path(__file__).parent / "profiles")

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


settings = Settings()
