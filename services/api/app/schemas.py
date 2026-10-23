"""Pydantic request and response schemas (see contracts/api-v1.openapi.yaml).

Every request schema is an allow-list: unknown fields are rejected and each text
field carries explicit length limits. Violations raise messages that name the
field and the rule (FR-010), without technical details.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictInt

from .models import ActivityAction, NotificationType, Role, Status


def _text(label: str, lo: int, hi: int, optional: bool = False) -> BeforeValidator:
    """Build a validator for a plain-text field.

    Args:
        label: Human-readable field name used in the error message.
        lo: Minimum length after trimming (0 for optional fields).
        hi: Maximum length after trimming.
        optional: Whether ``None`` or an empty string is accepted (stored as ``None``).

    Returns:
        A ``BeforeValidator`` that trims the text and enforces the limits.
    """

    def check(value: Any) -> Any:
        if value is None and optional:
            return None
        if not isinstance(value, str):
            raise ValueError(f"{label} must be text")
        text = value.strip()
        if optional and text == "":
            return None
        if not lo <= len(text) <= hi:
            if lo > 0:
                raise ValueError(f"{label} must be {lo}-{hi} characters")
            raise ValueError(f"{label} must be at most {hi} characters")
        return text

    return BeforeValidator(check)


ProjectName = Annotated[str, _text("Name", 1, 100)]
ProjectDescription = Annotated[str | None, _text("Description", 0, 1000, optional=True)]
TaskTitle = Annotated[str, _text("Title", 1, 150)]
TaskDescription = Annotated[str | None, _text("Description", 0, 2000, optional=True)]
CommentBody = Annotated[str, _text("Comment", 1, 2000)]


class _Request(BaseModel):
    """Base for request bodies: unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


class ProjectCreate(_Request):
    """Body of ``POST /projects``."""

    name: ProjectName
    description: ProjectDescription = None


class TaskCreate(_Request):
    """Body of ``POST /projects/{id}/tasks``."""

    title: TaskTitle
    description: TaskDescription = None
    assignee_id: StrictInt | None = None


class StatusChange(_Request):
    """Body of ``PUT /tasks/{id}/status``."""

    status: Status
    position: Annotated[StrictInt, Field(ge=0)] | None = None


class AssigneeChange(_Request):
    """Body of ``PUT /tasks/{id}/assignee``; ``null`` clears the assignee."""

    assignee_id: StrictInt | None


class CommentCreate(_Request):
    """Body of ``POST /tasks/{id}/comments``."""

    body: CommentBody


class _Out(BaseModel):
    """Base for response models built from ORM rows."""

    model_config = ConfigDict(from_attributes=True)


class UserOut(_Out):
    """A predefined user."""

    id: int
    name: str
    role: Role


class ProjectOut(_Out):
    """A project."""

    id: int
    name: str
    description: str | None
    created_by: int
    created_at: datetime


class TaskOut(_Out):
    """A task card."""

    id: int
    project_id: int
    title: str
    description: str | None
    status: Status
    position: int
    assignee_id: int | None
    created_by: int
    created_at: datetime
    updated_at: datetime


class CommentOut(_Out):
    """A comment on a task."""

    id: int
    task_id: int
    author_id: int
    body: str
    created_at: datetime


class ActivityOut(_Out):
    """One activity record."""

    id: int
    task_id: int
    actor_id: int
    action: ActivityAction
    from_value: str | None
    to_value: str | None
    created_at: datetime


class TaskDetailOut(TaskOut):
    """A task with its comments (oldest first) and 20 newest activity records."""

    comments: list[CommentOut]
    activity: list[ActivityOut]


class Columns(BaseModel):
    """Tasks grouped by status, ordered by position."""

    todo: list[TaskOut]
    in_progress: list[TaskOut]
    in_review: list[TaskOut]
    done: list[TaskOut]


class BoardOut(BaseModel):
    """A project with its four columns."""

    project: ProjectOut
    columns: Columns


class NotificationOut(_Out):
    """An in-app notification."""

    id: int
    type: NotificationType
    task_id: int
    actor_id: int
    message: str
    read: bool
    created_at: datetime
