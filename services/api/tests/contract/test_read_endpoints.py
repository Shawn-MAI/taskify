"""Contract tests for read endpoints (T018)."""


def test_users_match_contract(client, H, check_schema):
    r = client.get("/api/v1/users", headers=H(None))
    assert r.status_code == 200
    for u in r.json():
        check_schema("User", u)


def test_projects_match_contract(client, H, check_schema):
    r = client.get("/api/v1/projects", headers=H(1))
    assert r.status_code == 200
    for p in r.json():
        check_schema("Project", p)


def test_board_matches_contract(client, H, check_schema):
    r = client.get("/api/v1/projects/1", headers=H(1))
    assert r.status_code == 200
    check_schema("Board", r.json())
