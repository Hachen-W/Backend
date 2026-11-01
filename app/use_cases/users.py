import hashlib
from uuid import UUID

from app.exceptions.users import EmailAlreadyTaken, UserNotFound
from app.models.user import User
from app.repositories.users import UserRepository
from app.schemas.user import UserCreate, UserReplace
from app.use_cases.common import apply_changes


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class UserService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def get(self, user_id: UUID) -> User:
        user = await self._users.get(user_id)
        if user is None:
            raise UserNotFound(user_id)
        return user

    async def list(self) -> list[User]:
        return await self._users.find()

    async def create(self, payload: UserCreate) -> User:
        await self._check_email_free(payload.email)
        user = User(
            **payload.model_dump(exclude={"password"}),
            password_hash=hash_password(payload.password),
        )
        await self._users.add(user)
        return user

    async def replace(self, user_id: UUID, payload: UserReplace) -> User:
        current = await self.get(user_id)
        await self._check_email_free(payload.email, except_id=user_id)
        apply_changes(
            current,
            {
                **payload.model_dump(exclude={"password"}),
                "password_hash": hash_password(payload.password),
            },
        )
        await self._users.update(current)
        return current

    async def delete(self, user_id: UUID) -> None:
        await self.get(user_id)
        await self._users.delete(user_id)

    async def _check_email_free(self, email: str, except_id: UUID | None = None) -> None:
        owner = await self._users.get_by_email(email)
        if owner is not None and owner.id != except_id:
            raise EmailAlreadyTaken(email, owner.id)
