# Лабораторная работа 3. Слои, зависимости и база данных

Ветка `lab-03`. База поднимается в контейнере, таблицы создаются скриптом:

```bash
cp .env.example .env
docker compose up -d
uv run python -m scripts.create_db
uv run uvicorn app.main:app --reload
```

Выводы ниже получены на запущенном сервисе. Из заголовков ответа оставлен `location`.

## Задача 1. Три слоя и правила в сценарии

### Правила предметной области

| Правило | Тип по условию | Где проверяется | Операции |
|---|---|---|---|
| почта пользователя уникальна | нужны сохранённые объекты | `UserService._check_email_free` | создание, замена |
| опрос длится не дольше `MAX_SURVEY_DURATION_DAYS` дней | временной параметр из настроек | `SurveyService._check_rules` | создание, замена, PATCH |
| в опросе не больше `MAX_QUESTIONS_PER_SURVEY` вопросов | сохранённые объекты и числовой параметр | `QuestionService._check_can_add` | создание |

Правило о числе вопросов проверяется только при создании: схемы замены и PATCH вопроса
не содержат `survey_id`, поэтому замена не может перенести вопрос в другой опрос и
изменить число вопросов в нём. Правило о длительности опроса проверяется в одном методе,
который вызывают создание, замена и PATCH; для PATCH проверяется итоговый опрос
(присланные даты, а непереданные берутся из сохранённого опроса).

```python
def _check_rules(self, opens_at: datetime, closes_at: datetime) -> None:
    if closes_at <= opens_at:
        raise SurveyClosesBeforeOpens(opens_at, closes_at)
    duration = closes_at - opens_at
    if duration > self._max_duration:
        raise SurveyTooLong(duration, self._max_duration)
```

```python
async def _check_can_add(self, survey_id: UUID) -> None:
    """Правила добавления вопроса: опрос существует и в нём есть место."""
    if await self._surveys.get(survey_id) is None:
        raise SurveyNotFound(survey_id)
    if await self._questions.count_by_survey(survey_id) >= self._max_questions:
        raise QuestionLimitReached(survey_id, self._max_questions)
```

```python
async def _check_email_free(self, email: str, except_id: UUID | None = None) -> None:
    """Почта уникальна. При замене пользователь не сравнивается сам с собой."""
    owner = await self._users.get_by_email(email)
    if owner is not None and owner.id != except_id:
        raise EmailAlreadyTaken(email, owner.id)
```

### Слои и каталоги

```text
app/routers/v1/      обработчики: схема на входе → один метод сценария → код, заголовки, схема ответа
app/use_cases/       сценарии: правила и действие, работают с моделями
app/repositories/    протоколы и реализации хранилищ (в памяти и на AsyncSession)
app/models/          модели SQLAlchemy, они же внутренние модели сценариев
app/exceptions/      ошибки сценариев поверх HTTPException
app/dependencies/    место сборки
app/core/            настройки и подключение к базе
```

Каталог `app/api/` переименован в `app/routers/` отдельным коммитом `9fdb53b`.
Проверка, что слои ниже роутера не импортируют FastAPI, обработчики и место сборки:

```bash
$ grep -rnE 'fastapi|app\.routers|app\.dependencies' app/use_cases app/repositories app/models
совпадений нет
```

Обработчик после разделения, без условий по данным и без обращений к хранилищу:

```python
async def create_survey(
    payload: SurveyCreate, response: Response, service: SurveyServiceDep
) -> SurveyRead:
    survey = await service.create(payload, author_id=STUB_AUTHOR_ID)
    response.headers["Location"] = f"/api/v1/surveys/{survey.id}"
    return SurveyRead.model_validate(survey, from_attributes=True)
```

### Ошибки сценариев

Ошибки лежат в `app/exceptions/` и наследуются от `DomainError(HTTPException)`. Промежуточные
классы задают код ответа: `NotFoundError` 404, `ConflictError` 409, `RuleViolationError` 422.
Каждая ошибка хранит данные о случившемся (`survey_id`, `duration`, `max_duration`, `limit`,
`owner_id`). Формат ответа из второй работы не изменился, у доменных ошибок только
уточнён машиночитаемый `code`.

