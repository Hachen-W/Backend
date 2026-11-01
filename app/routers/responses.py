from typing import Any

from app.errors import ERROR_CODES
from app.schemas.errors import ErrorResponse

BODY_DETAILS = [
    {
        "field": "body.title",
        "rule": "string_too_long",
        "message": "String should have at most 100 characters",
    }
]
PATH_DETAILS = [
    {
        "field": "path.survey_id",
        "rule": "uuid_parsing",
        "message": "Input should be a valid UUID",
    }
]


def error_response(
    status_code: int, description: str, details: list[dict[str, str]] | None = None
) -> dict[int | str, dict[str, Any]]:
    if status_code == 422:
        error = {
            "code": "validation_error",
            "message": "Запрос не прошёл проверку",
            "details": details or [],
        }
    else:
        error = {"code": ERROR_CODES[status_code], "message": description, "details": []}
    return {
        status_code: {
            "model": ErrorResponse,
            "description": description,
            "content": {"application/json": {"example": {"error": error}}},
        }
    }


BAD_BODY = error_response(422, "Тело запроса не прошло проверку", BODY_DETAILS)
BAD_ID = error_response(422, "Идентификатор в пути не является UUID", PATH_DETAILS)
BAD_ID_OR_BODY = error_response(
    422, "Идентификатор в пути не является UUID или тело не прошло проверку", PATH_DETAILS
)
