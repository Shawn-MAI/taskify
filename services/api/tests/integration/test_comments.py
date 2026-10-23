"""Comment behaviour, activity in task detail and comment notifications (T037)."""

import pytest


@pytest.mark.parametrize("body", ["", "   ", "x" * 2001])
def test_invalid_body_rejected_and_nothing_stored(client, H, body):
    r = client.post("/api/v1/tasks/1/comments", json={"body": body}, headers=H(2))
    assert r.status_code == 422
    assert r.json()["error"]["message"] == "Comment must be 1-2000 characters"
    assert client.get("/api/v1/tasks/1", headers=H(1)).json()["comments"] == []


def test_missing_body_and_unknown_task(client, H):
    assert client.post("/api/v1/tasks/1/comments", json={}, headers=H(2)).status_code == 422
    assert client.post("/api/v1/tasks/999/comments", json={"body": "x"}, headers=H(2)).status_code == 404
    assert client.get("/api/v1/tasks/999", headers=H(2)).status_code == 404


def test_boundary_body_accepted(client, H):
    assert client.post("/api/v1/tasks/1/comments", json={"body": "x" * 2000}, headers=H(2)).status_code == 201


def test_any_user_can_comment_chronological(client, H):
    for user, text in ((2, "one"), (3, "two"), (1, "three")):
        client.post("/api/v1/tasks/1/comments", json={"body": text}, headers=H(user))
    comments = client.get("/api/v1/tasks/1", headers=H(1)).json()["comments"]
    assert [c["body"] for c in comments] == ["one", "two", "three"]
    assert [c["author_id"] for c in comments] == [2, 3, 1]
    assert all(c["created_at"] for c in comments)


def test_markup_in_comment_stored_verbatim(client, H):
    r = client.post("/api/v1/tasks/1/comments", json={"body": "<b>x</b>"}, headers=H(2))
    assert r.json()["body"] == "<b>x</b>"


def test_activity_limited_to_20_newest_first(client, H):
    for i in range(25):
        client.post("/api/v1/tasks/1/comments", json={"body": str(i)}, headers=H(2))
    activity = client.get("/api/v1/tasks/1", headers=H(1)).json()["activity"]
    assert len(activity) == 20
    ids = [a["id"] for a in activity]
    assert ids == sorted(ids, reverse=True)
    assert all(a["actor_id"] and a["created_at"] for a in activity)


def test_comment_notifies_assignee_and_prior_commenters_not_author(client, H):
    task = client.post("/api/v1/projects/1/tasks", json={"title": "N", "assignee_id": 2}, headers=H(1)).json()["id"]
    url = f"/api/v1/tasks/{task}/comments"
    client.post(url, json={"body": "a"}, headers=H(3))  # notifies assignee 2
    client.post(url, json={"body": "b"}, headers=H(4))  # notifies 2 and 3
    client.post(url, json={"body": "c"}, headers=H(2))  # notifies 3 and 4, not 2

    def commented(user):
        notes = client.get("/api/v1/notifications", headers=H(user)).json()
        return [n for n in notes if n["type"] == "task_commented"]

    assert len(commented(2)) == 2
    assert len(commented(3)) == 2
    assert len(commented(4)) == 1
    assert commented(1) == []
