from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions.base import DomainError
from app.schemas.errors import ErrorDetail, ErrorInfo, ErrorResponse

ERROR_CODES = {
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
}


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)


def error_body(code: str, message: str, details: list[ErrorDetail] | None = None) -> dict:
    error = ErrorResponse(error=ErrorInfo(code=code, message=message, details=details or []))
    return error.model_dump()


async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in err["loc"]),
            rule=err["type"],
            message=err["msg"],
        )
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_body("validation_error", "Запрос не прошёл проверку", details),
    )


async def http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc, DomainError):
        code = exc.code
    else:
        code = ERROR_CODES.get(exc.status_code, "http_error")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(code, str(exc.detail)),
    )
