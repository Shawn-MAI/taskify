"""Pages, JSON helpers for the browser script, and the event-stream relay.

Identity: the person picks one of the predefined users; the id is stored in the signed
session and is the only source of ``X-Acting-User`` (Phase-1 Authentication Exception,
see plan.md Threat Surface). All input is re-validated by the API service; this layer
only shapes requests and shows the API's error messages. All state-changing views are
POST and CSRF-protected by Django middleware.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from functools import wraps
from typing import Any

from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from . import api_client
from .api_client import ApiError

COLUMN_LABELS = [
    ("todo", "To Do"),
    ("in_progress", "In Progress"),
    ("in_review", "In Review"),
    ("done", "Done"),
]


def health(_request: HttpRequest) -> JsonResponse:
    """Unauthenticated liveness probe."""
    return JsonResponse({"status": "ok"})


def requires_user(wants_json: bool = False) -> Callable:
    """Decorator: require a selected user in the session.

    Args:
        wants_json: Respond with a 401 JSON error instead of redirecting to the chooser.
    """

    def decorator(view: Callable) -> Callable:
        """Wrap ``view`` with the session-user check."""

        @wraps(view)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            """Run the view only when a user has been chosen."""
            if request.session.get("user_id") is None:
                if wants_json:
                    return JsonResponse({"error": "Choose a user first."}, status=401)
                return redirect("users")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def _uid(request: HttpRequest) -> int:
    return int(request.session["user_id"])


def _call(request: HttpRequest, method: str, path: str, **kw: Any) -> Any:
    return api_client.request(method, path, acting_user=_uid(request), **kw)


def _context(request: HttpRequest, **extra: Any) -> dict[str, Any]:
    """Base template context: current user and unread notification count."""
    unread = 0
    if request.session.get("user_id") is not None:
        try:
            unread = len(_call(request, "GET", "/notifications", params={"unread": "true"}))
        except ApiError:
            unread = 0
    return {
        "current_user_id": request.session.get("user_id"),
        "current_user_name": request.session.get("user_name"),
        "unread_count": unread,
        **extra,
    }


def _error_page(request: HttpRequest, err: ApiError) -> HttpResponse:
    status = 404 if err.status == 404 else 503
    return render(request, "boards/error.html", _context(request, message=err.message), status=status)


def _json_error(err: ApiError) -> JsonResponse:
    return JsonResponse({"error": err.message, "field": err.field}, status=err.status if err.status < 500 else 502)


def _body(request: HttpRequest) -> dict[str, Any] | None:
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def users(request: HttpRequest) -> HttpResponse:
    """Choose which predefined user to act as (FR-002). POST stores the choice."""
    try:
        people = api_client.request("GET", "/users")
    except ApiError as err:
        return _error_page(request, err)
    error = None
    if request.method == "POST":
        raw = request.POST.get("user_id", "")
        chosen = next((u for u in people if str(u["id"]) == raw), None)
        if chosen:
            request.session["user_id"] = chosen["id"]
            request.session["user_name"] = chosen["name"]
            return redirect("projects")
        error = "Choose one of the listed users."
    return render(request, "boards/users.html", _context(request, people=people, error=error), status=422 if error else 200)


@requires_user()
def projects(request: HttpRequest) -> HttpResponse:
    """List projects and show the new-project form."""
    try:
        items = _call(request, "GET", "/projects")
    except ApiError as err:
        return _error_page(request, err)
    return render(request, "boards/projects.html", _context(request, projects=items, form={}))


@requires_user()
@require_POST
def project_create(request: HttpRequest) -> HttpResponse:
    """Create a project; on a validation error re-show the form with the API message."""
    form = {"name": request.POST.get("name", ""), "description": request.POST.get("description", "")}
    try:
        created = _call(request, "POST", "/projects", json=form)
    except ApiError as err:
        if err.status >= 500 or err.status == 404:
            return _error_page(request, err)
        items = _call(request, "GET", "/projects")
        return render(
            request,
            "boards/projects.html",
            _context(request, projects=items, form=form, error=err.message, error_field=err.field),
            status=409 if err.status == 409 else 422,
        )
    return redirect("board", project_id=created["id"])


def _board_context(request: HttpRequest, project_id: int, **extra: Any) -> dict[str, Any]:
    board = _call(request, "GET", f"/projects/{project_id}")
    people = api_client.request("GET", "/users")
    names = {u["id"]: u["name"] for u in people}
    columns = []
    for key, label in COLUMN_LABELS:
        tasks = [{**t, "assignee_name": names.get(t["assignee_id"])} for t in board["columns"][key]]
        columns.append({"key": key, "label": label, "tasks": tasks})
    return _context(request, project=board["project"], columns=columns, column_options=COLUMN_LABELS, people=people, form={}, **extra)


@requires_user()
def board(request: HttpRequest, project_id: int) -> HttpResponse:
    """Show a project's four-column Kanban board."""
    try:
        ctx = _board_context(request, project_id)
    except ApiError as err:
        return _error_page(request, err)
    return render(request, "boards/board.html", ctx)


@requires_user(wants_json=True)
@require_GET
def board_json(request: HttpRequest, project_id: int) -> JsonResponse:
    """Board plus user names as JSON, used by the browser to refresh after live events."""
    try:
        data = _call(request, "GET", f"/projects/{project_id}")
        people = api_client.request("GET", "/users")
    except ApiError as err:
        return _json_error(err)
    return JsonResponse({**data, "users": {str(u["id"]): u["name"] for u in people}})


