"""Application configuration via pydantic-settings."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "debug"

    # API Keys
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://syl:syl_dev_password@localhost:5432/syl_db"
    DATABASE_URL_SYNC: str = "postgresql://syl:syl_dev_password@localhost:5432/syl_db"

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    JWT_SECRET: str = "change_me_in_production_minimum_32_chars"
    JWT_EXPIRY_DAYS: int = 7

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # File storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 100

    # Embedding
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # LLM models
    CLAUDE_SONNET_MODEL: str = "claude-3-5-sonnet-20241022"
    CLAUDE_HAIKU_MODEL: str = "claude-3-haiku-20240307"
    OPENAI_MAIN_MODEL: str = "gpt-4o-mini"
    OPENAI_FALLBACK_MODEL: str = "gpt-4o"

    # Token budgets
    MAX_TOTAL_TOKENS: int = 6000
    SYSTEM_PROMPT_TOKENS: int = 400
    SESSION_SUMMARY_TOKENS: int = 300
    LAST_N_MESSAGES: int = 5
    RETRIEVED_CHUNKS_TOKENS: int = 2000

    # LLM timeouts
    LLM_TIMEOUT_SECONDS: float = 5.0
    LLM_FALLBACK_TIMEOUT_SECONDS: float = 8.0

    # OCR
    OCR_TEXT_THRESHOLD: int = 50  # chars; below this → page is scanned
    OCR_CONFIDENCE_WARNING: float = 70.0  # below this → warn user

    # Chunking
    TEXT_CHUNK_SIZE: int = 500  # tokens for text-based pages
    TEXT_CHUNK_OVERLAP: int = 50
    OCR_CHUNK_SIZE: int = 350  # smaller for noisy OCR text
    OCR_CHUNK_OVERLAP: int = 80

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    DAILY_MESSAGE_LIMIT_FREE: int = 50
    PAGE_LIMIT_FREE: int = 200

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
