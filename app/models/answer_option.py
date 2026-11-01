from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.question import Question


class AnswerOption(Base):
    __tablename__ = "answer_options"

    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4)
    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    text: Mapped[str] = mapped_column(String(200))

    question: Mapped[Question] = relationship(back_populates="options", init=False, repr=False)
