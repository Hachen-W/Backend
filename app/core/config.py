from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageBackend(StrEnum):
    MEMORY = "memory"
    DATABASE = "database"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    max_survey_duration_days: int = Field(
        default=90, ge=1, le=365, description="Максимальная длительность опроса, дни"
    )
    max_questions_per_survey: int = Field(
        default=50, ge=1, le=500, description="Максимальное число вопросов в опросе"
    )
    storage: StorageBackend = Field(
        default=StorageBackend.DATABASE, description="Где хранить данные: memory или database"
    )
    database_url: str = Field(
        default="postgresql+asyncpg://survey:survey@localhost:5432/survey",
        description="Строка подключения SQLAlchemy, драйвер asyncpg",
    )
    sql_echo: bool = Field(default=False, description="Печатать SQL-запросы в консоль")


@lru_cache
def get_settings() -> Settings:
    return Settings()
