"""SQLAlchemy models for the Taskify API (see specs/001-taskify-kanban-platform/data-model.md).

All timestamps are stored and returned in UTC.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    TypeDecorator,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """DateTime that always round-trips as timezone-aware UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):  # noqa: ANN001
        """Normalise to naive UTC for storage."""
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):  # noqa: ANN001
        """Attach UTC to values read from the database."""
        return value.replace(tzinfo=timezone.utc) if value is not None else None


class Role(str, enum.Enum):
    """Predefined user roles."""

    product_manager = "product_manager"
    engineer = "engineer"


class Status(str, enum.Enum):
    """Kanban columns in display order."""

    todo = "todo"
    in_progress = "in_progress"
    in_review = "in_review"
    done = "done"


class ActivityAction(str, enum.Enum):
    """Kinds of task activity (FR-012)."""

    created = "created"
    moved = "moved"
    assigned = "assigned"
    unassigned = "unassigned"
    commented = "commented"


class NotificationType(str, enum.Enum):
    """Kinds of in-app notification (FR-015)."""

    task_assigned = "task_assigned"
    task_commented = "task_commented"


def _enum(cls: type[enum.Enum]) -> Enum:
    return Enum(cls, native_enum=False, length=20, validate_strings=True)


class Base(DeclarativeBase):
    """Declarative base for all models."""


class User(Base):
    """A predefined team member. Read-only through the API."""

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    role: Mapped[Role] = mapped_column(_enum(Role))


class Project(Base):
    """A named container of tasks; names are unique ignoring case."""

    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


Index("ux_project_name_lower", func.lower(Project.name), unique=True)


class Task(Base):
    """A unit of work on a project board."""

    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[Status] = mapped_column(_enum(Status), default=Status.todo)
    position: Mapped[int] = mapped_column(default=0)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class Comment(Base):
    """A plain-text comment on a task."""

    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Activity(Base):
    """Append-only record of a change to a task."""

    __tablename__ = "activity"
    __table_args__ = (Index("ix_activity_task_created", "task_id", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[ActivityAction] = mapped_column(_enum(ActivityAction))
    from_value: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_value: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Notification(Base):
    """An in-app notification for one user."""

    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[NotificationType] = mapped_column(_enum(NotificationType))
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    message: Mapped[str] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