```python
from fastapi import HTTPException


class DomainError(HTTPException):
    status_code: int = 400
    code: str = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(status_code=self.status_code, detail=message)


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class RuleViolationError(DomainError):
    status_code = 422
    code = "rule_violation"


from uuid import UUID

from app.exceptions.base import ConflictError, NotFoundError


class QuestionNotFound(NotFoundError):
    def __init__(self, question_id: UUID) -> None:
        self.question_id = question_id
        super().__init__(f"Вопрос {question_id} не найден")


class QuestionLimitReached(ConflictError):
    code = "question_limit_reached"

    def __init__(self, survey_id: UUID, limit: int) -> None:
        self.survey_id = survey_id
        self.limit = limit
        super().__init__(f"В опросе {survey_id} уже {limit} вопросов, больше добавить нельзя")
```

### Проверка правил через API

Сервер запущен с `MAX_QUESTIONS_PER_SURVEY=2`, чтобы лимит вопросов был виден на коротком примере.

#### Опрос длиннее лимита: создание, 422

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/surveys \
  -H 'Content-Type: application/json' \
  -d '{"title": "Годовой опрос", "opens_at": "2026-11-01T10:00:00+03:00", "closes_at": "2027-06-01T10:00:00+03:00"}'
```

```http
HTTP/1.1 422 Unprocessable Content

{
  "error": {
    "code": "survey_too_long",
    "message": "Опрос длится 212 дн., а допускается не больше 90 дн.",
    "details": []
  }
}
```

#### Обычный опрос: создание, 201

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/surveys \
  -H 'Content-Type: application/json' \
  -d '{"title": "Удовлетворённость офисом", "opens_at": "2026-11-01T10:00:00+03:00", "closes_at": "2026-11-15T10:00:00+03:00"}'
```

```http
HTTP/1.1 201 Created
location: /api/v1/surveys/3104885c-67c1-4748-b5e0-b079a04afec0

{
  "id": "3104885c-67c1-4748-b5e0-b079a04afec0",
  "author_id": "00000000-0000-0000-0000-000000000001",
  "status": "draft",
  "created_at": "2026-10-26T23:56:56.133698Z",
  "updated_at": "2026-10-26T23:56:56.133705Z",
  "opens_at": "2026-11-01T10:00:00+03:00",
  "closes_at": "2026-11-15T10:00:00+03:00",
  "title": "Удовлетворённость офисом",
  "description": null,
  "anonymous": false
}
```

#### Замена теми же данными, 200

Объект не сравнивается сам с собой, замена теми же данными проходит.

```bash
curl -i -X PUT http://127.0.0.1:8000/api/v1/surveys/3104885c-67c1-4748-b5e0-b079a04afec0 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Удовлетворённость офисом", "opens_at": "2026-11-01T10:00:00+03:00", "closes_at": "2026-11-15T10:00:00+03:00"}'
```

```http
HTTP/1.1 200 OK

{
  "id": "3104885c-67c1-4748-b5e0-b079a04afec0",
  "author_id": "00000000-0000-0000-0000-000000000001",
  "status": "draft",
  "created_at": "2026-10-26T23:56:56.133698Z",
  "updated_at": "2026-10-26T23:56:56.244152Z",
  "opens_at": "2026-11-01T10:00:00+03:00",
  "closes_at": "2026-11-15T10:00:00+03:00",
  "title": "Удовлетворённость офисом",
  "description": null,
  "anonymous": false
}
```

#### Обход правила через замену не проходит, 422

```bash
curl -i -X PUT http://127.0.0.1:8000/api/v1/surveys/3104885c-67c1-4748-b5e0-b079a04afec0 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Удовлетворённость офисом", "opens_at": "2026-11-01T10:00:00+03:00", "closes_at": "2027-06-01T10:00:00+03:00"}'
```

```http
HTTP/1.1 422 Unprocessable Content

{
  "error": {
    "code": "survey_too_long",
    "message": "Опрос длится 212 дн., а допускается не больше 90 дн.",
    "details": []
  }
}
```

#### PATCH одной даты проверяется на итоговом опросе, 422

