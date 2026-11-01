from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: str = Field(description="Путь к полю через точку: источник и имя поля")
    rule: str = Field(description="Машиночитаемое имя нарушенного правила")
    message: str = Field(description="Человекочитаемое описание нарушения")


class ErrorInfo(BaseModel):
    code: str = Field(description="Машиночитаемый код ошибки")
    message: str = Field(description="Человекочитаемое сообщение")
    details: list[ErrorDetail] = Field(
        default_factory=list,
        description="Позиции для ошибок валидации; для остальных ошибок пустой список",
    )


class ErrorResponse(BaseModel):
    error: ErrorInfo
