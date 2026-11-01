# Лабораторная работа 2. Контракт API, схемы и валидация

Сервис: survey-service, приложение FastAPI в каталоге `app/`. Сервер из первой работы
остался в каталоге `rawhttp/`. Хранилище: словари в памяти процесса (`app/storage.py`),
ключ словаря - UUID объекта.

Запуск:

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Ниже приведены запросы к запущенному сервису и ответы на них. Из заголовков
ответа оставлены только `content-type` и `location`.

## Задача 1. Карта ресурсов

Таблица маршрутов со смыслом, кодом успеха и кодами ошибок для всех операций приведена
в [README.md](../README.md#маршруты), раздел «Маршруты». Покрыты три сущности:
пользователи (`/api/v1/users`), опросы (`/api/v1/surveys`) и вопросы (`/api/v1/questions`).
Эти же коды объявлены в `responses` каждой операции и видны в Swagger (задача 5).

## Задача 2. Полный набор операций для трёх сущностей

Выбраны сущности `User`, `Survey` и `Question`. Вопрос ссылается на опрос внешним ключом
`survey_id`, опрос ссылается на автора через `author_id`.

Структура:

```text
app/
  main.py              приложение, метаданные OpenAPI, include_router, /health
  errors.py            обработчики исключений (задача 6)
  storage.py           словари-хранилища
  api/responses.py     описания ответов об ошибках для OpenAPI
  api/v1/users.py      роутер пользователей
  api/v1/surveys.py    роутер опросов
  api/v1/questions.py  роутер вопросов
  schemas/             входные и выходные схемы Pydantic
  models/              внутренние модели (все поля, включая служебные)
```

Каждый роутер создан через `APIRouter(prefix=..., tags=[...])` и подключён в `main.py`
через `include_router`. В `main.py` остался только маршрут `/health`. Идентификаторы
генерирует сервер (`Field(default_factory=uuid4)` во внутренней модели).

Полный цикл показан на опросах, для пользователей и вопросов - создание и характерные
ошибки.

### Опросы: создание, 201 и заголовок Location

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/surveys \
  -H 'Content-Type: application/json' \
  -d '{
  "title": "Удовлетворённость сотрудников офисом",
  "description": "Ежегодный опрос об условиях работы в офисе",
  "anonymous": true,
  "opens_at": "2026-10-01T09:00:00+03:00",
  "closes_at": "2026-10-15T18:00:00+03:00"
}'
```

```http
HTTP/1.1 201 Created
content-type: application/json
location: /api/v1/surveys/f0291ab6-d9f2-4b05-ba7c-2ac587be77d6

{
  "id": "f0291ab6-d9f2-4b05-ba7c-2ac587be77d6",
  "author_id": "00000000-0000-0000-0000-000000000001",
  "status": "draft",
  "created_at": "2026-09-29T00:55:01.716249Z",
  "updated_at": "2026-09-29T00:55:01.716254Z",
  "opens_at": "2026-10-01T09:00:00+03:00",
  "closes_at": "2026-10-15T18:00:00+03:00",
  "title": "Удовлетворённость сотрудников офисом",
  "description": "Ежегодный опрос об условиях работы в офисе",
  "anonymous": true
}
```

### Опросы: чтение одного объекта, 200

```bash
curl -i -X GET http://127.0.0.1:8000/api/v1/surveys/f0291ab6-d9f2-4b05-ba7c-2ac587be77d6
```

```http
HTTP/1.1 200 OK
content-type: application/json

{
  "id": "f0291ab6-d9f2-4b05-ba7c-2ac587be77d6",
  "author_id": "00000000-0000-0000-0000-000000000001",
  "status": "draft",
  "created_at": "2026-09-29T00:55:01.716249Z",
  "updated_at": "2026-09-29T00:55:01.716254Z",
  "opens_at": "2026-10-01T09:00:00+03:00",
  "closes_at": "2026-10-15T18:00:00+03:00",
  "title": "Удовлетворённость сотрудников офисом",
  "description": "Ежегодный опрос об условиях работы в офисе",
  "anonymous": true
}
```

### Опросы: чтение списка, 200

```bash
curl -i -X GET http://127.0.0.1:8000/api/v1/surveys
```

```http
HTTP/1.1 200 OK
content-type: application/json

