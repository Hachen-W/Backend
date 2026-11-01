from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.question import Question


class QuestionRepository(Protocol):
    async def get(self, question_id: UUID) -> Question | None: ...
    async def find(self) -> list[Question]: ...
    async def add(self, question: Question) -> None: ...
    async def update(self, question: Question) -> None: ...
    async def delete(self, question_id: UUID) -> None: ...
    async def count_by_survey(self, survey_id: UUID) -> int: ...


class InMemoryQuestionRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Question] = {}

    async def get(self, question_id: UUID) -> Question | None:
        return self._items.get(question_id)

    async def find(self) -> list[Question]:
        return list(self._items.values())

    async def add(self, question: Question) -> None:
        self._items[question.id] = question

    async def update(self, question: Question) -> None:
        self._items[question.id] = question

    async def delete(self, question_id: UUID) -> None:
        self._items.pop(question_id, None)

    async def count_by_survey(self, survey_id: UUID) -> int:
        return sum(1 for q in self._items.values() if q.survey_id == survey_id)


class SqlAlchemyQuestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, question_id: UUID) -> Question | None:
        return await self._session.get(Question, question_id)

    async def find(self) -> list[Question]:
        return list((await self._session.scalars(select(Question))).all())

    async def add(self, question: Question) -> None:
        self._session.add(question)
        await self._session.flush()

    async def update(self, question: Question) -> None:
        await self._session.flush()

    async def delete(self, question_id: UUID) -> None:
        question = await self._session.get(Question, question_id)
        if question is not None:
            await self._session.delete(question)
            await self._session.flush()

    async def count_by_survey(self, survey_id: UUID) -> int:
        query = select(func.count()).select_from(Question).where(Question.survey_id == survey_id)
        return await self._session.scalar(query) or 0
