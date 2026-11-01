from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import AwareDatetime

from app.dependencies.surveys import get_survey_service
from app.models.survey import SortOrder, SurveySortField
from app.routers.responses import BAD_ID, BAD_ID_OR_BODY, error_response
from app.schemas.survey import SurveyCreate, SurveyPatch, SurveyRead, SurveyReplace, SurveyStatus
from app.use_cases.surveys import SurveyService

STUB_AUTHOR_ID = UUID("00000000-0000-0000-0000-000000000001")

router = APIRouter(prefix="/api/v1/surveys", tags=["surveys"])

NOT_FOUND = error_response(404, "Опрос не найден")
RULE_VIOLATION = error_response(
    422, "Тело не прошло проверку или нарушено правило: длительность, порядок дат"
)

SurveyServiceDep = Annotated[SurveyService, Depends(get_survey_service)]


@router.get(
    "",
    response_model=list[SurveyRead],
    summary="Список опросов",
    description=(
        "Возвращает страницу опросов. Параметр `limit` задаёт размер страницы "
        "(от 1 до 100, по умолчанию 20), `offset` - сколько опросов пропустить с начала. "
        "Можно отфильтровать по статусу (`status`) и по диапазону даты открытия "
        "(`opens_from`, `opens_to`), обе границы включаются. Сортировка задаётся "
        "параметрами `sort_by` (одно из допустимых полей) и `order` (`asc` или `desc`). "
        "Если подходящих опросов нет или `offset` больше их количества, возвращает "
        "пустой список. Отвечает 422, если параметры вне допустимых границ."
    ),
    responses=error_response(422, "Параметры запроса не прошли проверку"),
)
async def list_surveys(
    service: SurveyServiceDep,
    limit: Annotated[int, Query(ge=1, le=100, description="Сколько вернуть")] = 20,
    offset: Annotated[int, Query(ge=0, description="Сколько пропустить")] = 0,
    status_filter: Annotated[
        SurveyStatus | None, Query(alias="status", description="Только опросы с этим статусом")
    ] = None,
    opens_from: Annotated[
        AwareDatetime | None, Query(description="Открываются не раньше этого момента")
    ] = None,
    opens_to: Annotated[
        AwareDatetime | None, Query(description="Открываются не позже этого момента")
    ] = None,
    sort_by: Annotated[
        SurveySortField, Query(description="Поле для сортировки")
    ] = SurveySortField.CREATED_AT,
    order: Annotated[SortOrder, Query(description="Направление сортировки")] = SortOrder.ASC,
) -> list[SurveyRead]:
    surveys = await service.list(
        limit=limit,
        offset=offset,
        status=status_filter,
        opens_from=opens_from,
        opens_to=opens_to,
        sort_by=sort_by,
        order=order,
    )
    return [SurveyRead.model_validate(survey, from_attributes=True) for survey in surveys]


@router.post(
    "",
    response_model=SurveyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать опрос",
    description=(
        "Создаёт опрос в статусе `draft`. Автор, идентификатор и отметки времени назначает "
        "сервер, передавать их в теле нельзя. Адрес нового опроса возвращается в заголовке "
        "`Location`. Отвечает 422, если в теле есть лишние поля, строки выходят за пределы "
        "длины, у дат нет часового пояса, `closes_at` не позже `opens_at` или опрос "
        "длится дольше допустимого."
    ),
    responses=RULE_VIOLATION,
)
async def create_survey(
    payload: SurveyCreate, response: Response, service: SurveyServiceDep
) -> SurveyRead:
    survey = await service.create(payload, author_id=STUB_AUTHOR_ID)
    response.headers["Location"] = f"/api/v1/surveys/{survey.id}"
    return SurveyRead.model_validate(survey, from_attributes=True)


@router.get(
    "/{survey_id}",
    response_model=SurveyRead,
    summary="Прочитать опрос",
    description="Возвращает опрос по идентификатору. Отвечает 404, если опроса нет.",
    responses={**NOT_FOUND, **BAD_ID},
)
async def get_survey(survey_id: UUID, service: SurveyServiceDep) -> SurveyRead:
    survey = await service.get(survey_id)
    return SurveyRead.model_validate(survey, from_attributes=True)


@router.put(
    "/{survey_id}",
    response_model=SurveyRead,
    summary="Заменить опрос целиком",
    description=(
        "Заменяет все редактируемые поля опроса значениями из тела. Непереданные "
        "необязательные поля сбрасываются к значениям по умолчанию. Идентификатор, автор, "
        "статус и дата создания не меняются, `updated_at` обновляется. Отвечает 404, если "
        "опроса нет, и 422 по тем же правилам, что и создание."
    ),
    responses={**NOT_FOUND, **BAD_ID_OR_BODY, **RULE_VIOLATION},
)
async def replace_survey(
    survey_id: UUID, payload: SurveyReplace, service: SurveyServiceDep
) -> SurveyRead:
    survey = await service.replace(survey_id, payload)
    return SurveyRead.model_validate(survey, from_attributes=True)


@router.patch(
    "/{survey_id}",
    response_model=SurveyRead,
    summary="Частично обновить опрос",
    description=(
        "Меняет только переданные поля, остальные сохраняют прежние значения. "
        "Передача `description: null` очищает описание. `updated_at` обновляется. "
        "Правила проверяются на итоговом опросе. Отвечает 404, если опроса нет, и 422, "
        "если поле не прошло проверку, `closes_at` оказывается не позже `opens_at` или "
        "опрос становится длиннее допустимого."
    ),
    responses={**NOT_FOUND, **BAD_ID_OR_BODY, **RULE_VIOLATION},
)
async def patch_survey(
    survey_id: UUID, payload: SurveyPatch, service: SurveyServiceDep
) -> SurveyRead:
    survey = await service.update(survey_id, payload)
    return SurveyRead.model_validate(survey, from_attributes=True)


@router.delete(
    "/{survey_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить опрос",
    description=(
        "Удаляет опрос и возвращает пустой ответ. Отвечает 404, если опроса нет, и 409, "
        "если в опросе есть вопросы: сначала нужно удалить их."
    ),
    responses={**NOT_FOUND, **error_response(409, "В опросе есть вопросы"), **BAD_ID},
)
async def delete_survey(survey_id: UUID, service: SurveyServiceDep) -> None:
    await service.delete(survey_id)
