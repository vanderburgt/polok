"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://polok:polok@localhost:5432/polok"
    API_KEYS: str = ""
    SITE_PASSWORD: str = "CHANGE_ME"
    SECRET_KEY: str = "polok-session-key-change-me"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
