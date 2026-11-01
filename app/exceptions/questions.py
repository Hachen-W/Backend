from uuid import UUID

from app.exceptions.base import ConflictError, NotFoundError


class QuestionNotFound(NotFoundError):
    def __init__(self, question_id: UUID) -> None:
        self.question_id = question_id
        super().__init__(f"Вопрос {question_id} не найден")


class QuestionLimitReached(ConflictError):
    code = "question_limit_reached"

    def __init__(self, survey_id: UUID, limit: int) -> None:
        self.survey_id = survey_id
        self.limit = limit
        super().__init__(f"В опросе {survey_id} уже {limit} вопросов, больше добавить нельзя")
