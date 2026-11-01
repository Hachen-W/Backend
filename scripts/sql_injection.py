import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine, session_factory
from app.models.survey import Survey

MARK = f"inj-{uuid4().hex[:6]}"
TITLES = [f"{MARK} Удовлетворённость офисом", f"{MARK} Столовая", f"{MARK} Парковка"]

NORMAL = TITLES[1]
INJECTION = "' OR '1'='1"


async def find_by_string_concat(session: AsyncSession, title: str) -> list[str]:
    result = await session.execute(text(f"SELECT title FROM surveys WHERE title = '{title}'"))  # noqa: S608
    return list(result.scalars())


async def find_by_text_param(session: AsyncSession, title: str) -> list[str]:
    result = await session.execute(
        text("SELECT title FROM surveys WHERE title = :title"), {"title": title}
    )
    return list(result.scalars())


async def find_by_expression(session: AsyncSession, title: str) -> list[str]:
    query = select(Survey.title).where(Survey.title == title)
    result = await session.execute(query)
    return list(result.scalars())


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def find_by_substring(session: AsyncSession, part: str, *, escape: bool) -> list[str]:
    if escape:
        condition = Survey.title.ilike(f"%{escape_like(part)}%", escape="\\")
    else:
        condition = Survey.title.ilike(f"%{part}%")
    result = await session.execute(select(Survey.title).where(condition))
    return list(result.scalars())


METHODS = [
    ("1. склейка строки", find_by_string_concat),
    ("2. text() с параметром", find_by_text_param),
    ("3. выражения SQLAlchemy", find_by_expression),
]


async def seed(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    for title in TITLES:
        session.add(
            Survey(
                author_id=uuid4(),
                title=title,
                opens_at=now,
                closes_at=now + timedelta(days=7),
            )
        )
    await session.commit()


async def cleanup(session: AsyncSession) -> None:
    await session.execute(delete(Survey).where(Survey.title.startswith(MARK)))
    await session.commit()


async def main() -> None:
    engine.echo = True
    async with session_factory() as session:
        await seed(session)
        try:
            for value in (NORMAL, INJECTION):
                print(f"\n========== значение: {value!r} ==========")
                for name, method in METHODS:
                    print(f"\n--- {name}")
                    found = await method(session, value)
                    print(f">>> найдено {len(found)}: {found}")

            print("\n========== поиск по подстроке через ILIKE ==========")
            for part in ("Стол", "%", "_"):
                for escape in (False, True):
                    mode = "с экранированием" if escape else "без экранирования"
                    print(f"\n--- {part!r}, {mode}")
                    found = await find_by_substring(session, part, escape=escape)
                    print(f">>> найдено {len(found)}: {found}")
        finally:
            await cleanup(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
