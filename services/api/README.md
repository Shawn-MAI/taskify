# Taskify API service

FastAPI + SQLAlchemy + SQLite (WAL). REST under `/api/v1`, live events over SSE at `/api/v1/events`.

## Run

```sh
export TASKIFY_API_TOKEN=<long random value>
uvicorn app.main:create_app --factory --port 8001
```

## Security (Phase 1)

- Every endpoint except `/health` needs `Authorization: Bearer $TASKIFY_API_TOKEN`; otherwise 401.
- `X-Acting-User` names the acting user. It is **spoofable by any token holder**. This is an accepted
  Phase-1 risk (constitution v1.1.0) until `002-user-authentication`. Keep the service on a trusted network.
- All input is validated by Pydantic schemas; errors are `{"error": {"code", "message", "field"?}}`.

## Test

```sh
python -m pytest -q
```

Contract: `specs/001-taskify-kanban-platform/contracts/api-v1.openapi.yaml`.
