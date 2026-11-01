from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.exceptions.surveys import SurveyClosesBeforeOpens, SurveyNotFound, SurveyTooLong
from app.models.survey import SortOrder, Survey, SurveySortField
from app.repositories.surveys import SurveyRepository
from app.schemas.survey import SurveyCreate, SurveyPatch, SurveyReplace, SurveyStatus
from app.use_cases.common import apply_changes


class SurveyService:
    def __init__(self, surveys: SurveyRepository, max_duration: timedelta) -> None:
        self._surveys = surveys
        self._max_duration = max_duration

    async def get(self, survey_id: UUID) -> Survey:
        survey = await self._surveys.get(survey_id)
        if survey is None:
            raise SurveyNotFound(survey_id)
        return survey

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        status: SurveyStatus | None,
        opens_from: datetime | None,
        opens_to: datetime | None,
        sort_by: SurveySortField,
        order: SortOrder,
    ) -> list[Survey]:
        return await self._surveys.find(
            limit=limit,
            offset=offset,
            status_filter=status,
            opens_from=opens_from,
            opens_to=opens_to,
            sort_by=sort_by,
            order=order,
        )

    async def create(self, payload: SurveyCreate, author_id: UUID) -> Survey:
        self._check_rules(payload.opens_at, payload.closes_at)
        survey = Survey(**payload.model_dump(), author_id=author_id)
        await self._surveys.add(survey)
        return survey

    async def replace(self, survey_id: UUID, payload: SurveyReplace) -> Survey:
        current = await self.get(survey_id)
        self._check_rules(payload.opens_at, payload.closes_at)
        apply_changes(current, {**payload.model_dump(), "updated_at": datetime.now(UTC)})
        await self._surveys.update(current)
        return current

    async def update(self, survey_id: UUID, payload: SurveyPatch) -> Survey:
        current = await self.get(survey_id)
        changes = payload.model_dump(exclude_unset=True)
        self._check_rules(
            changes.get("opens_at", current.opens_at),
            changes.get("closes_at", current.closes_at),
        )
        apply_changes(current, {**changes, "updated_at": datetime.now(UTC)})
        await self._surveys.update(current)
        return current

    async def delete(self, survey_id: UUID) -> None:
        await self.get(survey_id)
        await self._surveys.delete(survey_id)

    def _check_rules(self, opens_at: datetime, closes_at: datetime) -> None:
        if closes_at <= opens_at:
            raise SurveyClosesBeforeOpens(opens_at, closes_at)
        duration = closes_at - opens_at
        if duration > self._max_duration:
            raise SurveyTooLong(duration, self._max_duration)
