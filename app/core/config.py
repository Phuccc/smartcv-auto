from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:conmeonho2@localhost:5432/smartcv-auto"
    SECRET_KEY: str = "smartcv-auto-super-secret-key-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
