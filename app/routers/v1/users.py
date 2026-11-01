from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.dependencies.users import get_user_service
from app.routers.responses import BAD_BODY, BAD_ID, BAD_ID_OR_BODY, error_response
from app.schemas.user import UserCreate, UserRead, UserReplace
from app.use_cases.users import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])

NOT_FOUND = error_response(404, "Пользователь не найден")
CONFLICT = error_response(409, "Почта уже занята другим пользователем")

UserServiceDep = Annotated[UserService, Depends(get_user_service)]


@router.get(
    "",
    response_model=list[UserRead],
    summary="Список пользователей",
    description="Возвращает всех пользователей. Пароль и его хеш в ответ не попадают.",
)
async def list_users(service: UserServiceDep) -> list[UserRead]:
    return [UserRead.model_validate(user, from_attributes=True) for user in await service.list()]


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Зарегистрировать пользователя",
    description=(
        "Создаёт пользователя с ролью `respondent`. Пароль сохраняется только в виде хеша "
        "и в ответе не возвращается. Роль, идентификатор и дату создания назначает сервер. "
        "Адрес нового пользователя возвращается в заголовке `Location`. Отвечает 409, если "
        "почта уже занята, и 422, если почта некорректна, пароль короче 8 символов или "
        "в теле есть лишние поля."
    ),
    responses={**CONFLICT, **BAD_BODY},
)
async def create_user(payload: UserCreate, response: Response, service: UserServiceDep) -> UserRead:
    user = await service.create(payload)
    response.headers["Location"] = f"/api/v1/users/{user.id}"
    return UserRead.model_validate(user, from_attributes=True)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Прочитать пользователя",
    description="Возвращает пользователя по идентификатору. Отвечает 404, если его нет.",
    responses={**NOT_FOUND, **BAD_ID},
)
async def get_user(user_id: UUID, service: UserServiceDep) -> UserRead:
    user = await service.get(user_id)
    return UserRead.model_validate(user, from_attributes=True)


@router.put(
    "/{user_id}",
    response_model=UserRead,
    summary="Заменить пользователя целиком",
    description=(
        "Заменяет почту, отображаемое имя и пароль. Роль, идентификатор и дата создания не "
        "меняются. Отвечает 404, если пользователя нет, 409, если новая почта занята другим "
        "пользователем, и 422 по тем же правилам, что и регистрация."
    ),
    responses={**NOT_FOUND, **CONFLICT, **BAD_ID_OR_BODY},
)
async def replace_user(user_id: UUID, payload: UserReplace, service: UserServiceDep) -> UserRead:
    user = await service.replace(user_id, payload)
    return UserRead.model_validate(user, from_attributes=True)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить пользователя",
    description="Удаляет пользователя и возвращает пустой ответ. Отвечает 404, если его нет.",
    responses={**NOT_FOUND, **BAD_ID},
)
async def delete_user(user_id: UUID, service: UserServiceDep) -> None:
    await service.delete(user_id)
