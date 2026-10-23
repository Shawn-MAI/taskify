"""Shared fixtures: temp SQLite database, seeded data, auth headers, contract checker."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft7Validator

from app.main import create_app

TOKEN = "test-token"
CONTRACT = Path(__file__).resolve().parents[3] / "specs/001-taskify-kanban-platform/contracts/api-v1.openapi.yaml"


@pytest.fixture
def app(tmp_path, monkeypatch):
    """A fresh app with its own seeded database."""
    monkeypatch.setenv("TASKIFY_API_TOKEN", TOKEN)
    return create_app(str(tmp_path / "test.db"))


@pytest.fixture
def client(app):
    """Test client that returns 500 responses instead of raising."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def auth(user_id: int | None = 1, token: str | None = TOKEN) -> dict[str, str]:
    """Build request headers; pass ``None`` to omit the token or acting user."""
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if user_id is not None:
        headers["X-Acting-User"] = str(user_id)
    return headers


@pytest.fixture
def H():
    """Header factory, e.g. ``H(2)`` acts as user 2."""
    return auth


@pytest.fixture(scope="session")
def contract() -> dict:
    """The parsed OpenAPI contract."""
    return yaml.safe_load(CONTRACT.read_text())


def _convert(node, spec):
    """Resolve $ref and translate OpenAPI 3.0 ``nullable`` into JSON Schema."""
    if isinstance(node, dict):
        if "$ref" in node:
            return _convert(spec["components"]["schemas"][node["$ref"].split("/")[-1]], spec)
        out = {k: _convert(v, spec) for k, v in node.items()}
        if out.pop("nullable", False) and "type" in out:
            out["type"] = [out["type"], "null"]
            if "enum" in out:
                out["enum"] = [*out["enum"], None]
        return out
    if isinstance(node, list):
        return [_convert(v, spec) for v in node]
    return node


@pytest.fixture
def check_schema(contract):
    """Return ``check(name, data)`` asserting data matches a components schema."""

    def check(name: str, data) -> None:
        schema = _convert({"$ref": f"#/components/schemas/{name}"}, contract)
        errors = list(Draft7Validator(schema).iter_errors(data))
        assert not errors, [e.message for e in errors]

    return check