```bash
curl -i -X PATCH http://127.0.0.1:8000/api/v1/surveys/3104885c-67c1-4748-b5e0-b079a04afec0 \
  -H 'Content-Type: application/json' \
  -d '{"closes_at": "2027-06-01T10:00:00+03:00"}'
```

```http
HTTP/1.1 422 Unprocessable Content

{
  "error": {
    "code": "survey_too_long",
    "message": "Опрос длится 212 дн., а допускается не больше 90 дн.",
    "details": []
  }
}
```

#### Лимит вопросов: третий вопрос при лимите 2, 409

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/questions \
  -H 'Content-Type: application/json' \
  -d '{"survey_id": "3104885c-67c1-4748-b5e0-b079a04afec0", "question_type": "scale", "position": 2, "body": "Вопрос 3"}'
```

```http
HTTP/1.1 409 Conflict

{
  "error": {
    "code": "question_limit_reached",
    "message": "В опросе 3104885c-67c1-4748-b5e0-b079a04afec0 уже 2 вопросов, больше добавить нельзя",
    "details": []
  }
}
```

#### Уникальная почта: создание с занятой почтой, 409; замена своей же почтой, 200

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/users \
  -H 'Content-Type: application/json' \
  -d '{"email": "ivanov@example.com", "password": "another-pass-1", "display_name": "Двойник"}'
```

```http
HTTP/1.1 409 Conflict

{
  "error": {
    "code": "email_taken",
    "message": "Почта ivanov@example.com уже занята другим пользователем",
    "details": []
  }
}
```

```bash
curl -i -X PUT http://127.0.0.1:8000/api/v1/users/ae945411-bb83-4722-ae3e-3c00ca56565c \
  -H 'Content-Type: application/json' \
  -d '{"email": "ivanov@example.com", "password": "new-pass-123", "display_name": "Иван И."}'
```

```http
HTTP/1.1 200 OK

{
  "id": "ae945411-bb83-4722-ae3e-3c00ca56565c",
  "email": "ivanov@example.com",
  "display_name": "Иван И.",
  "role": "respondent",
  "created_at": "2026-10-26T23:56:56.386828Z"
}
```

## Задача 2. Внедрение зависимостей, место сборки и подмена хранилища

Сценарий получает репозиторий и значение лимита через конструктор, сам ничего не создаёт и
настроек не читает:

```python
class SurveyService:
    def __init__(self, surveys: SurveyRepository, max_duration: timedelta) -> None:
        self._surveys = surveys
        self._max_duration = max_duration
```

Место сборки в `app/dependencies/`. Хранилище в памяти создаётся один раз на процесс
(`@lru_cache`), репозиторий на базе создаётся на каждый запрос вместе с сессией. Какую
реализацию получит сценарий, решает настройка `STORAGE` (`memory` или `database`, по умолчанию
`database`). Из настроек в сценарий передаётся только нужное значение:

```python
@lru_cache
def get_memory_survey_repository() -> InMemorySurveyRepository:
    """Хранилище в памяти одно на процесс, иначе данные терялись бы между запросами."""
    return InMemorySurveyRepository()


def get_survey_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SurveyRepository:
    """Какой репозиторий получат сценарии, решает одна настройка STORAGE."""
    if settings.storage == StorageBackend.MEMORY:
        return get_memory_survey_repository()
    return SqlAlchemySurveyRepository(session)


def get_survey_service(
    surveys: Annotated[SurveyRepository, Depends(get_survey_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SurveyService:
    return SurveyService(surveys, timedelta(days=settings.max_survey_duration_days))
```

Обработчики получают сценарий через `Depends`:

```python
22:SurveyServiceDep = Annotated[SurveyService, Depends(get_survey_service)]
```

### Подмена хранилища без правки кода

#### STORAGE=memory

Создание опроса:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/surveys \
  -H 'Content-Type: application/json' \
  -d '{"title": "Проверка перезапуска (memory)", "opens_at": "2026-11-01T10:00:00+03:00", "closes_at": "2026-11-10T10:00:00+03:00"}'
```

```http
HTTP/1.1 201 Created
location: /api/v1/surveys/baa5b37e-f9a9-483f-9955-0b1ba15500b4

