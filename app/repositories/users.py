from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository(Protocol):
    async def get(self, user_id: UUID) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def find(self) -> list[User]: ...
    async def add(self, user: User) -> None: ...
    async def update(self, user: User) -> None: ...
    async def delete(self, user_id: UUID) -> None: ...


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, User] = {}

    async def get(self, user_id: UUID) -> User | None:
        return self._items.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((user for user in self._items.values() if user.email == email), None)

    async def find(self) -> list[User]:
        return list(self._items.values())

    async def add(self, user: User) -> None:
        self._items[user.id] = user

    async def update(self, user: User) -> None:
        self._items[user.id] = user

    async def delete(self, user_id: UUID) -> None:
        self._items.pop(user_id, None)


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def find(self) -> list[User]:
        return list((await self._session.scalars(select(User))).all())

    async def add(self, user: User) -> None:
        self._session.add(user)
        await self._session.flush()

    async def update(self, user: User) -> None:
        await self._session.flush()

    async def delete(self, user_id: UUID) -> None:
        user = await self._session.get(User, user_id)
        if user is not None:
            await self._session.delete(user)
            await self._session.flush()

    async def get_by_email(self, email: str) -> User | None:
        query = select(User).where(User.email == email)
        return await self._session.scalar(query)
