from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import TZ_DATETIME, Base, enum_column, utc_now
from app.schemas.survey import SurveyStatus

if TYPE_CHECKING:
    from app.models.question import Question


class SurveySortField(StrEnum):
    CREATED_AT = "created_at"
    OPENS_AT = "opens_at"
    CLOSES_AT = "closes_at"
    TITLE = "title"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class Survey(Base):
    __tablename__ = "surveys"

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)
    author_id: Mapped[UUID]
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    anonymous: Mapped[bool] = mapped_column(default=False)
    opens_at: Mapped[datetime] = mapped_column(TZ_DATETIME)
    closes_at: Mapped[datetime] = mapped_column(TZ_DATETIME)
    status: Mapped[SurveyStatus] = mapped_column(
        enum_column(SurveyStatus), default=SurveyStatus.DRAFT
    )
    created_at: Mapped[datetime] = mapped_column(TZ_DATETIME, default_factory=utc_now)
    updated_at: Mapped[datetime] = mapped_column(TZ_DATETIME, default_factory=utc_now)

    questions: Mapped[list[Question]] = relationship(
        back_populates="survey",
        passive_deletes="all",
        default_factory=list,
        init=False,
        repr=False,
    )
