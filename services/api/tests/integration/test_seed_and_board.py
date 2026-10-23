"""Seed data, board layout and access control (T019)."""


def test_seed_users(client, H):
    users = client.get("/api/v1/users", headers=H(None)).json()
    assert len(users) == 5
    assert [u["role"] for u in users].count("product_manager") == 1
    assert [u["role"] for u in users].count("engineer") == 4


def test_seed_projects_and_columns(client, H):
    projects = client.get("/api/v1/projects", headers=H(1)).json()
    assert len(projects) == 3
    for p in projects:
        board = client.get(f"/api/v1/projects/{p['id']}", headers=H(1)).json()
        assert list(board["columns"]) == ["todo", "in_progress", "in_review", "done"]
        assert sum(len(c) for c in board["columns"].values()) > 0


def test_users_needs_token_only(client, H):
    assert client.get("/api/v1/users", headers=H(None)).status_code == 200
    assert client.get("/api/v1/users", headers=H(None, token=None)).status_code == 401
    assert client.get("/api/v1/users", headers=H(None, token="wrong")).status_code == 401


def test_projects_require_token(client, H):
    assert client.get("/api/v1/projects", headers=H(1, token=None)).status_code == 401


def test_acting_user_must_exist(client, H):
    assert client.get("/api/v1/projects", headers=H(999)).status_code == 404
    assert client.get("/api/v1/projects", headers=H(None)).status_code == 422
    assert client.get("/api/v1/projects", headers={**H(None), "X-Acting-User": "abc"}).status_code == 422


def test_unknown_project_404(client, H):
    assert client.get("/api/v1/projects/9999", headers=H(1)).status_code == 404


def test_health_is_open(client):
    assert client.get("/health").status_code == 200
