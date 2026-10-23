"""Service-token and acting-user dependencies.

Phase-1 Authentication Exception (constitution v1.1.0): there is no end-user login.
Every endpoint except ``/health`` is nevertheless deny-by-default: it requires the
shared service token (``TASKIFY_API_TOKEN``). The ``X-Acting-User`` header is an
unauthenticated *claim* about who is acting; anyone holding the token can claim any
of the five users. This risk is documented in plan.md (Threat Surface) and is
removed by the follow-up feature ``002-user-authentication``.
"""

from __future__ import annotations

import hmac
import os

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .db import get_session
from .models import User


def require_token(authorization: str | None = Header(default=None)) -> None:
    """Reject the request unless it carries the correct bearer service token.

    Raises:
        HTTPException: 401 when the token is missing, wrong, or not configured.
    """
    expected = os.environ.get("TASKIFY_API_TOKEN", "")
    scheme, _, supplied = (authorization or "").partition(" ")
    if (
        not expected
        or scheme.lower() != "bearer"
        or not hmac.compare_digest(supplied.encode(), expected.encode())
    ):
        raise HTTPException(status_code=401, detail="Authentication required")


def get_acting_user(
    x_acting_user: str | None = Header(default=None),
    _token: None = Depends(require_token),
    session: Session = Depends(get_session),
) -> User:
    """Resolve the ``X-Acting-User`` claim to a predefined user.

    Raises:
        HTTPException: 401 without a valid token (via ``require_token``), 422 when the
            header is missing or not a whole number, 404 when the user does not exist.
    """
    if x_acting_user is None or not x_acting_user.isdigit():
        raise HTTPException(status_code=422, detail="X-Acting-User must be a user id")
    user = session.get(User, int(x_acting_user))
    if user is None:
        raise HTTPException(status_code=404, detail="Acting user not found")
    return user