[
  {
    "id": "f0291ab6-d9f2-4b05-ba7c-2ac587be77d6",
    "author_id": "00000000-0000-0000-0000-000000000001",
    "status": "draft",
    "created_at": "2026-09-29T00:55:01.716249Z",
    "updated_at": "2026-09-29T00:55:01.716254Z",
    "opens_at": "2026-10-01T09:00:00+03:00",
    "closes_at": "2026-10-15T18:00:00+03:00",
    "title": "Удовлетворённость сотрудников офисом",
    "description": "Ежегодный опрос об условиях работы в офисе",
    "anonymous": true
  }
]
```

### Опросы: полная замена, 200 с новым состоянием

`id`, `author_id`, `status` и `created_at` сохранились, `updated_at` обновился.
Необязательное поле `description` не передано и сбросилось в `null`, как и положено
при полной замене.

```bash
curl -i -X PUT http://127.0.0.1:8000/api/v1/surveys/f0291ab6-d9f2-4b05-ba7c-2ac587be77d6 \
  -H 'Content-Type: application/json' \
  -d '{
  "title": "Удовлетворённость сотрудников офисом 2026",
  "anonymous": false,
  "opens_at": "2026-10-01T09:00:00+03:00",
  "closes_at": "2026-10-20T18:00:00+03:00"
}'
```

```http
HTTP/1.1 200 OK
content-type: application/json

{
  "id": "f0291ab6-d9f2-4b05-ba7c-2ac587be77d6",
  "author_id": "00000000-0000-0000-0000-000000000001",
  "status": "draft",
  "created_at": "2026-09-29T00:55:01.716249Z",
  "updated_at": "2026-09-29T00:55:01.738728Z",
  "opens_at": "2026-10-01T09:00:00+03:00",
  "closes_at": "2026-10-20T18:00:00+03:00",
  "title": "Удовлетворённость сотрудников офисом 2026",
  "description": null,
  "anonymous": false
}
```

### Пользователи: создание, 201

В ответе нет ни пароля, ни его хеша. Роль назначил сервер.

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/users \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "ivanov@example.com",
  "password": "correct-horse-42",
  "display_name": "Иван Иванов"
}'
```

```http
HTTP/1.1 201 Created
content-type: application/json
location: /api/v1/users/0d666a67-f762-4075-81bb-daed7b264a4f

{
  "id": "0d666a67-f762-4075-81bb-daed7b264a4f",
  "email": "ivanov@example.com",
  "display_name": "Иван Иванов",
  "role": "respondent",
  "created_at": "2026-09-29T00:55:01.747463Z"
}
```

### Пользователи: повторная почта, 409

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/users \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "ivanov@example.com",
  "password": "another-pass-1",
  "display_name": "Двойник"
}'
```

```http
HTTP/1.1 409 Conflict
content-type: application/json

{
  "error": {
    "code": "conflict",
    "message": "Почта занята",
    "details": []
  }
}
```

### Вопросы: создание в существующем опросе, 201

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/questions \
  -H 'Content-Type: application/json' \
  -d '{
  "survey_id": "f0291ab6-d9f2-4b05-ba7c-2ac587be77d6",
  "question_type": "scale",
  "position": 0,
  "required": true,
  "body": "Оцените удобство рабочего места от 1 до 10"
}'
```

```http
HTTP/1.1 201 Created
content-type: application/json
location: /api/v1/questions/97b0d7ba-0536-4b04-ae7e-8aa134e29c38

{
  "id": "97b0d7ba-0536-4b04-ae7e-8aa134e29c38",
  "survey_id": "f0291ab6-d9f2-4b05-ba7c-2ac587be77d6",
  "question_type": "scale",
  "position": 0,
  "required": true,
  "body": "Оцените удобство рабочего места от 1 до 10"
}
```

### Вопросы: создание в несуществующем опросе, 404

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/questions \
  -H 'Content-Type: application/json' \
  -d '{
  "survey_id": "00000000-0000-0000-0000-00000000dead",
  "question_type": "free_text",
  "position": 1,
  "body": "Что улучшить?"
}'
```

```http
HTTP/1.1 404 Not Found
content-type: application/json

{
  "error": {
    "code": "not_found",
    "message": "Опрос не найден",
    "details": []
  }
}
```

### Удаление, 204 без тела, затем чтение, 404

```bash
curl -i -X DELETE http://127.0.0.1:8000/api/v1/questions/97b0d7ba-0536-4b04-ae7e-8aa134e29c38
```

```http
HTTP/1.1 204 No Content
content-type: application/json
```

```bash
curl -i -X GET http://127.0.0.1:8000/api/v1/questions/97b0d7ba-0536-4b04-ae7e-8aa134e29c38
```

```http
HTTP/1.1 404 Not Found
content-type: application/json

