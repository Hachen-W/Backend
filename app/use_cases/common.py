from typing import Any


def apply_changes(target: object, changes: dict[str, Any]) -> None:
    for field, value in changes.items():
        setattr(target, field, value)
