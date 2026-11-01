from uuid import UUID

from app.exceptions.questions import QuestionLimitReached, QuestionNotFound
from app.exceptions.surveys import SurveyNotFound
from app.models.question import Question
from app.repositories.questions import QuestionRepository
from app.repositories.surveys import SurveyRepository
from app.schemas.question import QuestionCreate, QuestionPatch, QuestionReplace
from app.use_cases.common import apply_changes


class QuestionService:
    def __init__(
        self, questions: QuestionRepository, surveys: SurveyRepository, max_questions: int
    ) -> None:
        self._questions = questions
        self._surveys = surveys
        self._max_questions = max_questions

    async def get(self, question_id: UUID) -> Question:
        question = await self._questions.get(question_id)
        if question is None:
            raise QuestionNotFound(question_id)
        return question

    async def list(self) -> list[Question]:
        return await self._questions.find()

    async def create(self, payload: QuestionCreate) -> Question:
        await self._check_can_add(payload.survey_id)
        question = Question(**payload.model_dump())
        await self._questions.add(question)
        return question

    async def replace(self, question_id: UUID, payload: QuestionReplace) -> Question:
        current = await self.get(question_id)
        apply_changes(current, payload.model_dump())
        await self._questions.update(current)
        return current

    async def update(self, question_id: UUID, payload: QuestionPatch) -> Question:
        current = await self.get(question_id)
        apply_changes(current, payload.model_dump(exclude_unset=True))
        await self._questions.update(current)
        return current

    async def delete(self, question_id: UUID) -> None:
        await self.get(question_id)
        await self._questions.delete(question_id)

    async def _check_can_add(self, survey_id: UUID) -> None:
        if await self._surveys.get(survey_id) is None:
            raise SurveyNotFound(survey_id)
        if await self._questions.count_by_survey(survey_id) >= self._max_questions:
            raise QuestionLimitReached(survey_id, self._max_questions)
