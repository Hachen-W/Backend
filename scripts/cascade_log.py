import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select

from app.core.database import engine, session_factory
from app.models.answer_option import AnswerOption
from app.models.question import Question
from app.models.survey import Survey
from app.schemas.question import QuestionType


async def main() -> None:
    now = datetime.now(UTC)
    async with session_factory() as session:
        survey = Survey(
            author_id=uuid4(), title="Каскад", opens_at=now, closes_at=now + timedelta(days=1)
        )
        session.add(survey)
        await session.flush()
        question = Question(
            survey_id=survey.id, question_type=QuestionType.SINGLE_SELECTION, position=0, body="?"
        )
        session.add(question)
        await session.flush()
        for i in range(3):
            session.add(AnswerOption(question_id=question.id, position=i, text=f"Вариант {i + 1}"))
        await session.commit()
        question_id, survey_id = question.id, survey.id

    async with session_factory() as session:
        print("\n========== удаление вопроса с тремя вариантами ==========")
        engine.echo = True
        question = await session.get(Question, question_id)
        await session.delete(question)
        await session.commit()
        engine.echo = False
        print("========== конец ==========\n")

        left = await session.scalar(
            select(func.count())
            .select_from(AnswerOption)
            .where(AnswerOption.question_id == question_id)
        )
        print(f"вариантов ответа осталось: {left}")
        await session.delete(await session.get(Survey, survey_id))
        await session.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
