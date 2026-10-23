"""Contract tests for task detail and comments (T037)."""


def test_task_detail_matches_contract(client, H, check_schema):
    r = client.get("/api/v1/tasks/1", headers=H(1))
    assert r.status_code == 200
    check_schema("TaskDetail", r.json())


def test_comment_matches_contract(client, H, check_schema):
    r = client.post("/api/v1/tasks/1/comments", json={"body": "hi"}, headers=H(2))
    assert r.status_code == 201
    check_schema("Comment", r.json())
    detail = client.get("/api/v1/tasks/1", headers=H(1)).json()
    check_schema("TaskDetail", detail)
    assert detail["activity"][0]["action"] == "commented"
