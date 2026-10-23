"""Polish checks: contract sync (T045), security (T048), spoofed identity (T049), performance (T051)."""

import re
import time

import yaml

from tests.conftest import CONTRACT


def test_every_contract_route_is_implemented(app):
    spec = yaml.safe_load(CONTRACT.read_text())
    norm = lambda p: re.sub(r"\{[^}]+\}", "{}", p)
    served = {norm(p): p for p in app.openapi()["paths"]}
    for path, ops in spec["paths"].items():
        if path == "/health":
            continue
        match = served.get(norm("/api/v1" + path)) or served.get(norm(path))
        assert match, path
        assert set(ops) <= set(app.openapi()["paths"][match]), path


def test_no_stack_trace_or_token_in_errors(client, H):
    for r in (
        client.get("/api/v1/tasks/999999", headers=H(1)),
        client.put("/api/v1/tasks/1/status", json={"status": "nope"}, headers=H(1)),
        client.get("/api/v1/projects", headers={}),
    ):
        text = r.text
        assert "Traceback" not in text and "test-token" not in text and "sqlalchemy" not in text.lower()


def test_unknown_acting_user_rejected(client, H):
    assert client.get("/api/v1/projects", headers=H(9999)).status_code == 404
    assert client.get("/api/v1/projects", headers=H(None)).status_code == 422


def test_acting_user_recorded_in_activity(client, H):
    client.put("/api/v1/tasks/1/status", json={"status": "done"}, headers=H(4))
    assert client.get("/api/v1/tasks/1", headers=H(1)).json()["activity"][0]["actor_id"] == 4


def test_board_with_100_tasks_loads_under_one_second(client, H):
    for i in range(100):
        r = client.post("/api/v1/projects/1/tasks", json={"title": f"perf {i}"}, headers=H(1))
        assert r.status_code == 201
    start = time.perf_counter()
    r = client.get("/api/v1/projects/1", headers=H(1))
    assert r.status_code == 200
    assert time.perf_counter() - start < 1.0
