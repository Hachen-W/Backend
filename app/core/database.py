from collections.abc import AsyncIterator
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

from app.core.config import get_settings


class Base(MappedAsDataclass, DeclarativeBase, kw_only=True):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


def enum_column(enum_cls: type[StrEnum]) -> Enum:
    return Enum(
        enum_cls,
        native_enum=False,
        length=32,
        values_callable=lambda members: [member.value for member in members],
    )


TZ_DATETIME = DateTime(timezone=True)

_settings = get_settings()

engine = create_async_engine(_settings.database_url, echo=_settings.sql_echo)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
