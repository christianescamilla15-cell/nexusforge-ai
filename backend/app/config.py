from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://nexus:nexus_dev_2026@postgres:5432/nexusforge"

    # Redis
    redis_url: str = "redis://redis:6379"

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "nexusforge"

    # LLM Providers
    groq_api_key: str = ""
    anthropic_api_key: str = ""

    # Embeddings
    voyage_api_key: str = ""

    # App
    app_name: str = "NexusForge AI"
    debug: bool = True
    allowed_origins: str = "*"

    class Config:
        env_file = ".env"

settings = Settings()
