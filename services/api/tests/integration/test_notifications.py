"""Notification rules and endpoints (T031)."""


def _notes(client, H, user, **params):
    return client.get("/api/v1/notifications", headers=H(user), params=params).json()


def test_assignment_notifies_new_assignee(client, H, check_schema):
    client.put("/api/v1/tasks/1/assignee", json={"assignee_id": 3}, headers=H(2))
    notes = _notes(client, H, 3)
    assert notes and notes[0]["type"] == "task_assigned" and notes[0]["actor_id"] == 2
    check_schema("Notification", notes[0])


def test_no_notification_for_own_action(client, H):
    client.put("/api/v1/tasks/1/assignee", json={"assignee_id": 3}, headers=H(3))
    assert _notes(client, H, 3) == []


def test_creating_assigned_task_notifies(client, H):
    client.post("/api/v1/projects/1/tasks", json={"title": "n", "assignee_id": 4}, headers=H(1))
    assert len(_notes(client, H, 4)) == 1


def test_newest_first_and_unread_filter_and_mark_read(client, H):
    client.put("/api/v1/tasks/1/assignee", json={"assignee_id": 3}, headers=H(2))
    client.put("/api/v1/tasks/2/assignee", json={"assignee_id": 3}, headers=H(2))
    notes = _notes(client, H, 3)
    assert [n["id"] for n in notes] == sorted((n["id"] for n in notes), reverse=True)
    r = client.post(f"/api/v1/notifications/{notes[0]['id']}/read", headers=H(3))
    assert r.status_code == 200 and r.json()["read"] is True
    unread = _notes(client, H, 3, unread="true")
    assert [n["id"] for n in unread] == [notes[1]["id"]]


def test_only_recipient_can_mark_read(client, H):
    client.put("/api/v1/tasks/1/assignee", json={"assignee_id": 3}, headers=H(2))
    nid = _notes(client, H, 3)[0]["id"]
    assert client.post(f"/api/v1/notifications/{nid}/read", headers=H(4)).status_code == 404
    assert _notes(client, H, 3)[0]["read"] is False
    assert client.post("/api/v1/notifications/9999/read", headers=H(3)).status_code == 404


def test_notifications_are_private(client, H):
    client.put("/api/v1/tasks/1/assignee", json={"assignee_id": 3}, headers=H(2))
    assert _notes(client, H, 4) == []