{
  "error": {
    "code": "not_found",
    "message": "Вопрос не найден",
    "details": []
  }
}
```

### Некорректный формат идентификатора в пути, 422

```bash
curl -i -X GET http://127.0.0.1:8000/api/v1/users/not-a-uuid
```

```http
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{
  "error": {
    "code": "validation_error",
    "message": "Запрос не прошёл проверку",
    "details": [
      {
        "field": "path.user_id",
        "rule": "uuid_parsing",
        "message": "Input should be a valid UUID, invalid character: found `n` at 1"
      }
    ]
  }
}
```

## Задача 3. Раздельные схемы Pydantic и ограничения полей

Для каждой сущности описаны три схемы (`app/schemas/`):

| Сущность | Создание | Замена | Ответ |
|---|---|---|---|
| User | `UserCreate` | `UserReplace` | `UserRead` |
| Survey | `SurveyCreate` | `SurveyReplace` | `SurveyRead` |
| Question | `QuestionCreate` | `QuestionReplace` | `QuestionRead` |

- Все входные схемы наследуются от базового класса с `model_config = ConfigDict(extra="forbid")`.
- `QuestionCreate` содержит `survey_id`, а `QuestionReplace` нет: вопрос нельзя перенести
  в другой опрос заменой.
- Даты описаны типом `AwareDatetime`: время без часового пояса отклоняется с 422, иначе
  сравнение наивной и осведомлённой даты привело бы к 500.
- Ограничения: длина строк (`min_length`/`max_length`), пароль не короче 8 символов,
  `EmailStr` для почты, `position` в диапазоне 0–100, перечисления для статуса, роли
  и типа вопроса.
- Валидатор поля: `@field_validator` запрещает строки из одних пробелов в `title`,
  `display_name` и `body`.
- Валидатор модели: `@model_validator(mode="after")` в `SurveyBase` проверяет, что
  `closes_at` строго позже `opens_at`. Оба валидатора поднимают `ValueError`, FastAPI
  превращает его в 422.
- Каждый маршрут объявляет `response_model`, обработчики возвращают схему ответа
  (`XxxRead.model_validate(obj, from_attributes=True)`), а не словарь.

### Запрос с лишним полем

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/surveys \
  -H 'Content-Type: application/json' \
  -d '{
  "title": "Удовлетворённость сотрудников офисом",
  "description": "Ежегодный опрос об условиях работы в офисе",
  "anonymous": true,
  "opens_at": "2026-10-01T09:00:00+03:00",
  "closes_at": "2026-10-15T18:00:00+03:00",
  "priority": "high"
}'
```

```http
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{
  "error": {
    "code": "validation_error",
    "message": "Запрос не прошёл проверку",
    "details": [
      {
        "field": "body.priority",
        "rule": "extra_forbidden",
        "message": "Extra inputs are not permitted"
      }
    ]
  }
}
```

### Строка длиннее максимума

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/surveys \
  -H 'Content-Type: application/json' \
  -d '{
  "title": "Очень длинный заголовок опроса Очень длинный заголовок опроса Очень длинный заголовок опроса Очень длинный заголовок опроса Очень длинный заголовок опроса ",
  "description": "Ежегодный опрос об условиях работы в офисе",
  "anonymous": true,
  "opens_at": "2026-10-01T09:00:00+03:00",
  "closes_at": "2026-10-15T18:00:00+03:00"
}'
```

```http
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{
  "error": {
    "code": "validation_error",
    "message": "Запрос не прошёл проверку",
    "details": [
      {
        "field": "body.title",
        "rule": "string_too_long",
        "message": "String should have at most 100 characters"
      }
    ]
  }
}
```

### Нарушение межполевого правила

Поле `field` равно `body`: валидатор модели проверяет объект целиком, а не одно поле.

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/surveys \
  -H 'Content-Type: application/json' \
  -d '{
  "title": "Удовлетворённость сотрудников офисом",
  "description": "Ежегодный опрос об условиях работы в офисе",
  "anonymous": true,
  "opens_at": "2026-10-15T18:00:00+03:00",
  "closes_at": "2026-10-01T09:00:00+03:00"
}'
```

```http
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{
  "error": {
    "code": "validation_error",
    "message": "Запрос не прошёл проверку",
    "details": [
      {
        "field": "body",
        "rule": "value_error",
        "message": "Value error, Опрос должен закрываться после открытия"
      }
    ]
  }
}
```

## Задача 4. Защита от массового присвоения

Служебные поля есть только во внутренних моделях (`app/models/`) и в схемах ответа, во
входных схемах их нет:

| Сущность | Служебные поля | Кто задаёт |
|---|---|---|
| User | `id`, `role`, `created_at`, `password_hash` | сервер: UUID, роль `respondent`, текущее время, хеш пароля |
| Survey | `id`, `author_id`, `status`, `created_at`, `updated_at` | сервер: UUID, заглушка автора, статус `draft`, время |
| Question | `id` | сервер: UUID |

Аутентификации пока нет, поэтому автор опроса подставляется константой
`STUB_AUTHOR_ID = 00000000-0000-0000-0000-000000000001` в `app/api/v1/surveys.py`.

Схемы ответа перечисляют поля явно и не наследуются от внутренних моделей. `UserRead` не
содержит `password_hash`, поэтому хеш пароля никогда не попадает в ответ.