{
  "id": "baa5b37e-f9a9-483f-9955-0b1ba15500b4",
  "author_id": "00000000-0000-0000-0000-000000000001",
  "status": "draft",
  "created_at": "2026-10-26T23:57:05.091953Z",
  "updated_at": "2026-10-26T23:57:05.091961Z",
  "opens_at": "2026-11-01T10:00:00+03:00",
  "closes_at": "2026-11-10T10:00:00+03:00",
  "title": "Проверка перезапуска (memory)",
  "description": null,
  "anonymous": false
}
```

Приложение остановлено и запущено снова с тем же `STORAGE=memory`. Чтение по идентификатору, ожидается 404:

```bash
curl -i -X GET http://127.0.0.1:8000/api/v1/surveys/baa5b37e-f9a9-483f-9955-0b1ba15500b4
```

```http
HTTP/1.1 404 Not Found

{
  "error": {
    "code": "not_found",
    "message": "Опрос baa5b37e-f9a9-483f-9955-0b1ba15500b4 не найден",
    "details": []
  }
}
```

#### STORAGE=database

Создание опроса:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/surveys \
  -H 'Content-Type: application/json' \
  -d '{"title": "Проверка перезапуска (database)", "opens_at": "2026-11-01T10:00:00+03:00", "closes_at": "2026-11-10T10:00:00+03:00"}'
```

```http
HTTP/1.1 201 Created
location: /api/v1/surveys/95337b8b-d948-4b84-a07a-bf3310ab34b9

{
  "id": "95337b8b-d948-4b84-a07a-bf3310ab34b9",
  "author_id": "00000000-0000-0000-0000-000000000001",
  "status": "draft",
  "created_at": "2026-10-26T23:57:21.390869Z",
  "updated_at": "2026-10-26T23:57:21.390877Z",
  "opens_at": "2026-11-01T10:00:00+03:00",
  "closes_at": "2026-11-10T10:00:00+03:00",
  "title": "Проверка перезапуска (database)",
  "description": null,
  "anonymous": false
}
```

Приложение остановлено и запущено снова с тем же `STORAGE=database`. Чтение по идентификатору, ожидается 200:

```bash
curl -i -X GET http://127.0.0.1:8000/api/v1/surveys/95337b8b-d948-4b84-a07a-bf3310ab34b9
```

```http
HTTP/1.1 200 OK

{
  "id": "95337b8b-d948-4b84-a07a-bf3310ab34b9",
  "author_id": "00000000-0000-0000-0000-000000000001",
  "status": "draft",
  "created_at": "2026-10-26T23:57:21.390869Z",
  "updated_at": "2026-10-26T23:57:21.390877Z",
  "opens_at": "2026-11-01T07:00:00Z",
  "closes_at": "2026-11-10T07:00:00Z",
  "title": "Проверка перезапуска (database)",
  "description": null,
  "anonymous": false
}
```

Те же шаги в Swagger: `docs/img/lab-03/1.PNG` (создание, память), `2.PNG` (чтение до
перезапуска), `3.PNG` (404 после перезапуска), `db-before.PNG` и `db-after.PNG` (база, 200
после перезапуска).

![Память после перезапуска](img/lab-03/3.PNG)

![База после перезапуска](img/lab-03/db-after.PNG)

## Задача 3. Конфигурация

Класс настроек `Settings` в `app/core/config.py` на pydantic-settings, все параметры с типом
и диапазоном. Полный список с умолчаниями приведён в README, раздел «Конфигурация», и в
`.env.example`.

```python
class Settings(BaseSettings):
    """Настройки сервиса. Читаются из переменных окружения и файла `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    max_survey_duration_days: int = Field(
        default=90, ge=1, le=365, description="Максимальная длительность опроса, дни"
    )
    max_questions_per_survey: int = Field(
        default=50, ge=1, le=500, description="Максимальное число вопросов в опросе"
    )
    storage: StorageBackend = Field(
        default=StorageBackend.DATABASE, description="Где хранить данные: memory или database"
    )
    database_url: str = Field(
        default="postgresql+asyncpg://survey:survey@localhost:5432/survey",
        description="Строка подключения SQLAlchemy, драйвер asyncpg",
    )
    sql_echo: bool = Field(default=False, description="Печатать SQL-запросы в консоль")
