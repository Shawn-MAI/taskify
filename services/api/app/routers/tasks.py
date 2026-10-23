"""Task endpoints: create, detail, move between columns, assign.

Each mutating endpoint writes the change, its activity record and any
notifications in one transaction, then publishes events after commit.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_session
from ..events import broker
from ..models import ActivityAction, Comment, Notification, Project, Status, Task, User
from ..schemas import AssigneeChange, StatusChange, TaskCreate, TaskDetailOut, TaskOut
from ..security import get_acting_user
from ..services.activity import record_activity, recent_activity
from ..services.notifications import notify_assigned

router = APIRouter(tags=["tasks"])


def publish_notifications(notes: list[Notification]) -> None:
    """Publish ``notification_created`` for committed notifications."""
    for note in notes:
        broker.publish(
            {
                "type": "notification_created",
                "notification_id": note.id,
                "recipient_id": note.recipient_id,
                "task_id": note.task_id,
            }
        )


def _get_task(session: Session, task_id: int) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _require_user(session: Session, user_id: int | None) -> None:
    if user_id is not None and session.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="Assignee not found")


def _column(session: Session, project_id: int, status: Status, exclude: int | None = None) -> list[Task]:
    stmt = select(Task).where(Task.project_id == project_id, Task.status == status)
    if exclude is not None:
        stmt = stmt.where(Task.id != exclude)
    return list(session.scalars(stmt.order_by(Task.position, Task.id)))


@router.post("/projects/{project_id}/tasks", response_model=TaskOut, status_code=201)
def create_task(
    project_id: int,
    body: TaskCreate,
    user: User = Depends(get_acting_user),
    session: Session = Depends(get_session),
) -> Task:
    """Create a task at the end of To Do.

    Errors: 404 unknown project or assignee, 422 invalid input.
    """
    if session.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _require_user(session, body.assignee_id)
    last = session.scalar(
        select(func.max(Task.position)).where(Task.project_id == project_id, Task.status == Status.todo)
    )
    task = Task(
        project_id=project_id,
        title=body.title,
        description=body.description,
        status=Status.todo,
        position=0 if last is None else last + 1,
        assignee_id=body.assignee_id,
        created_by=user.id,
    )
    session.add(task)
    session.flush()
    record_activity(session, task.id, user.id, ActivityAction.created, None, Status.todo.value)
    notes = notify_assigned(session, task, user)
    session.commit()
    broker.publish({"type": "task_created", "project_id": project_id, "task_id": task.id, "actor_id": user.id})
    publish_notifications(notes)
    return task


@router.get("/tasks/{task_id}", response_model=TaskDetailOut)
def get_task(
    task_id: int,
    _user: User = Depends(get_acting_user),
    session: Session = Depends(get_session),
) -> TaskDetailOut:
    """Return a task with comments (oldest first) and its 20 newest activity records."""
    task = _get_task(session, task_id)
    comments = session.scalars(
        select(Comment).where(Comment.task_id == task_id).order_by(Comment.created_at, Comment.id)
    )
    return TaskDetailOut.model_validate(
        {
            **TaskOut.model_validate(task).model_dump(),
            "comments": list(comments),
            "activity": recent_activity(session, task_id),
        },
        from_attributes=True,
    )


@router.put("/tasks/{task_id}/status", response_model=TaskOut)
def move_task(
    task_id: int,
    body: StatusChange,
    user: User = Depends(get_acting_user),
    session: Session = Depends(get_session),
) -> Task:
    """Move a task to any column (last write wins).

    The task is appended to the target column unless ``position`` is given. Moving
    to the current column without a position is a no-op and records nothing.
    Errors: 404 unknown task, 422 invalid status or position.
    """
    task = _get_task(session, task_id)
    old_status = task.status
    if old_status == body.status and body.position is None:
        return task
    column = _column(session, task.project_id, body.status, exclude=task.id)
    index = len(column) if body.position is None else min(body.position, len(column))
    column.insert(index, task)
    before = task.position
    task.status = body.status
    for i, item in enumerate(column):
        item.position = i
    if old_status == body.status and before == task.position:
        session.rollback()
        return task
    if old_status != body.status:
        record_activity(session, task.id, user.id, ActivityAction.moved, old_status.value, body.status.value)
    session.commit()
    broker.publish(
        {
            "type": "task_moved",
            "project_id": task.project_id,
            "task_id": task.id,
            "actor_id": user.id,
            "status": task.status.value,
        }
    )
    return task


@router.put("/tasks/{task_id}/assignee", response_model=TaskOut)
def assign_task(
    task_id: int,
    body: AssigneeChange,
    user: User = Depends(get_acting_user),
    session: Session = Depends(get_session),
) -> Task:
    """Assign, reassign, or clear (``null``) the assignee. Unchanged assignment is a no-op.

    Errors: 404 unknown task or user, 422 invalid input.
    """
    task = _get_task(session, task_id)
    _require_user(session, body.assignee_id)
    if task.assignee_id == body.assignee_id:
        return task
    old = task.assignee_id
    task.assignee_id = body.assignee_id
    action = ActivityAction.unassigned if body.assignee_id is None else ActivityAction.assigned
    record_activity(
        session,
        task.id,
        user.id,
        action,
        None if old is None else str(old),
        None if body.assignee_id is None else str(body.assignee_id),
    )
    notes = notify_assigned(session, task, user)
    session.commit()
    broker.publish(
        {
            "type": "task_assigned",
            "project_id": task.project_id,
            "task_id": task.id,
            "actor_id": user.id,
            "assignee_id": task.assignee_id,
        }
    )
    publish_notifications(notes)
    return task
