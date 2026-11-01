from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.dependencies.questions import get_question_service
from app.routers.responses import BAD_BODY, BAD_ID, BAD_ID_OR_BODY, error_response
from app.schemas.question import QuestionCreate, QuestionPatch, QuestionRead, QuestionReplace
from app.use_cases.questions import QuestionService

router = APIRouter(prefix="/api/v1/questions", tags=["questions"])

NOT_FOUND = error_response(404, "Вопрос не найден")
LIMIT_REACHED = error_response(409, "В опросе уже максимальное число вопросов")

QuestionServiceDep = Annotated[QuestionService, Depends(get_question_service)]


@router.get(
    "",
    response_model=list[QuestionRead],
    summary="Список вопросов",
    description="Возвращает вопросы всех опросов. Если вопросов нет, возвращает пустой список.",
)
async def list_questions(service: QuestionServiceDep) -> list[QuestionRead]:
    return [
        QuestionRead.model_validate(question, from_attributes=True)
        for question in await service.list()
    ]


@router.post(
    "",
    response_model=QuestionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить вопрос в опрос",
    description=(
        "Создаёт вопрос в опросе, указанном в `survey_id`. Адрес нового вопроса возвращается "
        "в заголовке `Location`. Отвечает 404, если опроса с таким идентификатором нет, "
        "409, если в опросе уже максимальное число вопросов, и 422, если тип вопроса "
        "неизвестен, позиция вне диапазона 0–100, текст пустой или в теле есть лишние поля."
    ),
    responses={
        **error_response(404, "Опрос из `survey_id` не найден"),
        **LIMIT_REACHED,
        **BAD_BODY,
    },
)
async def create_question(
    payload: QuestionCreate, response: Response, service: QuestionServiceDep
) -> QuestionRead:
    question = await service.create(payload)
    response.headers["Location"] = f"/api/v1/questions/{question.id}"
    return QuestionRead.model_validate(question, from_attributes=True)


@router.get(
    "/{question_id}",
    response_model=QuestionRead,
    summary="Прочитать вопрос",
    description="Возвращает вопрос по идентификатору. Отвечает 404, если вопроса нет.",
    responses={**NOT_FOUND, **BAD_ID},
)
async def get_question(question_id: UUID, service: QuestionServiceDep) -> QuestionRead:
    question = await service.get(question_id)
    return QuestionRead.model_validate(question, from_attributes=True)


@router.put(
    "/{question_id}",
    response_model=QuestionRead,
    summary="Заменить вопрос целиком",
    description=(
        "Заменяет текст, тип, позицию и обязательность вопроса. Перенести вопрос в другой "
        "опрос нельзя: поля `survey_id` в теле замены нет. Отвечает 404, если вопроса нет, "
        "и 422 по тем же правилам, что и создание."
    ),
    responses={**NOT_FOUND, **BAD_ID_OR_BODY},
)
async def replace_question(
    question_id: UUID, payload: QuestionReplace, service: QuestionServiceDep
) -> QuestionRead:
    question = await service.replace(question_id, payload)
    return QuestionRead.model_validate(question, from_attributes=True)


@router.patch(
    "/{question_id}",
    response_model=QuestionRead,
    summary="Частично обновить вопрос",
    description=(
        "Меняет только переданные поля вопроса, непереданные сохраняют прежние значения. "
        "Каждое переданное поле проверяется по тем же правилам, что и при создании; "
        "передать `null` в поле нельзя. Перенести вопрос в другой опрос нельзя: поля "
        "`survey_id` в теле нет. Отвечает 404, если вопроса нет, и 422, если поле "
        "не прошло проверку или в теле есть лишние поля."
    ),
    responses={**NOT_FOUND, **BAD_ID_OR_BODY},
)
async def patch_question(
    question_id: UUID, payload: QuestionPatch, service: QuestionServiceDep
) -> QuestionRead:
    question = await service.update(question_id, payload)
    return QuestionRead.model_validate(question, from_attributes=True)


@router.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить вопрос",
    description="Удаляет вопрос и возвращает пустой ответ. Отвечает 404, если вопроса нет.",
    responses={**NOT_FOUND, **BAD_ID},
)
async def delete_question(question_id: UUID, service: QuestionServiceDep) -> None:
    await service.delete(question_id)
