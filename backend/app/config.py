from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = ""

    # Redis
    redis_url: str = "redis://redis:6379"

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "nexusforge"

    # LLM Providers
    groq_api_key: str = ""
    anthropic_api_key: str = ""

    # Ollama (local inference)
    ollama_enabled: bool = False
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"

    # Embeddings
    voyage_api_key: str = ""

    # JWT
    jwt_secret: str = ""

    # App
    app_name: str = "NexusForge AI"
    debug: bool = False  # default secure — set DEBUG=true in .env for development
    allowed_origins: str = ""  # set ALLOWED_ORIGINS in .env (comma-separated)
    port: int = 8000

    class Config:
        env_file = ".env"

settings = Settings()

# ── Startup validations ─────────────────────────────────────────────────────
import logging as _logging

_startup_logger = _logging.getLogger("nexusforge.config")

if not settings.database_url:
    raise RuntimeError(
        "CRITICAL: DATABASE_URL environment variable is not set. "
        "The application cannot start without a database connection."
    )

if not settings.jwt_secret or len(settings.jwt_secret.encode()) < 32:
    raise RuntimeError(
        "CRITICAL: JWT_SECRET is missing or too short (< 32 bytes). "
        "Authentication tokens will be insecure. Set a strong JWT_SECRET in .env."
    )
