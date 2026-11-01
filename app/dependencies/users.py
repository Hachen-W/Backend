from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, StorageBackend, get_settings
from app.core.database import get_session
from app.repositories.users import InMemoryUserRepository, SqlAlchemyUserRepository, UserRepository
from app.use_cases.users import UserService


@lru_cache
def get_memory_user_repository() -> UserRepository:
    return InMemoryUserRepository()


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserRepository:
    if settings.storage == StorageBackend.MEMORY:
        return get_memory_user_repository()
    return SqlAlchemyUserRepository(session)


def get_user_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    return UserService(users)
