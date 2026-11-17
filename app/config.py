from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    REDIS_URL: str = "redis://localhost:6379/0"
    WEBHOOK_BASE_URL: str  # e.g. https://your-app.onrender.com
    WEBAPP_URL: str        # e.g. https://your-app.onrender.com/static/index.html

    class Config:
        env_file = ".env"

settings = Settings()