### Запрос со служебными полями к безопасному маршруту, 422

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/users \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "attacker@example.com",
  "password": "12345678",
  "display_name": "Attacker",
  "role": "admin"
}'
```

```http
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{
  "error": {
    "code": "validation_error",
    "message": "Запрос не прошёл проверку",
    "details": [
      {
        "field": "body.role",
        "rule": "extra_forbidden",
        "message": "Extra inputs are not permitted"
      }
    ]
  }
}
```

То же для опроса: клиент пытается сразу опубликовать опрос от чужого имени.

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/surveys \
  -H 'Content-Type: application/json' \
  -d '{
  "title": "Удовлетворённость сотрудников офисом",
  "description": "Ежегодный опрос об условиях работы в офисе",
  "anonymous": true,
  "opens_at": "2026-10-01T09:00:00+03:00",
  "closes_at": "2026-10-15T18:00:00+03:00",
  "status": "published",
  "author_id": "00000000-0000-0000-0000-0000000000aa"
}'
```

```http
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{
  "error": {
    "code": "validation_error",
    "message": "Запрос не прошёл проверку",
    "details": [
      {
        "field": "body.status",
        "rule": "extra_forbidden",
        "message": "Extra inputs are not permitted"
      },
      {
        "field": "body.author_id",
        "rule": "extra_forbidden",
        "message": "Extra inputs are not permitted"
      }
    ]
  }
}
```

### Уязвимый вариант

В `app/api/v1/users.py` добавлен маршрут `POST /api/v1/users/vuln` (помечен в Swagger
как `deprecated` и `[VULN]`). Он принимает тело как `dict` и распаковывает его во
внутреннюю модель:

```python
async def create_user_vuln(payload: dict, response: Response) -> UserRead:
    password = payload.pop("password")
    user = User(**payload, password_hash=hash_password(password))
```

Тот же запрос проходит, и роль `admin` устанавливается значением из тела:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/users/vuln \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "attacker@example.com",
  "password": "12345678",
  "display_name": "Attacker",
  "role": "admin"
}'
```

```http
HTTP/1.1 201 Created
content-type: application/json
location: /api/v1/users/34649cfc-25d6-4988-93ad-d03c8988fc1f

{
  "id": "34649cfc-25d6-4988-93ad-d03c8988fc1f",
  "email": "attacker@example.com",
  "display_name": "Attacker",
  "role": "admin",
  "created_at": "2026-09-29T00:55:01.802536Z"
}
```

**Что получил бы злоумышленник.** Любой анонимный клиент при регистрации назначает себе
роль администратора сервиса опросов. Администратор может закрывать и удалять чужие опросы,
менять формулировки вопросов уже после начала голосования, а в дальнейшем - удалять голоса
и видеть, кто как ответил в неанонимных опросах. То есть злоумышленник может подделать
результаты любого опроса. Кроме того, через поле `id` из тела можно перезаписать
существующего пользователя в хранилище. В безопасном варианте это невозможно: `UserCreate`
не содержит служебных полей, а `extra="forbid"` отклоняет их с 422.

## Задача 5. Автодокументация

- Метаданные приложения в `app/main.py`: название `Survey Service API`, версия `0.2.0`,
  описание из трёх предложений.
- Теги объявлены через `openapi_tags` с описаниями: `health`, `users`, `surveys`,
  `questions`. Каждый роутер принадлежит ровно одному тегу.
- У каждой операции заполнены `summary` (одна строка) и `description` (поведение и
  условия отказа). Коды ошибок описаны через `responses` со схемой `ErrorResponse` и
  примером тела для каждого кода (`app/api/responses.py`).
- Примеры значений заданы через `examples` в `Field` во всех входных схемах.

Схема: http://127.0.0.1:8000/openapi.json, Swagger UI: http://127.0.0.1:8000/docs.
Скриншоты Swagger приложены в PDF-версии отчёта.

Перечень операций из сгенерированной схемы OpenAPI:

| Метод | Путь | Тег | summary | Коды в responses |
|---|---|---|---|---|
| GET | `/api/v1/users` | users | Список пользователей | 200 |
| POST | `/api/v1/users` | users | Зарегистрировать пользователя | 201, 409, 422 |
| POST | `/api/v1/users/vuln` | users | [VULN] Регистрация с массовым присвоением | 201, 422 |
| GET | `/api/v1/users/{user_id}` | users | Прочитать пользователя | 200, 404, 422 |
| PUT | `/api/v1/users/{user_id}` | users | Заменить пользователя целиком | 200, 404, 409, 422 |
| DELETE | `/api/v1/users/{user_id}` | users | Удалить пользователя | 204, 404, 422 |
| GET | `/api/v1/surveys` | surveys | Список опросов | 200 |
| POST | `/api/v1/surveys` | surveys | Создать опрос | 201, 422 |
| GET | `/api/v1/surveys/{survey_id}` | surveys | Прочитать опрос | 200, 404, 422 |
| PUT | `/api/v1/surveys/{survey_id}` | surveys | Заменить опрос целиком | 200, 404, 422 |
| DELETE | `/api/v1/surveys/{survey_id}` | surveys | Удалить опрос | 204, 404, 422 |
| GET | `/api/v1/questions` | questions | Список вопросов | 200 |
| POST | `/api/v1/questions` | questions | Добавить вопрос в опрос | 201, 404, 422 |
| GET | `/api/v1/questions/{question_id}` | questions | Прочитать вопрос | 200, 404, 422 |
| PUT | `/api/v1/questions/{question_id}` | questions | Заменить вопрос целиком | 200, 404, 422 |
| DELETE | `/api/v1/questions/{question_id}` | questions | Удалить вопрос | 204, 404, 422 |
| GET | `/health` | health | Проверка состояния | 200 |

## Задача 6. Единый формат ответа об ошибке

Все ошибки приводятся к форме:

```json
{"error": {"code": "...", "message": "...", "details": [{"field": "...", "rule": "...", "message": "..."}]}}
```

В `app/errors.py` зарегистрированы два обработчика: на `RequestValidationError` и на
`StarletteHTTPException` (он ловит и `HTTPException` из маршрутов, и 404/405 самого
роутинга). Тело формирует одна функция `error_body`, которая строит его через схемы
`ErrorResponse`/`ErrorInfo`/`ErrorDetail` из `app/schemas/errors.py`. Эти же схемы
использованы в документации, поэтому формат описан в одном месте. `details` всегда список,
для ошибок без позиций пустой.

### 422 на некорректном теле

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/users \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "not-an-email",
  "password": "1",
  "display_name": "A"
}'
```

