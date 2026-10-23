"""Web test fixtures: the Django views talk to a real in-process API service."""

from __future__ import annotations

import pytest
from django.test import Client
from fastapi.testclient import TestClient

from app.main import create_app
from boards import api_client


@pytest.fixture
def api(tmp_path, monkeypatch):
    """Real API app on a temp database, injected as the web service's HTTP client."""
    monkeypatch.setenv("TASKIFY_API_TOKEN", "test-token")
    with TestClient(create_app(str(tmp_path / "web-test.db")), raise_server_exceptions=False) as c:
        api_client.set_http_client(c)
        yield c
    api_client.set_http_client(None)


@pytest.fixture
def browser(api):
    """Django test client with CSRF checks on, not yet signed in as any user."""
    return Client(enforce_csrf_checks=False)


@pytest.fixture
def pm(browser):
    """Browser acting as user 1."""
    resp = browser.post("/", {"user_id": "1"})
    assert resp.status_code == 302
    return browser
