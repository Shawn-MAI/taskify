"""Validation, assignment and activity tests (T030)."""

import pytest


def _activity(client, H, task_id):
    return client.get(f"/api/v1/tasks/{task_id}", headers=H(1)).json()["activity"]


@pytest.mark.parametrize(
    "payload,field,fragment",
    [
        ({"name": ""}, "name", "Name must be 1-100 characters"),
        ({"name": "   "}, "name", "Name must be 1-100 characters"),
        ({"name": "x" * 101}, "name", "Name must be 1-100 characters"),
        ({"name": "ok", "description": "x" * 1001}, "description", "Description must be at most 1000 characters"),
        ({}, "name", "Name is required"),
        ({"name": "ok", "extra": 1}, "extra", "not allowed"),
        ({"name": 5}, "name", "must be text"),
    ],
)
def test_project_validation(client, H, payload, field, fragment):
    before = len(client.get("/api/v1/projects", headers=H(1)).json())
    r = client.post("/api/v1/projects", json=payload, headers=H(1))
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["field"] == field and fragment in err["message"]
    assert len(client.get("/api/v1/projects", headers=H(1)).json()) == before


@pytest.mark.parametrize(
    "payload,field,fragment",
    [
        ({"title": ""}, "title", "Title must be 1-150 characters"),
        ({"title": "x" * 151}, "title", "Title must be 1-150 characters"),
        ({"title": "ok", "description": "x" * 2001}, "description", "at most 2000 characters"),
        ({"title": "ok", "assignee_id": "two"}, "assignee_id", "whole number"),
        ({"description": "no title"}, "title", "Title is required"),
    ],
)
def test_task_validation_changes_nothing(client, H, payload, field, fragment):
    before = client.get("/api/v1/projects/1", headers=H(1)).json()
    r = client.post("/api/v1/projects/1/tasks", json=payload, headers=H(1))
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["field"] == field and fragment in err["message"]
    assert client.get("/api/v1/projects/1", headers=H(1)).json() == before


def test_duplicate_project_name_case_insensitive(client, H):
    assert client.post("/api/v1/projects", json={"name": "Alpha"}, headers=H(1)).status_code == 201
    assert client.post("/api/v1/projects", json={"name": "ALPHA"}, headers=H(1)).status_code == 409
    assert client.post("/api/v1/projects", json={"name": "website redesign"}, headers=H(1)).status_code == 409


def test_boundary_lengths_accepted(client, H):
    assert client.post("/api/v1/projects", json={"name": "n" * 100, "description": "d" * 1000}, headers=H(1)).status_code == 201
    assert client.post("/api/v1/projects/1/tasks", json={"title": "t" * 150, "description": "d" * 2000}, headers=H(1)).status_code == 201


def test_unknown_references(client, H):
    assert client.post("/api/v1/projects/999/tasks", json={"title": "x"}, headers=H(1)).status_code == 404
    assert client.post("/api/v1/projects/1/tasks", json={"title": "x", "assignee_id": 999}, headers=H(1)).status_code == 404
    assert client.put("/api/v1/tasks/1/assignee", json={"assignee_id": 999}, headers=H(1)).status_code == 404
    assert client.put("/api/v1/tasks/999/assignee", json={"assignee_id": 1}, headers=H(1)).status_code == 404


def test_assignee_can_be_cleared_and_reassigned(client, H):
    r = client.put("/api/v1/tasks/1/assignee", json={"assignee_id": None}, headers=H(2))
    assert r.json()["assignee_id"] is None
    r = client.put("/api/v1/tasks/1/assignee", json={"assignee_id": 4}, headers=H(2))
    assert r.json()["assignee_id"] == 4
    assert client.put("/api/v1/tasks/1/assignee", json={}, headers=H(1)).status_code == 422


def test_task_created_without_assignee(client, H):
    r = client.post("/api/v1/projects/1/tasks", json={"title": "solo"}, headers=H(1))
    assert r.status_code == 201 and r.json()["assignee_id"] is None


def test_markup_stored_verbatim(client, H):
    text = "<script>alert(1)</script>"
    r = client.post("/api/v1/projects/1/tasks", json={"title": text}, headers=H(1))
    assert r.json()["title"] == text


def test_activity_created_assigned_unassigned(client, H):
    task_id = client.post("/api/v1/projects/1/tasks", json={"title": "A"}, headers=H(2)).json()["id"]
    client.put(f"/api/v1/tasks/{task_id}/assignee", json={"assignee_id": 3}, headers=H(2))
    client.put(f"/api/v1/tasks/{task_id}/assignee", json={"assignee_id": None}, headers=H(4))
    acts = _activity(client, H, task_id)
    assert [a["action"] for a in acts] == ["unassigned", "assigned", "created"]
    assert [a["actor_id"] for a in acts] == [4, 2, 2]
    assert (acts[1]["from_value"], acts[1]["to_value"]) == (None, "3")
    assert (acts[0]["from_value"], acts[0]["to_value"]) == ("3", None)


def test_unchanged_assignee_and_failures_write_no_activity(client, H):
    task_id = client.post("/api/v1/projects/1/tasks", json={"title": "A", "assignee_id": 3}, headers=H(2)).json()["id"]
    client.put(f"/api/v1/tasks/{task_id}/assignee", json={"assignee_id": 3}, headers=H(2))
    client.put(f"/api/v1/tasks/{task_id}/assignee", json={"assignee_id": 999}, headers=H(2))
    assert len(_activity(client, H, task_id)) == 1
