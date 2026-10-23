"""Taskify API application factory.

Run with ``uvicorn app.main:create_app --factory``. Error responses use a single
format, ``{"error": {"code", "message", "field"?}}``, and never contain stack traces
or internal details (constitution Technology & Security constraints).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import db
from .models import Base
from .routers import comments, events, notifications, projects, tasks, users
from .seed import seed

log = logging.getLogger("taskify.api")

_CODES = {400: "bad_request", 401: "unauthorized", 404: "not_found", 409: "conflict", 422: "validation_error"}


def _error(status: int, message: str, field: str | None = None) -> JSONResponse:
    body: dict[str, Any] = {"code": _CODES.get(status, "error"), "message": message}
    if field:
        body["field"] = field
    return JSONResponse({"error": body}, status_code=status)


def describe_validation_error(err: dict[str, Any]) -> tuple[str, str | None]:
    """Turn one Pydantic error into a user-facing message naming the field and rule.

    Args:
        err: An entry from ``RequestValidationError.errors()``.

    Returns:
        ``(message, field)``; ``field`` is ``None`` for whole-body problems.
    """
    loc = [p for p in err.get("loc", ()) if p != "body"]
    field = str(loc[-1]) if loc else None
    label = field.replace("_", " ").capitalize() if field else "Request"
    kind = err.get("type", "")
    if kind == "value_error":
        return str(err.get("msg", "")).removeprefix("Value error, "), field
    if kind == "missing":
        return f"{label} is required", field
    if kind == "extra_forbidden":
        return f"{label} is not allowed", field
    if kind == "enum":
        expected = (err.get("ctx") or {}).get("expected", "a valid value")
        return f"{label} must be one of {expected}", field
    if kind in ("int_parsing", "int_type"):
        return f"{label} must be a whole number", field
    if kind == "greater_than_equal":
        return f"{label} must be 0 or more", field
    return f"{label} is invalid", field


def create_app(db_path: str | None = None) -> FastAPI:
    """Build the FastAPI app, initialise SQLite and seed sample data.

    Args:
        db_path: SQLite file path; defaults to ``TASKIFY_DB_PATH`` or ``taskify.db``.

    Returns:
        The configured application.
    """
    engine = db.init_engine(db_path)
    Base.metadata.create_all(engine)
    with db.new_session() as session:
        seed(session)

    app = FastAPI(title="Taskify API", version="1.0.0")

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        message, field = describe_validation_error(exc.errors()[0])
        return _error(422, message, field)

    @app.exception_handler(HTTPException)
    async def _http(_: Request, exc: HTTPException) -> JSONResponse:
        return _error(exc.status_code, str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.error(json.dumps({"event": "unhandled_error", "path": request.url.path, "type": type(exc).__name__}))
        return _error(500, "Something went wrong. Please try again.")

    @app.middleware("http")
    async def _access_log(request: Request, call_next):  # noqa: ANN001
        start = time.perf_counter()
        response = await call_next(request)
        log.info(
            json.dumps(
                {
                    "event": "request",
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": round((time.perf_counter() - start) * 1000),
                }
            )
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        """Unauthenticated liveness probe."""
        return {"status": "ok"}

    for module in (users, projects, tasks, comments, notifications, events):
        app.include_router(module.router, prefix="/api/v1")
    return app
