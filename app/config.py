from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str
    WEBHOOK_BASE_URL: str = "http://localhost:8000"
    WEBAPP_URL: str = "http://localhost:8000/static/index.html"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"

    # Whisper
    WHISPER_MODEL: str = "base"

    # Clipping
    MAX_CLIPS: int = 6
    MIN_CLIP_SECONDS: int = 15
    MAX_CLIP_SECONDS: int = 90

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
