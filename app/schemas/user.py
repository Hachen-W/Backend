from enum import StrEnum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRole(StrEnum):
    RESPONDENT = "respondent"
    ADMIN = "admin"


class UserBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=100, examples=["user@gmail.com"])
    password: str = Field(min_length=8, max_length=100, examples=["123456789"])
    display_name: str = Field(min_length=1, max_length=100, examples=["user"])

    @field_validator("display_name")
    @classmethod
    def strip_value(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Поле не может состоять только из пробелов")
        return value


class UserCreate(UserBase):
    pass


class UserReplace(UserBase):
    pass


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str
    role: UserRole
    created_at: AwareDatetime
