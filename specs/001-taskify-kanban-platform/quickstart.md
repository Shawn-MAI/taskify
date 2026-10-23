# Quickstart: Taskify Kanban Platform

Validation guide; commands assume the layout in [plan.md](./plan.md).

## Prerequisites

- Python 3.12, pip
- Environment: `TASKIFY_API_TOKEN` (any random value, shared by both services), `DJANGO_SECRET_KEY`

## Run

1. API: `cd services/api && pip install -r requirements.txt && uvicorn app.main:app --port 8001` (seeds 5 users and 3 projects on first start).
2. Web: `cd services/web && pip install -r requirements.txt && python manage.py runserver 8000`.

## Validation scenarios

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Open `http://localhost:8000`, pick a user | Three sample projects listed; chosen user shown (US1) |
| 2 | Open a project | Columns To Do, In Progress, In Review, Done with sample tasks (US1) |
| 3 | Drag a card to another column, reload | Card stays in the new column (US2) |
| 4 | Open the board in two browsers; move a card in one | Other browser updates within 2 s without refresh |
| 5 | Create a project and a task, assign it to another user | Task in To Do with assignee; assignee gets a notification (US3) |
| 6 | Clear the assignee | Card shows Unassigned |
| 7 | Add a comment | Listed with author and time; assignee notified (US4) |
| 8 | Submit empty or over-length title/comment; `<script>` text | Rejected with message / shown as plain text (FR-010, FR-011) |
| 9 | `curl localhost:8001/api/v1/projects` without token | 401 |
| 10 | `curl localhost:8001/health` | 200 |

## Automated checks

- `cd services/api && pytest` (unit, integration, contract against [api-v1.openapi.yaml](./contracts/api-v1.openapi.yaml))
- `cd services/web && pytest`
