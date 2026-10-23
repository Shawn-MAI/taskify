"""``POST /tasks/{id}/comments``: any user can comment on any task (FR-009)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_session
from ..events import broker
from ..models import ActivityAction, Comment, Task, User
from ..schemas import CommentCreate, CommentOut
from ..security import get_acting_user
from ..services.activity import record_activity
from ..services.notifications import notify_commented
from .tasks import publish_notifications

router = APIRouter(tags=["comments"])


@router.post("/tasks/{task_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    task_id: int,
    body: CommentCreate,
    user: User = Depends(get_acting_user),
    session: Session = Depends(get_session),
) -> Comment:
    """Add a plain-text comment (1-2000 characters) authored by the acting user.

    Notifies the assignee and prior commenters (never the author). Errors: 404
    unknown task, 422 empty or over-length body.
    """
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    notes = notify_commented(session, task, user)
    comment = Comment(task_id=task_id, author_id=user.id, body=body.body)
    session.add(comment)
    session.flush()
    record_activity(session, task_id, user.id, ActivityAction.commented, None, None)
    session.commit()
    broker.publish(
        {
            "type": "comment_added",
            "project_id": task.project_id,
            "task_id": task_id,
            "comment_id": comment.id,
            "actor_id": user.id,
        }
    )
    publish_notifications(notes)
    return comment