```http
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{
  "error": {
    "code": "validation_error",
    "message": "Запрос не прошёл проверку",
    "details": [
      {
        "field": "body.email",
        "rule": "value_error",
        "message": "value is not a valid email address: An email address must have an @-sign."
      },
      {
        "field": "body.password",
        "rule": "string_too_short",
        "message": "String should have at least 8 characters"
      }
    ]
  }
}
```

### 404 на несуществующем идентификаторе

```bash
curl -i -X GET http://127.0.0.1:8000/api/v1/surveys/00000000-0000-0000-0000-00000000dead
```

```http
HTTP/1.1 404 Not Found
content-type: application/json

{
  "error": {
    "code": "not_found",
    "message": "Опрос не найден",
    "details": []
  }
}
```

### 422 на некорректном параметре

```bash
curl -i -X GET http://127.0.0.1:8000/api/v1/surveys/abc
```

```http
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{
  "error": {
    "code": "validation_error",
    "message": "Запрос не прошёл проверку",
    "details": [
      {
        "field": "path.survey_id",
        "rule": "uuid_parsing",
        "message": "Input should be a valid UUID, invalid length: expected length 32 for simple format, found 3"
      }
    ]
  }
}
```

### 404 на несуществующем маршруте

```bash
curl -i -X GET http://127.0.0.1:8000/api/v1/nothing
```

```http
HTTP/1.1 404 Not Found
content-type: application/json

{
  "error": {
    "code": "not_found",
    "message": "Not Found",
    "details": []
  }
}
```

У всех ответов совпадает структура верхнего уровня `{"error": {"code", "message",
"details"}}`. В телах нет трассировки стека, имён файлов проекта и текста исходных
исключений. Поле `input` из ошибок Pydantic намеренно не передаётся клиенту, чтобы не
возвращать ему присланные данные, например пароль.

## Задача 7. Частичное обновление (PATCH)

Метод `PATCH` добавлен для вопросов (`/api/v1/questions/{question_id}`) и опросов
(`/api/v1/surveys/{survey_id}`).

Для частичного обновления описаны отдельные схемы `QuestionPatch` и `SurveyPatch`. Они не
наследуются от базовых схем: в `QuestionBase` и `SurveyBase` поля обязательные, и
наследник получил бы их обязательными, а в PATCH любое поле можно не передавать.
Ограничения те же, что при создании: длины строк, диапазон `position` 0–100, запрет
строк из одних пробелов, `AwareDatetime` для дат, `extra="forbid"`.

Поля, которые не могут быть пустыми, объявлены как `position: int = None`, а не
`int | None`. Значение по умолчанию Pydantic не проверяет, поэтому непереданное поле
ошибки не даёт, а явно переданный `null` отклоняется с 422 как значение неверного типа.
Поле `description` у опроса допускает пустое значение, поэтому там тип `str | None`, и
`null` очищает описание.

Изменения применяются так:

```python
changes = payload.model_dump(exclude_unset=True)
updated = question.model_copy(update=changes)
```

`exclude_unset=True` оставляет только поля, которые клиент действительно прислал.
`exclude_none=True` не подходит: он не отличает «поле не передано» от «поле передано как
`null`», и запрос `{"description": null}` к опросу молча ничего бы не изменил.