```

```text
MAX_SURVEY_DURATION_DAYS=90

MAX_QUESTIONS_PER_SURVEY=50

STORAGE=database
DATABASE_URL=postgresql+asyncpg://survey:survey@localhost:5432/survey
SQL_ECHO=false
```

Настройки читаются в `app/main.py` при импорте приложения, поэтому недопустимое значение
останавливает запуск до первого запроса. Отрицательный лимит:

```bash
$ MAX_SURVEY_DURATION_DAYS=-5 uv run uvicorn app.main:app
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
max_survey_duration_days
  Input should be greater than or equal to 1 [type=greater_than_equal, input_value='-5', input_type=str]
```

Строка вместо числа:

```bash
$ MAX_QUESTIONS_PER_SURVEY=abc uv run uvicorn app.main:app
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
max_questions_per_survey
  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='abc', input_type=str]
```

## Задача 4. Модели SQLAlchemy и схема базы

`app/core/database.py` содержит движок (`asyncpg`), фабрику асинхронных сессий и общий
предок `Base`. Движок и фабрика создаются один раз при импорте модуля, вывод SQL включается
настройкой `SQL_ECHO`. Модели описаны через `Mapped` и `mapped_column`, это те же классы,
с которыми работают сценарии и хранилище в памяти. Идентификаторы UUID генерирует
приложение (`default_factory=uuid4`). Вопрос ссылается на опрос внешним ключом, связь
`relationship` объявлена с обеих сторон. У опроса нет внешнего ключа на автора:
аутентификации пока нет, автор подставляется заглушкой, которой нет в таблице пользователей.

```python
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, enum_column
from app.schemas.question import QuestionType

if TYPE_CHECKING:
    from app.models.survey import Survey


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)
    survey_id: Mapped[UUID] = mapped_column(
        ForeignKey("surveys.id", ondelete="CASCADE"), index=True
    )
    question_type: Mapped[QuestionType] = mapped_column(enum_column(QuestionType))
    position: Mapped[int]
    required: Mapped[bool] = mapped_column(default=False)
    body: Mapped[str] = mapped_column(Text)

    survey: Mapped[Survey] = relationship(back_populates="questions", init=False, repr=False)
```

Схема создаётся скриптом `scripts/create_db.py` по `Base.metadata`. Флаг `--recreate`
удаляет таблицы и создаёт заново, потому что `create_all` существующие таблицы не меняет.
Вывод с `SQL_ECHO=true`:

```sql
$ SQL_ECHO=true uv run python -m scripts.create_db --recreate
DROP TABLE questions

DROP TABLE users

DROP TABLE surveys

