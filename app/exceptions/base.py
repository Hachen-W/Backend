from fastapi import HTTPException


class DomainError(HTTPException):
    status_code: int = 400
    code: str = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(status_code=self.status_code, detail=message)


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class RuleViolationError(DomainError):
    status_code = 422
    code = "rule_violation"
