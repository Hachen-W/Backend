from uuid import UUID

from fastapi import APIRouter

from app.models.survey import Survey
from app.routers.responses import BAD_ID
from app.routers.v1.surveys import NOT_FOUND, SurveyServiceDep
from app.schemas.survey import SurveyReadV2, SurveySchedule

router = APIRouter(prefix="/api/v2/surveys", tags=["surveys v2"])


def to_read_v2(survey: Survey) -> SurveyReadV2:
    return SurveyReadV2(
        id=survey.id,
        author_id=survey.author_id,
        status=survey.status,
        created_at=survey.created_at,
        updated_at=survey.updated_at,
        schedule=SurveySchedule(opens_at=survey.opens_at, closes_at=survey.closes_at),
        title=survey.title,
        description=survey.description,
        anonymous=survey.anonymous,
    )


@router.get(
    "/{survey_id}",
    response_model=SurveyReadV2,
    summary="Прочитать опрос (v2)",
    description=(
        "Возвращает опрос по идентификатору. В отличие от v1, даты открытия и закрытия "
        "собраны в объект `schedule`. Отвечает 404, если опроса нет."
    ),
    responses={**NOT_FOUND, **BAD_ID},
)
async def get_survey_v2(survey_id: UUID, service: SurveyServiceDep) -> SurveyReadV2:
    survey = await service.get(survey_id)
    return to_read_v2(survey)
