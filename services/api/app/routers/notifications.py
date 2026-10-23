"""Notification endpoints for the acting user (FR-015, FR-016)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Notification, User
from ..schemas import NotificationOut
from ..security import get_acting_user

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    unread: bool | None = None,
    user: User = Depends(get_acting_user),
    session: Session = Depends(get_session),
) -> list[Notification]:
    """List the acting user's notifications, newest first; ``unread=true`` filters."""
    stmt = select(Notification).where(Notification.recipient_id == user.id)
    if unread:
        stmt = stmt.where(Notification.read.is_(False))
    return list(session.scalars(stmt.order_by(Notification.created_at.desc(), Notification.id.desc())))


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: int,
    user: User = Depends(get_acting_user),
    session: Session = Depends(get_session),
) -> Notification:
    """Mark a notification read. Only the recipient may; others get 404."""
    note = session.get(Notification, notification_id)
    if note is None or note.recipient_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    note.read = True
    session.commit()
    return note
