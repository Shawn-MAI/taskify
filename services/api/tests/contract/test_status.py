"""Contract tests for ``PUT /tasks/{id}/status`` (T024)."""


def test_status_response_matches_contract(client, H, check_schema):
    r = client.put("/api/v1/tasks/1/status", json={"status": "done"}, headers=H(1))
    assert r.status_code == 200
    check_schema("Task", r.json())


def test_invalid_status_is_422(client, H):
    r = client.put("/api/v1/tasks/1/status", json={"status": "blocked"}, headers=H(1))
    assert r.status_code == 422
    assert r.json()["error"]["field"] == "status"
    assert "must be one of" in r.json()["error"]["message"]


def test_extra_field_rejected(client, H):
    r = client.put("/api/v1/tasks/1/status", json={"status": "done", "x": 1}, headers=H(1))
    assert r.status_code == 422


def test_unknown_task_404(client, H):
    assert client.put("/api/v1/tasks/9999/status", json={"status": "done"}, headers=H(1)).status_code == 404