У опроса правило «`closes_at` позже `opens_at`» проверяется после слияния с текущими
значениями: в PATCH может прийти только одна из дат, и валидатору модели сравнивать её
не с чем. Нарушение возвращается через `RequestValidationError`, поэтому ответ имеет
общий формат ошибки валидации.

### Создание вопроса, 201

Предварительно создан опрос `75e0b0b0-16b8-49d8-91d1-b9b14610b405`.

```bash
curl -i -X POST http://127.0.0.1:8005/api/v1/questions \
  -H 'Content-Type: application/json' \
  -d '{
  "survey_id": "75e0b0b0-16b8-49d8-91d1-b9b14610b405",
  "question_type": "scale",
  "position": 1,
  "required": false,
  "body": "Насколько удобен офис?"
}'
```

```http
HTTP/1.1 201 Created
content-type: application/json
location: /api/v1/questions/dac439ae-50eb-4dda-b029-a78f4ae3969c

{
  "id": "dac439ae-50eb-4dda-b029-a78f4ae3969c",
  "survey_id": "75e0b0b0-16b8-49d8-91d1-b9b14610b405",
  "question_type": "scale",
  "position": 1,
  "required": false,
  "body": "Насколько удобен офис?"
}
```

### PATCH одного поля, 200

Передано только поле `required`.

```bash
curl -i -X PATCH http://127.0.0.1:8005/api/v1/questions/dac439ae-50eb-4dda-b029-a78f4ae3969c \
  -H 'Content-Type: application/json' \
  -d '{"required": true}'
```

```http
HTTP/1.1 200 OK
content-type: application/json

{
  "id": "dac439ae-50eb-4dda-b029-a78f4ae3969c",
  "survey_id": "75e0b0b0-16b8-49d8-91d1-b9b14610b405",
  "question_type": "scale",
  "position": 1,
  "required": true,
  "body": "Насколько удобен офис?"
}
```

### Чтение после PATCH, 200

Изменилось только `required`. Поля `question_type`, `position` и `body` сохранили
прежние значения.

```bash
curl -i -X GET http://127.0.0.1:8005/api/v1/questions/dac439ae-50eb-4dda-b029-a78f4ae3969c
```

```http
HTTP/1.1 200 OK
content-type: application/json

{
  "id": "dac439ae-50eb-4dda-b029-a78f4ae3969c",
  "survey_id": "75e0b0b0-16b8-49d8-91d1-b9b14610b405",
  "question_type": "scale",
  "position": 1,
  "required": true,
  "body": "Насколько удобен офис?"
}
```

### null в поле, которое не может быть пустым, 422

```bash
curl -i -X PATCH http://127.0.0.1:8005/api/v1/questions/dac439ae-50eb-4dda-b029-a78f4ae3969c \
  -H 'Content-Type: application/json' \
  -d '{"required": null}'
```

```http
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{
  "error": {
    "code": "validation_error",
    "message": "Запрос не прошёл проверку",
    "details": [
      {
        "field": "body.required",
        "rule": "bool_type",
        "message": "Input should be a valid boolean"
      }
    ]
  }
}
```

### Очистка описания опроса через null, 200

Здесь видна разница между `exclude_unset` и `exclude_none`: `description` стал `null`,
остальные поля опроса не изменились, `updated_at` обновился.

```bash
curl -i -X PATCH http://127.0.0.1:8005/api/v1/surveys/75e0b0b0-16b8-49d8-91d1-b9b14610b405 \
  -H 'Content-Type: application/json' \
  -d '{"description": null}'
```

```http
HTTP/1.1 200 OK
content-type: application/json

{
  "id": "75e0b0b0-16b8-49d8-91d1-b9b14610b405",
  "author_id": "00000000-0000-0000-0000-000000000001",
  "status": "draft",
  "created_at": "2026-10-06T13:01:32.677479Z",
  "updated_at": "2026-10-06T13:01:32.859734Z",
  "opens_at": "2026-10-01T09:00:00+03:00",
  "closes_at": "2026-10-15T18:00:00+03:00",
  "title": "Удовлетворённость офисом",
  "description": null,
  "anonymous": false
}
```

### Нарушение правила дат после слияния, 422

Передана только `closes_at`, и она раньше сохранённой `opens_at`.

```bash
curl -i -X PATCH http://127.0.0.1:8005/api/v1/surveys/75e0b0b0-16b8-49d8-91d1-b9b14610b405 \
  -H 'Content-Type: application/json' \
  -d '{"closes_at": "2026-09-01T00:00:00+03:00"}'
```

```http
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{
  "error": {
    "code": "validation_error",
    "message": "Запрос не прошёл проверку",
    "details": [
      {
        "field": "body.closes_at",
        "rule": "value_error",
        "message": "Опрос должен закрываться после открытия"
      }
    ]
  }
}
```

