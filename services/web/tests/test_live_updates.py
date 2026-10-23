"""Live updates, reconnect recovery, dialog/notification rendering and board size (FR-009, FR-014, FR-016, SC-006)."""

from __future__ import annotations

import json
import re
import time

from django.test import Client

from boards import views


def post_json(client, url, data):
    return client.post(url, json.dumps(data), content_type="application/json")


def test_relay_ends_cleanly_when_upstream_drops():
    """A dropped API stream ends the relay so the browser's EventSource reconnects."""
    lines = ["event: task_moved", 'data: {"type": "task_moved", "project_id": 1}', ""]

    def dropping():
        yield from lines
        raise ConnectionError("stream dropped")

    out = []
    try:
        for chunk in views.relay_blocks(dropping(), 1):
            out.append(chunk)
    except ConnectionError:
        pass
    assert out[0].startswith("retry:") and any("task_moved" in c for c in out)


def test_board_json_recovers_changes_missed_while_disconnected(pm):
    """After reconnect the browser re-fetches board.json and sees every missed change."""
    pid = pm.get("/projects/").context["projects"][0]["id"]
    before = pm.get(f"/projects/{pid}/board.json").json()
    other = Client()
    other.post("/", {"user_id": "2"})
    other.post(f"/projects/{pid}/tasks/new/", {"title": "Missed while offline", "description": ""})
    after = pm.get(f"/projects/{pid}/board.json").json()
    assert "Missed while offline" not in json.dumps(before)
    assert any(t["title"] == "Missed while offline" for t in after["columns"]["todo"])


def test_board_page_has_reconnect_indicator_and_script(pm):
    pid = pm.get("/projects/").context["projects"][0]["id"]
    html = pm.get(f"/projects/{pid}/").content.decode()
    assert 'id="connection-status"' in html and "board.js" in html


def test_comments_are_chronological_and_notifications_newest_first(pm):
    pid = pm.get("/projects/").context["projects"][0]["id"]
    tid = pm.get(f"/projects/{pid}/board.json").json()["columns"]["todo"][0]["id"]
    for body in ("first", "second", "third"):
        assert post_json(pm, f"/tasks/{tid}/comments/", {"body": body}).status_code == 201
    assert [c["body"] for c in pm.get(f"/tasks/{tid}/").json()["comments"]] == ["first", "second", "third"]

    post_json(pm, f"/tasks/{tid}/assign/", {"assignee_id": 2})
    other = Client()
    other.post("/", {"user_id": "2"})
    post_json(pm, f"/tasks/{tid}/comments/", {"body": "ping"})
    notes = other.get("/notifications.json").json()
    stamps = [n["created_at"] for n in notes]
    assert len(notes) >= 2 and stamps == sorted(stamps, reverse=True)
    assert all("read" in n for n in notes)


def test_board_with_100_tasks_renders_quickly(pm):
    pid = pm.get("/projects/").context["projects"][0]["id"]
    for i in range(100):
        pm.post(f"/projects/{pid}/tasks/new/", {"title": f"t{i}", "description": ""})
    start = time.perf_counter()
    resp = pm.get(f"/projects/{pid}/")
    assert resp.status_code == 200
    assert time.perf_counter() - start < 1.0
    assert len(re.findall(r'class="card"', resp.content.decode())) >= 100
