"""Notification rules (FR-015).

Functions add rows to the caller's session and return them; the caller commits and
then publishes ``notification_created`` events.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Comment, Notification, NotificationType, Task, User


def _snippet(title: str) -> str:
    return title if len(title) <= 60 else title[:57] + "..."


def notify_assigned(session: Session, task: Task, actor: User) -> list[Notification]:
    """Notify the new assignee, unless they are the actor or there is none."""
    if task.assignee_id is None or task.assignee_id == actor.id:
        return []
    note = Notification(
        recipient_id=task.assignee_id,
        type=NotificationType.task_assigned,
        task_id=task.id,
        actor_id=actor.id,
        message=f"{actor.name} assigned you \"{_snippet(task.title)}\"",
    )
    session.add(note)
    return [note]


def notify_commented(session: Session, task: Task, author: User) -> list[Notification]:
    """Notify the task's assignee and prior commenters, excluding the comment author."""
    recipients: set[int] = set(
        session.scalars(select(Comment.author_id).where(Comment.task_id == task.id))
    )
    if task.assignee_id is not None:
        recipients.add(task.assignee_id)
    recipients.discard(author.id)
    created = []
    for user_id in sorted(recipients):
        note = Notification(
            recipient_id=user_id,
            type=NotificationType.task_commented,
            task_id=task.id,
            actor_id=author.id,
            message=f"{author.name} commented on \"{_snippet(task.title)}\"",
        )
        session.add(note)
        created.append(note)
    return created
