"""Web service tests: views, forms, relay, security (US1-US5, FR-011, T049)."""

from __future__ import annotations

import json

from django.test import Client

from boards import api_client, views


def post_json(client, url, data):
    return client.post(url, json.dumps(data), content_type="application/json")


def first_project(client):
    return client.get("/projects/").context["projects"][0]["id"]


def test_requires_user_selection(browser):
    assert browser.get("/projects/").status_code in (302, 401)
    assert browser.get("/projects/1/board.json").status_code in (401, 302)


def test_users_page_lists_five(browser):
    resp = browser.get("/")
    assert resp.status_code == 200
    assert len(resp.context["people"]) == 5


def test_invalid_user_choice_rejected(browser):
    assert browser.post("/", {"user_id": "999"}).status_code == 422
    assert browser.post("/", {"user_id": "abc"}).status_code == 422


def test_projects_and_board(pm):
    resp = pm.get("/projects/")
    assert resp.status_code == 200 and len(resp.context["projects"]) == 3
    pid = first_project(pm)
    board = pm.get(f"/projects/{pid}/")
    assert board.status_code == 200
    data = pm.get(f"/projects/{pid}/board.json").json()
    assert set(data["columns"]) == {"todo", "in_progress", "in_review", "done"}


def test_create_task_validation(pm):
    pid = first_project(pm)
    bad = pm.post(f"/projects/{pid}/tasks/new/", {"title": "   ", "description": ""})
    assert bad.status_code == 422
    ok = pm.post(f"/projects/{pid}/tasks/new/", {"title": "Web task", "description": "d"})
    assert ok.status_code == 302
    cols = pm.get(f"/projects/{pid}/board.json").json()["columns"]
    assert any(t["title"] == "Web task" for t in cols["todo"])


def test_move_assign_comment(pm):
    pid = first_project(pm)
    pm.post(f"/projects/{pid}/tasks/new/", {"title": "Flow", "description": ""})
    task = next(t for t in pm.get(f"/projects/{pid}/board.json").json()["columns"]["todo"] if t["title"] == "Flow")
    tid = task["id"]
    assert post_json(pm, f"/tasks/{tid}/move/", {"status": "in_review"}).status_code == 200
    assert post_json(pm, f"/tasks/{tid}/move/", {"status": "bogus"}).status_code in (400, 422)
    assert post_json(pm, f"/tasks/{tid}/assign/", {"assignee_id": 2}).status_code == 200
    assert post_json(pm, f"/tasks/{tid}/assign/", {"assignee_id": None}).status_code == 200
    assert post_json(pm, f"/tasks/{tid}/comments/", {"body": ""}).status_code in (400, 422)
    assert post_json(pm, f"/tasks/{tid}/comments/", {"body": "<b>hi</b>"}).status_code == 201
    detail = pm.get(f"/tasks/{tid}/").json()
    assert detail["comments"][0]["body"] == "<b>hi</b>"
    assert {a["action"] for a in detail["activity"]} >= {"created", "moved", "assigned", "unassigned", "commented"}


def test_markup_is_escaped_in_html(pm):
    pid = first_project(pm)
    pm.post(f"/projects/{pid}/tasks/new/", {"title": "<script>alert(1)</script>", "description": ""})
    html = pm.get(f"/projects/{pid}/").content.decode()
    assert "<script>alert(1)</script>" not in html


def test_notifications_flow(pm):
    pid = first_project(pm)
    pm.post(f"/projects/{pid}/tasks/new/", {"title": "N", "description": ""})
    tid = pm.get(f"/projects/{pid}/board.json").json()["columns"]["todo"][-1]["id"]
    post_json(pm, f"/tasks/{tid}/assign/", {"assignee_id": 2})
    other = Client()
    other.post("/", {"user_id": "2"})
    unread = other.get("/notifications.json?unread=true").json()
    assert len(unread) >= 1
    assert other.get("/notifications/").status_code == 200
    resp = other.post(f"/notifications/{unread[0]['id']}/read/", HTTP_X_REQUESTED_WITH="fetch")
    assert resp.status_code in (200, 204)
    assert len(other.get("/notifications.json?unread=true").json()) == len(unread) - 1


def test_acting_user_ignores_browser_header(pm, api, monkeypatch):
    """T049: X-Acting-User sent by the browser must never reach the API."""
    seen = []
    real = api.request

    def spy(method, url, **kw):
        seen.append(kw.get("headers", {}).get("X-Acting-User"))
        return real(method, url, **kw)

    monkeypatch.setattr(api, "request", spy)
    pm.get("/projects/", HTTP_X_ACTING_USER="3")
    assert seen and set(seen) == {"1"}


def test_csrf_enforced(api):
    strict = Client(enforce_csrf_checks=True)
    assert strict.post("/", {"user_id": "1"}).status_code == 403


def test_security_headers(browser):
    resp = browser.get("/")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "default-src" in csp and "unsafe-inline" not in csp
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"


def test_api_down_shows_safe_message(browser):
    import httpx

    api_client.set_http_client(httpx.Client(base_url="http://127.0.0.1:1", timeout=0.5))
    try:
        resp = browser.get("/")
    finally:
        api_client.set_http_client(None)
    body = resp.content.decode()
    assert resp.status_code >= 500 or "unavailable" in body
    assert "Traceback" not in body and "127.0.0.1" not in body


def test_relay_filters_other_users_notifications():
    def block(kind, **data):
        return ["event: " + kind, "data: " + json.dumps({"type": kind, **data}), ""]

    lines = block("notification_created", recipient_id=2) + block("task_moved", project_id=1) + block("notification_created", recipient_id=1)
    out = "".join(views.relay_blocks(iter(lines), 1))
    assert "task_moved" in out
    assert '"recipient_id": 1' in out and '"recipient_id": 2' not in out


def test_health_open(browser):
    assert browser.get("/health").status_code == 200