## Задача 8. Пагинация, фильтрация и сортировка списка

Приведён в порядок маршрут `GET /api/v1/surveys`. Все параметры описаны через `Query`
с декларативными ограничениями и видны в Swagger:

| Параметр | Тип | По умолчанию | Ограничение | Смысл |
|---|---|---|---|---|
| `limit` | `int` | 20 | от 1 до 100 | размер страницы |
| `offset` | `int` | 0 | не меньше 0 | сколько опросов пропустить |
| `status` | `SurveyStatus` | не задан | `draft`, `published`, `closed` | фильтр по значению из перечисления |
| `opens_from` | `AwareDatetime` | не задан | дата с часовым поясом | нижняя граница даты открытия (включительно) |
| `opens_to` | `AwareDatetime` | не задан | дата с часовым поясом | верхняя граница даты открытия (включительно) |
| `sort_by` | `SurveySortField` | `created_at` | `created_at`, `opens_at`, `closes_at`, `title` | поле сортировки |
| `order` | `SortOrder` | `asc` | `asc`, `desc` | направление сортировки |

Порядок обработки: сначала фильтры, затем сортировка, затем срез `[offset:offset + limit]`.
Если обрезать страницу до сортировки, вторая страница не будет продолжением первой.

Поле сортировки принимается только как элемент перечисления `SurveySortField`. Произвольная
строка отклоняется FastAPI с 422 ещё до вызова обработчика, поэтому в хранилище (а после
перехода на БД - в `ORDER BY`) может попасть только одно из четырёх известных полей.

Параметр фильтра по статусу в коде назван `status_filter` с `alias="status"`, чтобы не
перекрывать импорт `fastapi.status`. В URL он называется `status`.

### limit=0, 422

```bash
curl -i "http://127.0.0.1:8005/api/v1/surveys?limit=0"
```

```http
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{
  "error": {
    "code": "validation_error",
    "message": "Запрос не прошёл проверку",
    "details": [
      {
        "field": "query.limit",
        "rule": "greater_than_equal",
        "message": "Input should be greater than or equal to 1"
      }
    ]
  }
}
```

### limit=1000, 422

```bash
curl -i "http://127.0.0.1:8005/api/v1/surveys?limit=1000"
```

```http
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{
  "error": {
    "code": "validation_error",
    "message": "Запрос не прошёл проверку",
    "details": [
      {
        "field": "query.limit",
        "rule": "less_than_equal",
        "message": "Input should be less than or equal to 100"
      }
    ]
  }
}
```

### offset=-1, 422

```bash
curl -i "http://127.0.0.1:8005/api/v1/surveys?offset=-1"
```

```http
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{
  "error": {
    "code": "validation_error",
    "message": "Запрос не прошёл проверку",
    "details": [
      {
        "field": "query.offset",
        "rule": "greater_than_equal",
        "message": "Input should be greater than or equal to 0"
      }
    ]
  }
}
```

### sort_by с недопустимым значением, 422

```bash
curl -i "http://127.0.0.1:8005/api/v1/surveys?sort_by=password"
```

```http
HTTP/1.1 422 Unprocessable Content
content-type: application/json

{
  "error": {
    "code": "validation_error",
    "message": "Запрос не прошёл проверку",
    "details": [
      {
        "field": "query.sort_by",
        "rule": "enum",
        "message": "Input should be 'created_at', 'opens_at', 'closes_at' or 'title'"
      }
    ]
  }
}
```

### Две страницы подряд

В хранилище по два опроса с одинаковым названием, поэтому при сортировке по `title` на
первой странице оба «Опрос 1», на второй оба «Опрос 2». Идентификаторы всех четырёх
объектов различны, то есть вторая страница не повторяет элементы первой.

```bash
curl -i "http://127.0.0.1:8005/api/v1/surveys?limit=2&offset=0&sort_by=title"
```

```http
HTTP/1.1 200 OK
content-type: application/json

[
  {
    "id": "8acd7d63-f921-474a-938a-f477ae66a06d",
    "author_id": "00000000-0000-0000-0000-000000000001",
    "status": "draft",
    "created_at": "2026-10-06T12:58:34.943451Z",
    "updated_at": "2026-10-06T12:58:34.943456Z",
    "opens_at": "2026-11-01T10:00:00Z",
    "closes_at": "2026-12-01T10:00:00Z",
    "title": "Опрос 1",
    "description": null,
    "anonymous": false
  },
  {
    "id": "e43a1626-436e-4c39-9daa-bc6a1992730c",
    "author_id": "00000000-0000-0000-0000-000000000001",
    "status": "draft",
    "created_at": "2026-10-06T12:58:56.172208Z",
    "updated_at": "2026-10-06T12:58:56.172212Z",
    "opens_at": "2026-11-01T10:00:00Z",
    "closes_at": "2026-12-01T10:00:00Z",
    "title": "Опрос 1",
    "description": null,
    "anonymous": false
  }
]
```

