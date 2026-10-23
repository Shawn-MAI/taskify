"""``GET /users``: the five predefined users.

Requires the service token only (no ``X-Acting-User``), because a person picks who
they act as from this list.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import User
from ..schemas import UserOut
from ..security import require_token

router = APIRouter(tags=["users"], dependencies=[Depends(require_token)])


@router.get("/users", response_model=list[UserOut])
def list_users(session: Session = Depends(get_session)) -> list[User]:
    """Return all predefined users ordered by id.

    Errors: 401 without a valid service token.
    """
    return list(session.scalars(select(User).order_by(User.id)))
