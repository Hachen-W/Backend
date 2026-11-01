from fastapi import FastAPI

from app.core.config import get_settings
from app.errors import register_error_handlers
from app.routers.v1 import questions, surveys, users
from app.routers.v2 import surveys as surveys_v2

get_settings()

tags_metadata = [
    {"name": "health", "description": "Служебная проверка, что сервис запущен и отвечает."},
    {
        "name": "users",
        "description": "Пользователи сервиса: авторы опросов и респонденты. "
        "Почта уникальна, пароль никогда не возвращается в ответах.",
    },
    {
        "name": "surveys",
        "description": "Опросы: заголовок, режим анонимности и окно проведения. "
        "Автор и статус назначаются сервером.",
    },
    {
        "name": "questions",
        "description": "Вопросы внутри опроса с типом, порядковым номером "
        "и признаком обязательности.",
    },
    {
        "name": "surveys v2",
        "description": "Опросы, версия 2. Хранилище общее с v1, отличается только "
        "схема ответа: даты открытия и закрытия собраны в объект `schedule`.",
    },
]

app = FastAPI(
    title="Survey Service API",
    version="0.2.0",
    description=(
        "Микросервис проведения опросов, который подключается к вашей системе по REST API. "
        "Позволяет управлять пользователями, опросами и вопросами к ним. "
        "Все ошибки возвращаются в едином формате "
        '`{"error": {"code", "message", "details"}}`.'
    ),
    openapi_tags=tags_metadata,
)
app.include_router(users.router)
app.include_router(surveys.router)
app.include_router(questions.router)
app.include_router(surveys_v2.router)
register_error_handlers(app)


@app.get(
    "/health",
    summary="Проверка состояния",
    description="Возвращает `ok`, если сервис запущен. Не обращается к хранилищу.",
    tags=["health"],
)
async def health():
    return {"status": "ok"}