```bash
curl -i "http://127.0.0.1:8005/api/v1/surveys?limit=2&offset=2&sort_by=title"
```

```http
HTTP/1.1 200 OK
content-type: application/json

[
  {
    "id": "03117dfa-bb5e-44ff-a17f-ca064ddd7bfb",
    "author_id": "00000000-0000-0000-0000-000000000001",
    "status": "draft",
    "created_at": "2026-10-06T12:58:34.953524Z",
    "updated_at": "2026-10-06T12:58:34.953529Z",
    "opens_at": "2026-11-02T10:00:00Z",
    "closes_at": "2026-12-01T10:00:00Z",
    "title": "Опрос 2",
    "description": null,
    "anonymous": false
  },
  {
    "id": "1a43ae2a-d697-4018-8c35-7a8f747dca1d",
    "author_id": "00000000-0000-0000-0000-000000000001",
    "status": "draft",
    "created_at": "2026-10-06T12:58:56.183522Z",
    "updated_at": "2026-10-06T12:58:56.183529Z",
    "opens_at": "2026-11-02T10:00:00Z",
    "closes_at": "2026-12-01T10:00:00Z",
    "title": "Опрос 2",
    "description": null,
    "anonymous": false
  }
]
```

## Задача 9. Версионирование API через префикс пути

Сущность `Survey` выставлена в двух версиях: `/api/v1/surveys` и `/api/v2/surveys`.

**Изменение во второй версии** — схлопывание двух полей в объект. Даты открытия и
закрытия, которые в v1 были отдельными полями верхнего уровня, в v2 собраны в объект
`schedule`:

```text
v1:  "opens_at": "...", "closes_at": "..."
v2:  "schedule": {"opens_at": "...", "closes_at": "..."}
```

Изменение несовместимое: клиент v1, читающий `response["opens_at"]`, на ответе v2 не
найдёт поля. Поэтому оно выпущено отдельной версией, а v1 продолжает работать без
изменений.

**Что общее, а что своё у каждой версии:**

| | v1 | v2 |
|---|---|---|
| Хранилище | `surveys` из `app/storage.py` | то же |
| Внутренняя модель | `Survey` из `app/models/survey.py` | та же |
| Поиск объекта | `get_survey_or_404` | та же функция, импортирована из v1 |
| Схема ответа | `SurveyRead` | `SurveyReadV2` со вложенной `SurveySchedule` |
| Преобразование | `SurveyRead.model_validate(survey, from_attributes=True)` | `to_read_v2(survey)` |
| Тег в OpenAPI | `surveys` | `surveys v2` |

Роутер второй версии лежит в `app/api/v2/surveys.py` и подключается в `main.py` через
`include_router`. Логика хранения в нём не дублируется: v2 содержит только схему ответа
и функцию преобразования:

```python
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
```

### Один объект по двум версиям

Опрос `791baf47-4ff1-47c2-8fa2-f6cd98659f0c` создан через v1 и прочитан по обоим путям.

```bash
curl -i http://127.0.0.1:8005/api/v1/surveys/791baf47-4ff1-47c2-8fa2-f6cd98659f0c
```

```http
HTTP/1.1 200 OK
content-type: application/json

{
  "id": "791baf47-4ff1-47c2-8fa2-f6cd98659f0c",
  "author_id": "00000000-0000-0000-0000-000000000001",
  "status": "draft",
  "created_at": "2026-10-06T13:25:42.043680Z",
  "updated_at": "2026-10-06T13:25:42.043684Z",
  "opens_at": "2026-10-01T09:00:00+03:00",
  "closes_at": "2026-10-15T18:00:00+03:00",
  "title": "Удовлетворённость офисом",
  "description": null,
  "anonymous": false
}
```

```bash
curl -i http://127.0.0.1:8005/api/v2/surveys/791baf47-4ff1-47c2-8fa2-f6cd98659f0c
```

```http
HTTP/1.1 200 OK
content-type: application/json

{
  "id": "791baf47-4ff1-47c2-8fa2-f6cd98659f0c",
  "author_id": "00000000-0000-0000-0000-000000000001",
  "status": "draft",
  "created_at": "2026-10-06T13:25:42.043680Z",
  "updated_at": "2026-10-06T13:25:42.043684Z",
  "schedule": {
    "opens_at": "2026-10-01T09:00:00+03:00",
    "closes_at": "2026-10-15T18:00:00+03:00"
  },
  "title": "Удовлетворённость офисом",
  "description": null,
  "anonymous": false
}
```

Идентификатор, даты создания и значения полей совпадают, то есть это один объект из
одного хранилища. Отличается только форма ответа.

### OpenAPI

В Swagger маршруты разведены по тегам: `surveys` для v1 и `surveys v2` для второй версии,
у тега v2 есть описание отличия.

