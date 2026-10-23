"""Server-Sent Events: delivery of every event type within 2 seconds (T025, T041)."""

from __future__ import annotations

import json
import queue
import socket
import threading
import time

import httpx
import pytest
import uvicorn

from app.main import create_app

TOKEN = "test-token"


@pytest.fixture
def live(tmp_path, monkeypatch):
    """Run the real app on a free local port; yield its base URL."""
    monkeypatch.setenv("TASKIFY_API_TOKEN", TOKEN)
    app = create_app(str(tmp_path / "live.db"))
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 5
    while not server.started and time.time() < deadline:
        time.sleep(0.02)
    assert server.started
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    server.force_exit = True
    thread.join(timeout=5)


class Subscriber:
    """Reads the event stream in a thread and records (event, arrival time)."""

    def __init__(self, base: str, token: str | None = TOKEN):
        self.events: queue.Queue = queue.Queue()
        self.ready = threading.Event()
        self.status: int | None = None
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._thread = threading.Thread(target=self._run, args=(base, headers), daemon=True)
        self._thread.start()
        assert self.ready.wait(5)

    def _run(self, base, headers):
        with httpx.Client(timeout=None) as client:
            with client.stream("GET", f"{base}/api/v1/events", headers=headers) as r:
                self.status = r.status_code
                self.ready.set()
                if r.status_code != 200:
                    return
                for line in r.iter_lines():
                    if line.startswith("data: "):
                        self.events.put((json.loads(line[6:]), time.monotonic()))

    def wait_for(self, type_: str, timeout: float = 2.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                event, ts = self.events.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                break
            if event["type"] == type_:
                return event, ts
        raise AssertionError(f"no {type_} event within {timeout}s")


def _h(user=1):
    return {"Authorization": f"Bearer {TOKEN}", "X-Acting-User": str(user)}


def test_stream_requires_token(live):
    assert Subscriber(live, token=None).status == 401
    assert Subscriber(live, token="wrong").status == 401


def test_all_event_types_arrive_within_two_seconds(live):
    sub = Subscriber(live)
    with httpx.Client(base_url=f"{live}/api/v1") as c:
        t0 = time.monotonic()
        task = c.post("/projects/1/tasks", json={"title": "live", "assignee_id": 3}, headers=_h(2)).json()
        _, ts = sub.wait_for("task_created")
        assert ts - t0 < 2
        sub.wait_for("notification_created")

        t0 = time.monotonic()
        c.put(f"/tasks/{task['id']}/status", json={"status": "done"}, headers=_h(2))
        moved, ts = sub.wait_for("task_moved")
        assert ts - t0 < 2 and moved["status"] == "done"

        c.put(f"/tasks/{task['id']}/assignee", json={"assignee_id": 4}, headers=_h(2))
        assigned, _ = sub.wait_for("task_assigned")
        assert assigned["assignee_id"] == 4

        c.post(f"/tasks/{task['id']}/comments", json={"body": "secret comment body"}, headers=_h(3))
        commented, _ = sub.wait_for("comment_added")
        note, _ = sub.wait_for("notification_created")
        assert note["recipient_id"] == 4
        assert "secret comment body" not in json.dumps([moved, assigned, commented, note])
        assert "body" not in commented


def test_failed_change_publishes_nothing(live):
    sub = Subscriber(live)
    with httpx.Client(base_url=f"{live}/api/v1") as c:
        c.post("/projects/1/tasks", json={"title": ""}, headers=_h(2))
    with pytest.raises(AssertionError):
        sub.wait_for("task_created", timeout=0.5)
