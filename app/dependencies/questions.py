from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, StorageBackend, get_settings
from app.core.database import get_session
from app.dependencies.surveys import get_survey_repository
from app.repositories.questions import (
    InMemoryQuestionRepository,
    QuestionRepository,
    SqlAlchemyQuestionRepository,
)
from app.repositories.surveys import SurveyRepository
from app.use_cases.questions import QuestionService


@lru_cache
def get_memory_question_repository() -> InMemoryQuestionRepository:
    return InMemoryQuestionRepository()


def get_question_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> QuestionRepository:
    if settings.storage == StorageBackend.MEMORY:
        return get_memory_question_repository()
    return SqlAlchemyQuestionRepository(session)


def get_question_service(
    questions: Annotated[QuestionRepository, Depends(get_question_repository)],
    surveys: Annotated[SurveyRepository, Depends(get_survey_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> QuestionService:
    return QuestionService(questions, surveys, max_questions=settings.max_questions_per_survey)
