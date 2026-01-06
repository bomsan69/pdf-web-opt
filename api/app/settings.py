from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )

    REDIS_URL: str = "redis://redis:6379/0"
    STORAGE_DIR: str = "/data"
    PUBLIC_BASE_URL: str = "http://localhost:8003"
    MAX_UPLOAD_MB: int = 2048

settings = Settings()
