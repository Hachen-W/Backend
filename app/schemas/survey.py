from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


class SurveyStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class SurveyBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=100, examples=["Кто лучше?"])
    description: str | None = Field(
        default=None,
        min_length=1,
        max_length=1000,
        examples=["Требуется проголосовать за одного человека"],
    )
    anonymous: bool = False
    opens_at: AwareDatetime
    closes_at: AwareDatetime

    @field_validator("title")
    @classmethod
    def strip_title(cls, title: str) -> str:
        title = title.strip()
        if not title:
            raise ValueError("Поле не может состоять только из пробелов")
        return title

    @model_validator(mode="after")
    def check_dates(self) -> Self:
        if self.opens_at >= self.closes_at:
            raise ValueError("Опрос должен закрываться после открытия")
        return self


class SurveyCreate(SurveyBase):
    pass


class SurveyReplace(SurveyBase):
    pass


class SurveyRead(BaseModel):
    id: UUID
    author_id: UUID
    status: SurveyStatus
    created_at: AwareDatetime
    updated_at: AwareDatetime
    opens_at: AwareDatetime
    closes_at: AwareDatetime
    title: str
    description: str | None
    anonymous: bool


class SurveyPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, min_length=1, max_length=1000)
    anonymous: bool = None
    opens_at: AwareDatetime = None
    closes_at: AwareDatetime = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, title: str) -> str:
        title = title.strip()
        if not title:
            raise ValueError("Поле не может состоять только из пробелов")
        return title


class SurveySchedule(BaseModel):
    opens_at: AwareDatetime
    closes_at: AwareDatetime


class SurveyReadV2(BaseModel):
    id: UUID
    author_id: UUID
    status: SurveyStatus
    created_at: AwareDatetime
    updated_at: AwareDatetime
    schedule: SurveySchedule
    title: str
    description: str | None
    anonymous: bool
