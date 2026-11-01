from datetime import timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, StorageBackend, get_settings
from app.core.database import get_session
from app.repositories.surveys import (
    InMemorySurveyRepository,
    SqlAlchemySurveyRepository,
    SurveyRepository,
)
from app.use_cases.surveys import SurveyService


@lru_cache
def get_memory_survey_repository() -> InMemorySurveyRepository:
    return InMemorySurveyRepository()


def get_survey_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SurveyRepository:
    if settings.storage == StorageBackend.MEMORY:
        return get_memory_survey_repository()
    return SqlAlchemySurveyRepository(session)


def get_survey_service(
    surveys: Annotated[SurveyRepository, Depends(get_survey_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SurveyService:
    return SurveyService(surveys, timedelta(days=settings.max_survey_duration_days))
