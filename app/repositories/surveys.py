from typing import Protocol
from uuid import UUID

from pydantic import AwareDatetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.surveys import SurveyHasQuestions
from app.models.survey import SortOrder, Survey, SurveySortField, SurveyStatus

SORT_COLUMNS = {
    SurveySortField.CREATED_AT: Survey.created_at,
    SurveySortField.OPENS_AT: Survey.opens_at,
    SurveySortField.CLOSES_AT: Survey.closes_at,
    SurveySortField.TITLE: Survey.title,
}


class SurveyRepository(Protocol):
    async def get(self, survey_id: UUID) -> Survey | None: ...
    async def find(
        self,
        limit: int = 20,
        offset: int = 0,
        status_filter: SurveyStatus | None = None,
        opens_from: AwareDatetime | None = None,
        opens_to: AwareDatetime | None = None,
        sort_by: SurveySortField = SurveySortField.CREATED_AT,
        order: SortOrder = SortOrder.ASC,
    ) -> list[Survey]: ...
    async def add(self, survey: Survey) -> None: ...
    async def update(self, survey: Survey) -> None: ...
    async def delete(self, survey_id: UUID) -> None: ...


class InMemorySurveyRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Survey] = {}

    async def get(self, survey_id: UUID) -> Survey | None:
        return self._items.get(survey_id)

    async def find(
        self,
        limit: int = 20,
        offset: int = 0,
        status_filter: SurveyStatus | None = None,
        opens_from: AwareDatetime | None = None,
        opens_to: AwareDatetime | None = None,
        sort_by: SurveySortField = SurveySortField.CREATED_AT,
        order: SortOrder = SortOrder.ASC,
    ) -> list[Survey]:
        result = list(self._items.values())

        if status_filter is not None:
            result = [survey for survey in result if survey.status == status_filter]
        if opens_from is not None:
            result = [survey for survey in result if survey.opens_at >= opens_from]
        if opens_to is not None:
            result = [survey for survey in result if survey.opens_at <= opens_to]

        result.sort(
            key=lambda survey: getattr(survey, sort_by.value),
            reverse=order == SortOrder.DESC,
        )

        return result[offset : offset + limit]

    async def add(self, survey: Survey) -> None:
        self._items[survey.id] = survey

    async def update(self, survey: Survey) -> None:
        self._items[survey.id] = survey

    async def delete(self, survey_id: UUID) -> None:
        self._items.pop(survey_id, None)


class SqlAlchemySurveyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, survey_id: UUID) -> Survey | None:
        return await self._session.get(Survey, survey_id)

    async def find(
        self,
        limit: int = 20,
        offset: int = 0,
        status_filter: SurveyStatus | None = None,
        opens_from: AwareDatetime | None = None,
        opens_to: AwareDatetime | None = None,
        sort_by: SurveySortField = SurveySortField.CREATED_AT,
        order: SortOrder = SortOrder.ASC,
    ) -> list[Survey]:
        query = select(Survey)
        if status_filter is not None:
            query = query.where(Survey.status == status_filter)
        if opens_from is not None:
            query = query.where(Survey.opens_at >= opens_from)
        if opens_to is not None:
            query = query.where(Survey.opens_at <= opens_to)

        column = SORT_COLUMNS[sort_by]
        query = query.order_by(column.desc() if order == SortOrder.DESC else column.asc())
        query = query.limit(limit).offset(offset)
        return list((await self._session.scalars(query)).all())

    async def add(self, survey: Survey) -> None:
        self._session.add(survey)
        await self._session.flush()

    async def update(self, survey: Survey) -> None:
        await self._session.flush()

    async def delete(self, survey_id: UUID) -> None:
        survey = await self._session.get(Survey, survey_id)
        if survey is None:
            return
        await self._session.delete(survey)
        try:
            await self._session.flush()
        except IntegrityError:
            raise SurveyHasQuestions(survey_id) from None