@requires_user()
@require_POST
def task_create(request: HttpRequest, project_id: int) -> HttpResponse:
    """Create a task from the board form; errors re-render the board with the API message."""
    assignee = request.POST.get("assignee_id", "")
    payload: dict[str, Any] = {"title": request.POST.get("title", ""), "description": request.POST.get("description", "")}
    if assignee:
        payload["assignee_id"] = int(assignee) if assignee.isdigit() else assignee
    else:
        payload["assignee_id"] = None
    try:
        _call(request, "POST", f"/projects/{project_id}/tasks", json=payload)
    except ApiError as err:
        if err.status >= 500:
            return _error_page(request, err)
        try:
            ctx = _board_context(request, project_id, error=err.message, error_field=err.field)
        except ApiError as inner:
            return _error_page(request, inner)
        ctx["form"] = {"title": payload["title"], "description": payload["description"]}
        return render(request, "boards/board.html", ctx, status=422 if err.status != 404 else 404)
    return redirect("board", project_id=project_id)


@requires_user(wants_json=True)
@require_POST
def task_move(request: HttpRequest, task_id: int) -> JsonResponse:
    """Move a task to a column (drag-and-drop or the Move-to menu)."""
    data = _body(request)
    if data is None:
        return HttpResponseBadRequest("Invalid request.")
    payload = {"status": data.get("status")}
    if data.get("position") is not None:
        payload["position"] = data["position"]
    try:
        return JsonResponse(_call(request, "PUT", f"/tasks/{task_id}/status", json=payload))
    except ApiError as err:
        return _json_error(err)


@requires_user(wants_json=True)
@require_POST
def task_assign(request: HttpRequest, task_id: int) -> JsonResponse:
    """Assign, reassign or clear (``null``) a task's assignee."""
    data = _body(request)
    if data is None:
        return HttpResponseBadRequest("Invalid request.")
    try:
        return JsonResponse(_call(request, "PUT", f"/tasks/{task_id}/assignee", json={"assignee_id": data.get("assignee_id")}))
    except ApiError as err:
        return _json_error(err)


@requires_user(wants_json=True)
@require_GET
def task_detail(request: HttpRequest, task_id: int) -> JsonResponse:
    """Task with comments and recent activity as JSON, plus user names."""
    try:
        data = _call(request, "GET", f"/tasks/{task_id}")
        people = api_client.request("GET", "/users")
    except ApiError as err:
        return _json_error(err)
    return JsonResponse({**data, "users": {str(u["id"]): u["name"] for u in people}})


@requires_user(wants_json=True)
@require_POST
def comment_add(request: HttpRequest, task_id: int) -> JsonResponse:
    """Add a comment to a task."""
    data = _body(request)
    if data is None:
        return HttpResponseBadRequest("Invalid request.")
    try:
        return JsonResponse(_call(request, "POST", f"/tasks/{task_id}/comments", json={"body": data.get("body")}), status=201)
    except ApiError as err:
        return _json_error(err)


@requires_user()
@require_GET
def notifications(request: HttpRequest) -> HttpResponse:
    """List the current user's notifications, newest first."""
    try:
        items = _call(request, "GET", "/notifications")
        people = api_client.request("GET", "/users")
    except ApiError as err:
        return _error_page(request, err)
    return render(request, "boards/notifications.html", _context(request, notifications=items, people=people))


@requires_user(wants_json=True)
@require_GET
def notifications_json(request: HttpRequest) -> JsonResponse:
    """Notifications as JSON; ``?unread=true`` filters unread ones."""
    params = {"unread": "true"} if request.GET.get("unread") == "true" else None
    try:
        return JsonResponse(_call(request, "GET", "/notifications", params=params), safe=False)
    except ApiError as err:
        return _json_error(err)


@requires_user()
@require_POST
def notification_read(request: HttpRequest, notification_id: int) -> HttpResponse:
    """Mark a notification read; JSON for the script, redirect for plain form posts."""
    wants_json = request.headers.get("X-Requested-With") == "fetch"
    try:
        note = _call(request, "POST", f"/notifications/{notification_id}/read")
    except ApiError as err:
        if wants_json:
            return _json_error(err)
        return _error_page(request, err)
    return JsonResponse(note) if wants_json else redirect("notifications")


def _blocks(lines: Iterator[str]) -> Iterator[str]:
    """Group SSE lines into blocks separated by blank lines."""
    block: list[str] = []
    for line in lines:
        if line == "":
            if block:
                yield "\n".join(block)
            block = []
        else:
            block.append(line)


def relay_blocks(lines: Iterator[str], user_id: int) -> Iterator[str]:
    """Relay API events to one browser, dropping notifications meant for other users."""
    yield "retry: 2000\n\n"
    for block in _blocks(lines):
        for line in block.split("\n"):
            if line.startswith("data: "):
                try:
                    event = json.loads(line[6:])
                except ValueError:
                    break
                if event.get("type") == "notification_created" and event.get("recipient_id") != user_id:
                    block = ""
                break
        if block:
            yield block + "\n\n"


@requires_user(wants_json=True)
@require_GET
def events(request: HttpRequest) -> HttpResponse:
    """Server-Sent Events relay from the API's event stream to the browser."""
    response = StreamingHttpResponse(
        relay_blocks(api_client.stream_events(), _uid(request)), content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
