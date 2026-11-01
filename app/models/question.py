from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, enum_column
from app.schemas.question import QuestionType

if TYPE_CHECKING:
    from app.models.answer_option import AnswerOption
    from app.models.survey import Survey


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)
    survey_id: Mapped[UUID] = mapped_column(
        ForeignKey("surveys.id", ondelete="RESTRICT"), index=True
    )
    question_type: Mapped[QuestionType] = mapped_column(enum_column(QuestionType))
    position: Mapped[int]
    required: Mapped[bool] = mapped_column(default=False)
    body: Mapped[str] = mapped_column(Text)

    survey: Mapped[Survey] = relationship(back_populates="questions", init=False, repr=False)
    options: Mapped[list[AnswerOption]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        default_factory=list,
        init=False,
        repr=False,
        passive_deletes=True,
    )
