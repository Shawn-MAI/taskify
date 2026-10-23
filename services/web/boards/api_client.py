"""HTTP client for the Taskify API service.

The service token comes from ``TASKIFY_API_TOKEN``. The acting user is taken only from
the Django session by the views and passed in here; headers sent by a browser are
never forwarded. API failures are mapped to :class:`ApiError` carrying a safe,
user-facing message (never the raw upstream body or the token).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import httpx

API_PREFIX = "/api/v1"
_http: httpx.Client | None = None


class ApiError(Exception):
    """An API call failed; ``message`` is safe to show to the user."""

    def __init__(self, status: int, message: str, field: str | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.field = field


def set_http_client(client: httpx.Client | None) -> None:
    """Replace the shared HTTP client (used by tests); ``None`` resets to default."""
    global _http
    _http = client


def _client() -> httpx.Client:
    global _http
    if _http is None:
        _http = httpx.Client(base_url=os.environ.get("TASKIFY_API_URL", "http://localhost:8001"), timeout=5.0)
    return _http


def _headers(acting_user: int | None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {os.environ.get('TASKIFY_API_TOKEN', '')}"}
    if acting_user is not None:
        headers["X-Acting-User"] = str(acting_user)
    return headers


def request(
    method: str,
    path: str,
    acting_user: int | None = None,
    json: Any = None,
    params: dict[str, Any] | None = None,
) -> Any:
    """Call the API and return the decoded JSON body.

    Args:
        method: HTTP method.
        path: Path below ``/api/v1``, e.g. ``/projects``.
        acting_user: Id of the session user, sent as ``X-Acting-User``.
        json: Optional JSON body.
        params: Optional query parameters.

    Raises:
        ApiError: For 4xx responses from the API (message passed through), and with a
            generic message for authentication, server or connection failures.
    """
    try:
        resp = _client().request(
            method, API_PREFIX + path, headers=_headers(acting_user), json=json, params=params
        )
    except httpx.HTTPError:
        raise ApiError(503, "The service is temporarily unavailable. Please try again.") from None
    if resp.status_code >= 500 or resp.status_code == 401:
        raise ApiError(502, "The service is temporarily unavailable. Please try again.")
    if resp.status_code >= 400:
        try:
            err = resp.json()["error"]
            raise ApiError(resp.status_code, str(err["message"]), err.get("field"))
        except (ValueError, KeyError, TypeError):
            raise ApiError(resp.status_code, "The request could not be completed.") from None
    return resp.json()


def stream_events() -> Iterator[str]:
    """Yield raw lines of the API event stream (reconnect is handled by the browser)."""
    with httpx.stream(
        "GET",
        os.environ.get("TASKIFY_API_URL", "http://localhost:8001") + API_PREFIX + "/events",
        headers=_headers(None),
        timeout=httpx.Timeout(5.0, read=None),
    ) as resp:
        if resp.status_code != 200:
            raise ApiError(502, "The event stream is unavailable.")
        yield from resp.iter_lines()
