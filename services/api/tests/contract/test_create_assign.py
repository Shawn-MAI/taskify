"""Contract and negative tests for create/assign endpoints (T030)."""


def test_create_project_matches_contract(client, H, check_schema):
    r = client.post("/api/v1/projects", json={"name": "Alpha", "description": "d"}, headers=H(1))
    assert r.status_code == 201
    check_schema("Project", r.json())


def test_create_task_matches_contract(client, H, check_schema):
    r = client.post("/api/v1/projects/1/tasks", json={"title": "T", "assignee_id": 2}, headers=H(1))
    assert r.status_code == 201
    check_schema("Task", r.json())
    assert r.json()["status"] == "todo"


def test_assign_matches_contract(client, H, check_schema):
    r = client.put("/api/v1/tasks/1/assignee", json={"assignee_id": 3}, headers=H(1))
    assert r.status_code == 200
    check_schema("Task", r.json())


def test_error_body_shape(client, H):
    r = client.post("/api/v1/projects", json={"name": ""}, headers=H(1))
    assert r.status_code == 422
    assert set(r.json()["error"]) >= {"code", "message", "field"}
