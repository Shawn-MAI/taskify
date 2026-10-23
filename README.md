# Taskify

A team productivity platform: create projects, assign tasks, comment, and move tasks across Kanban columns
(To Do, In Progress, In Review, Done). Phase 1 ships with five predefined users (one product manager, four
engineers), three sample projects, and **no login** (you pick who you act as).

## Architecture

| Service | Path | Stack | Default port |
|---------|------|-------|--------------|
| API | [services/api](./services/api) | FastAPI, SQLAlchemy, SQLite (WAL), Server-Sent Events | 8001 |
| Web | [services/web](./services/web) | Django, httpx, HTML5 drag-and-drop, EventSource | 8000 |

The web service has no database; it calls the API with a shared service token and forwards the selected user
as `X-Acting-User`.

## Quick start

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r services/api/requirements.txt -r services/web/requirements-test.txt

export TASKIFY_API_TOKEN=<long random value>
export TASKIFY_API_URL=http://localhost:8001
export DJANGO_SECRET_KEY=<random value>

# terminal 1
cd services/api && uvicorn app.main:create_app --factory --port 8001

# terminal 2
cd services/web && python manage.py runserver 8000
```

Open <http://localhost:8000>, choose a user, and open a project board. See [.env.example](./.env.example)
for all variables.

## Tests

```sh
cd services/api && python -m pytest -q
cd services/web && python -m pytest -q
```

## Security (Phase 1)

- Every API endpoint except `/health` requires a bearer service token.
- All inputs are validated; errors never expose stack traces or secrets.
- With no login, the acting user is spoofable by anyone with network access. Deploy only on a trusted network
  (see [deploy/README.md](./deploy/README.md)) until the follow-up `002-user-authentication` feature lands.

## Project docs

Specification, plan, data model, API contract and tasks live in
[specs/001-taskify-kanban-platform](./specs/001-taskify-kanban-platform). Governing principles are in
[.specify/memory/constitution.md](./.specify/memory/constitution.md).