CREATE TABLE surveys (
	id UUID NOT NULL, 
	author_id UUID NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	description TEXT, 
	anonymous BOOLEAN NOT NULL, 
	opens_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	closes_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

CREATE TABLE users (
	id UUID NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	display_name VARCHAR(100) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
)

CREATE TABLE questions (
	id UUID NOT NULL, 
	survey_id UUID NOT NULL, 
	question_type VARCHAR(32) NOT NULL, 
	position INTEGER NOT NULL, 
	required BOOLEAN NOT NULL, 
	body TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(survey_id) REFERENCES surveys (id) ON DELETE CASCADE
)

CREATE INDEX ix_questions_survey_id ON questions (survey_id)
Таблицы созданы: questions, surveys, users
```

## Задача 5. Репозиторий на сессии

Протокол каждого репозитория содержит только операции, нужные сценариям: например,
`get_by_email` для правила о почте и `count_by_survey` для лимита вопросов. Рядом с
реализацией на словаре лежит реализация на `AsyncSession` с теми же методами:

```python
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
```

Репозиторий вызывает `flush`, но не `commit`. Сессия выдаётся зависимостью с `yield`: одна
сессия и одна транзакция на запрос, фиксация при успехе и откат при исключении до того, как
клиент получит ответ. FastAPI кэширует зависимость в пределах запроса, поэтому сценарий вопросов
получает оба репозитория (вопросов и опросов) на одной сессии.

```python
async def get_session() -> AsyncIterator[AsyncSession]:
    """Одна сессия и одна транзакция на запрос.

    Обработчик отработал без исключения — транзакция фиксируется.
    Обработчик или сценарий подняли исключение — транзакция откатывается,
    и только потом исключение уходит дальше и превращается в ответ.
    """
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
```

Переход на базу оформлен отдельным коммитом `fe7a728`. Сценарии в нём не менялись по логике:
в `use_cases/` удалена одна строка комментария.

```bash
$ git diff --stat 205a73e fe7a728
app/dependencies/questions.py | 21 ++++++++++++++---
 app/dependencies/surveys.py   | 23 +++++++++++++++---
 app/dependencies/users.py     | 16 +++++++++++--
 app/repositories/questions.py | 31 ++++++++++++++++++++++++
 app/repositories/surveys.py   | 55 +++++++++++++++++++++++++++++++++++++++++++
 app/repositories/users.py     | 31 ++++++++++++++++++++++++
 app/use_cases/questions.py    |  1 -
 7 files changed, 169 insertions(+), 9 deletions(-)
```

Все обработчики отвечают теми же кодами и в той же форме, что на словаре: ответы в задаче 1
получены на базе, ответы с `STORAGE=memory` в задаче 2 совпадают по форме.

## Задача 6. SQL-инъекция

Скрипт `scripts/sql_injection.py` создаёт три опроса, ищет опрос по заголовку тремя способами
с обычным значением и со строкой `' OR '1'='1`, затем показывает поиск по подстроке через
`ILIKE` без экранирования и с ним, и удаляет свои данные.

```python
async def find_by_string_concat(session: AsyncSession, title: str) -> list[str]:
    result = await session.execute(text(f"SELECT title FROM surveys WHERE title = '{title}'"))  # noqa: S608
    return list(result.scalars())


async def find_by_text_param(session: AsyncSession, title: str) -> list[str]:
    result = await session.execute(
        text("SELECT title FROM surveys WHERE title = :title"), {"title": title}
    )
    return list(result.scalars())


async def find_by_expression(session: AsyncSession, title: str) -> list[str]:
    query = select(Survey.title).where(Survey.title == title)
    result = await session.execute(query)
    return list(result.scalars())


def escape_like(value: str) -> str:
    # Сначала обратный слеш, иначе он задвоится в уже вставленных \% и \_.
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def find_by_substring(session: AsyncSession, part: str, *, escape: bool) -> list[str]:
    if escape:
        condition = Survey.title.ilike(f"%{escape_like(part)}%", escape="\\")
    else:
        condition = Survey.title.ilike(f"%{part}%")
    result = await session.execute(select(Survey.title).where(condition))
    return list(result.scalars())
```

```text
$ uv run python -m scripts.sql_injection
========== значение: 'inj-0a7d16 Столовая' ==========
--- 1. склейка строки
SELECT title FROM surveys WHERE title = 'inj-0a7d16 Столовая'
[generated in 0.00019s] ()
>>> найдено 1: ['inj-0a7d16 Столовая']
--- 2. text() с параметром
SELECT title FROM surveys WHERE title = $1
[generated in 0.00047s] ('inj-0a7d16 Столовая',)
>>> найдено 1: ['inj-0a7d16 Столовая']
--- 3. выражения SQLAlchemy
SELECT surveys.title 
FROM surveys 
WHERE surveys.title = $1::VARCHAR
[generated in 0.00023s] ('inj-0a7d16 Столовая',)
>>> найдено 1: ['inj-0a7d16 Столовая']
========== значение: "' OR '1'='1" ==========
--- 1. склейка строки
SELECT title FROM surveys WHERE title = '' OR '1'='1'
[generated in 0.00021s] ()
>>> найдено 5: ['Удовлетворённость офисом', 'Проверка перезапуска (database)', 'inj-0a7d16 Удовлетворённость офисом', 'inj-0a7d16 Столовая', 'inj-0a7d16 Парковка']
--- 2. text() с параметром
SELECT title FROM surveys WHERE title = $1
[cached since 0.01433s ago] ("' OR '1'='1",)
>>> найдено 0: []
--- 3. выражения SQLAlchemy
SELECT surveys.title 
FROM surveys 
WHERE surveys.title = $1::VARCHAR
[cached since 0.01154s ago] ("' OR '1'='1",)
>>> найдено 0: []
```

Строки в квадратных скобках печатает SQLAlchemy: это параметры, переданные в базу отдельно
от текста запроса. У способа 1 параметров нет, значение вклеено в текст SQL.

### Что уходит в базу

В первом способе значение вклеивается в текст SQL ещё в Python, и база получает уже готовый
запрос `SELECT title FROM surveys WHERE title = '' OR '1'='1'`. Кавычка из значения закрыла
строковый литерал, остаток значения стал частью условия, а условие `'1'='1'` истинно для любой
строки, поэтому вернулись все опросы таблицы, включая чужие. Во втором и третьем способах в базу
уходит текст запроса с местом для параметра `$1`, одинаковый для любого значения, а само значение
передаётся отдельным сообщением протокола: драйвер asyncpg сначала отправляет запрос на разбор,
затем отдельно привязывает к нему байты значения. К этому моменту PostgreSQL уже разобрал запрос
и знает, что `$1` — одно строковое значение для сравнения с колонкой `title`, поэтому кавычки
в нём ничего не закрывают, и база ищет опрос с заголовком, буквально равным `' OR '1'='1`, и не
находит его. Третий способ под капотом устроен так же, как второй: SQLAlchemy строит из выражения
запрос с параметром `$1::VARCHAR`, только собирает его библиотека, а не программист. Защита во
втором и третьем случае обеспечена разделением кода запроса и данных, а не экранированием кавычек.

### Поиск по подстроке и подстановочные знаки LIKE

```python
def escape_like(value: str) -> str:
    # Сначала обратный слеш, иначе он задвоится в уже вставленных \% и \_.
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def find_by_substring(session: AsyncSession, part: str, *, escape: bool) -> list[str]:
    if escape:
        condition = Survey.title.ilike(f"%{escape_like(part)}%", escape="\\")
    else:
        condition = Survey.title.ilike(f"%{part}%")
    result = await session.execute(select(Survey.title).where(condition))
    return list(result.scalars())
```

```text
========== поиск по подстроке через ILIKE ==========
--- 'Стол', без экранирования
WHERE surveys.title ILIKE $1::VARCHAR
[generated in 0.00022s] ('%Стол%',)
>>> найдено 1: ['inj-0a7d16 Столовая']
--- 'Стол', с экранированием
WHERE surveys.title ILIKE $1::VARCHAR ESCAPE '\'
[generated in 0.00044s] ('%Стол%',)
>>> найдено 1: ['inj-0a7d16 Столовая']
--- '%', без экранирования
WHERE surveys.title ILIKE $1::VARCHAR
[cached since 0.01045s ago] ('%%%',)
>>> найдено 5: ['Удовлетворённость офисом', 'Проверка перезапуска (database)', 'inj-0a7d16 Удовлетворённость офисом', 'inj-0a7d16 Столовая', 'inj-0a7d16 Парковка']
--- '%', с экранированием
WHERE surveys.title ILIKE $1::VARCHAR ESCAPE '\'
[cached since 0.008252s ago] ('%\\%%',)
>>> найдено 0: []
--- '_', без экранирования
WHERE surveys.title ILIKE $1::VARCHAR
[cached since 0.01642s ago] ('%_%',)
>>> найдено 5: ['Удовлетворённость офисом', 'Проверка перезапуска (database)', 'inj-0a7d16 Удовлетворённость офисом', 'inj-0a7d16 Столовая', 'inj-0a7d16 Парковка']
--- '_', с экранированием
WHERE surveys.title ILIKE $1::VARCHAR ESCAPE '\'
[cached since 0.01378s ago] ('%\\_%',)
>>> найдено 0: []
[generated in 0.00023s] ('inj-0a7d16',)
```

Параметр защищает структуру запроса: в обоих режимах запрос уходит с `$1`, SQL-инъекции нет.
Но `%` и `_` внутри значения остаются подстановочными знаками `LIKE`, и клиент, приславший `%`,
получает все строки таблицы. Экранирование (`\%`, `\_` и `ESCAPE '\'`) делает их буквальными
символами, и такой запрос находит только заголовки, где эти символы действительно есть.
