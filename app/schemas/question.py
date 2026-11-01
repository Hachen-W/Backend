from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QuestionType(StrEnum):
    SINGLE_SELECTION = "single_selection"
    MULTIPLE = "multiple"
    SCALE = "scale"
    FREE_TEXT = "free_text"


class QuestionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_type: QuestionType = Field(examples=[QuestionType.SINGLE_SELECTION])
    position: int = Field(ge=0, le=100, examples=[0])
    required: bool = False
    body: str = Field(
        min_length=1,
        max_length=1000,
        examples=["Как вы оцениваете удобство офиса?"],
    )

    @field_validator("body")
    @classmethod
    def strip_value(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Поле не может состоять только из пробелов")
        return value


class QuestionCreate(QuestionBase):
    survey_id: UUID = Field(examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])


class QuestionReplace(QuestionBase):
    pass


class QuestionRead(BaseModel):
    id: UUID
    survey_id: UUID
    question_type: QuestionType
    position: int
    required: bool
    body: str


class QuestionPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_type: QuestionType = None
    position: int = Field(default=None, ge=0, le=100)
    required: bool = None
    body: str = Field(default=None, min_length=1, max_length=1000)

    @field_validator("body")
    @classmethod
    def strip_value(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Поле не может состоять только из пробелов")
        return value
