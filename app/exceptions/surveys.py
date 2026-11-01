from datetime import datetime, timedelta
from uuid import UUID

from app.exceptions.base import ConflictError, NotFoundError, RuleViolationError


class SurveyNotFound(NotFoundError):
    def __init__(self, survey_id: UUID) -> None:
        self.survey_id = survey_id
        super().__init__(f"Опрос {survey_id} не найден")


class SurveyClosesBeforeOpens(RuleViolationError):
    code = "survey_closes_before_opens"

    def __init__(self, opens_at: datetime, closes_at: datetime) -> None:
        self.opens_at = opens_at
        self.closes_at = closes_at
        super().__init__("Опрос должен закрываться после открытия")


class SurveyTooLong(RuleViolationError):
    code = "survey_too_long"

    def __init__(self, duration: timedelta, max_duration: timedelta) -> None:
        self.duration = duration
        self.max_duration = max_duration
        super().__init__(
            f"Опрос длится {duration.days} дн., а допускается не больше {max_duration.days} дн."
        )


class SurveyHasQuestions(ConflictError):
    code = "survey_has_questions"

    def __init__(self, survey_id: UUID) -> None:
        self.survey_id = survey_id
        super().__init__(f"В опросе {survey_id} есть вопросы, сначала удалите их")
