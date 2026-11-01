from uuid import UUID

from app.exceptions.base import ConflictError, NotFoundError


class UserNotFound(NotFoundError):
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        super().__init__(f"Пользователь {user_id} не найден")


class EmailAlreadyTaken(ConflictError):
    code = "email_taken"

    def __init__(self, email: str, owner_id: UUID) -> None:
        self.email = email
        self.owner_id = owner_id
        super().__init__(f"Почта {email} уже занята другим пользователем")
