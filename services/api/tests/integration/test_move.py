"""Moving tasks between columns (T024)."""


def _task(client, H, task_id=1):
    return client.get(f"/api/v1/tasks/{task_id}", headers=H(1)).json()


def test_any_to_any_including_backward(client, H):
    for status in ("done", "in_progress", "todo", "in_review"):
        r = client.put("/api/v1/tasks/1/status", json={"status": status}, headers=H(2))
        assert r.status_code == 200 and r.json()["status"] == status
        assert _task(client, H)["status"] == status


def test_move_records_one_activity(client, H):
    before = _task(client, H)
    client.put("/api/v1/tasks/1/status", json={"status": "done"}, headers=H(3))
    activity = _task(client, H)["activity"]
    assert len(activity) == len(before["activity"]) + 1
    assert activity[0]["action"] == "moved"
    assert activity[0]["actor_id"] == 3
    assert (activity[0]["from_value"], activity[0]["to_value"]) == (before["status"], "done")


def test_same_status_is_noop(client, H):
    task = _task(client, H)
    r = client.put("/api/v1/tasks/1/status", json={"status": task["status"]}, headers=H(1))
    assert r.status_code == 200
    assert len(_task(client, H)["activity"]) == len(task["activity"])


def test_position_inserts_and_orders(client, H):
    board = client.get("/api/v1/projects/1", headers=H(1)).json()
    todo_ids = [t["id"] for t in board["columns"]["todo"]]
    moved = board["columns"]["in_progress"][0]["id"]
    client.put(f"/api/v1/tasks/{moved}/status", json={"status": "todo", "position": 0}, headers=H(1))
    board = client.get("/api/v1/projects/1", headers=H(1)).json()
    assert [t["id"] for t in board["columns"]["todo"]] == [moved, *todo_ids]
    assert [t["position"] for t in board["columns"]["todo"]] == list(range(len(todo_ids) + 1))


def test_move_appends_to_end(client, H):
    board = client.get("/api/v1/projects/1", headers=H(1)).json()
    done_ids = [t["id"] for t in board["columns"]["done"]]
    client.put("/api/v1/tasks/1/status", json={"status": "done"}, headers=H(1))
    board = client.get("/api/v1/projects/1", headers=H(1)).json()
    assert [t["id"] for t in board["columns"]["done"]] == [*done_ids, 1]


def test_negative_position_422(client, H):
    r = client.put("/api/v1/tasks/1/status", json={"status": "done", "position": -1}, headers=H(1))
    assert r.status_code == 422
