from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    REDIS_URL: str = "redis://redis:6379/0"
    STORAGE_DIR: str = "/data"
    PUBLIC_BASE_URL: str = "http://localhost"
    MAX_UPLOAD_MB: int = 2048

settings = Settings()
