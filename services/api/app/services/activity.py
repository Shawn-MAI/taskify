"""Activity recording (FR-012).

Records are written inside the caller's transaction, so a failed change leaves no
record. Callers must not call :func:`record_activity` for no-op changes.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Activity, ActivityAction

RECENT_LIMIT = 20


def record_activity(
    session: Session,
    task_id: int,
    actor_id: int,
    action: ActivityAction,
    from_value: str | None = None,
    to_value: str | None = None,
) -> Activity:
    """Add an activity row to ``session`` (the caller commits).

    Args:
        session: Open session whose transaction also holds the described change.
        task_id: Task the action applies to.
        actor_id: User who performed the action.
        action: Kind of action.
        from_value: Previous status or assignee id, when applicable.
        to_value: New status or assignee id, when applicable.

    Returns:
        The pending ``Activity`` row.
    """
    row = Activity(
        task_id=task_id,
        actor_id=actor_id,
        action=action,
        from_value=from_value,
        to_value=to_value,
    )
    session.add(row)
    return row


def recent_activity(session: Session, task_id: int) -> list[Activity]:
    """Return the 20 newest activity records for a task, newest first."""
    stmt = (
        select(Activity)
        .where(Activity.task_id == task_id)
        .order_by(Activity.created_at.desc(), Activity.id.desc())
        .limit(RECENT_LIMIT)
    )
    return list(session.scalars(stmt))
