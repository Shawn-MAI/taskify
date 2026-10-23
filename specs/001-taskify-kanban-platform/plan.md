# Implementation Plan: Taskify Kanban Platform

**Branch**: `001-taskify-kanban-platform` | **Date**: 2026-10-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-taskify-kanban-platform/spec.md`

## Summary

Two independently deployable Python services. The **API service** owns all data in SQLite and exposes REST endpoints for users, projects, tasks, comments, and notifications, plus a live event stream. The **Web service** is a Django app that renders the project list and Kanban board, supports drag-and-drop card moves, and updates boards in real time by consuming the API's event stream. Five users and three sample projects are seeded; no login (identity is a selected user).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: API: FastAPI, Pydantic v2, SQLAlchemy 2, uvicorn. Web: Django 5, httpx. Browser: native HTML5 drag-and-drop and EventSource (no JS framework).

**Storage**: SQLite (file, owned exclusively by the API service)

**Testing**: pytest (API unit, contract, integration), Django test runner via pytest-django (web)

**Target Platform**: Linux/macOS containers; desktop browsers

**Project Type**: web application composed of two services (web + api)

**Performance Goals**: Board with 100 tasks renders under 1 s; move visible to other viewers within 2 s

**Constraints**: SQLite single-writer (WAL mode); live updates via Server-Sent Events; all validation server-side in the API; each service containerized with a health endpoint

**Scale/Scope**: 5 users, 3+ projects, up to ~100 tasks per board

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Security-First | Threat surface documented; no secrets in repo; deny-by-default; TLS in transit | PASS under the constitution v1.1.0 Phase-1 Authentication Exception (spec FR-002 omits login). Conditions: services token-authenticated and deny by default at the service boundary (service token from env, 401 otherwise); non-secure identity and risks documented in the Threat Surface below; follow-up feature `002-user-authentication` scheduled. CSRF protection on in Django. |
| II. Input Validation | Server-side allow-list schemas for every endpoint; parameterized queries; output encoding | PASS (Pydantic schemas, SQLAlchemy ORM, Django auto-escaping) |
| III. Microservices | Independent services, own data store, versioned contracts | PASS (web and api, `/api/v1`, only api touches SQLite) |
| IV. Documentation | Docstrings, service READMEs, OpenAPI | PASS (OpenAPI generated and saved in `contracts/`) |
| V. Test-Driven | Negative tests, contract tests, CI | PASS (see structure) |

Post-design re-check: PASS; same exception applies.

### Threat Surface (Phase-1 Authentication Exception)

| Asset / entry point | Threat | Mitigation | Accepted residual risk |
|---------------------|--------|------------|------------------------|
| API service endpoints (`/api/v1/*`) | Unauthorized callers | Bearer service token from `TASKIFY_API_TOKEN`; 401 without it; only `/health` is open | Any holder of the token can call the API |
| Acting-user identity (`X-Acting-User`) | Spoofing: a caller can act as any of the five users | Web service sets it from the session; API verifies the user exists | Identity is a claim, not authenticated; actions and notifications can be attributed to the wrong user. Authorization is the same for all users (FR-013) |
| Task, project, and comment text | Injection / XSS | Server-side allow-list validation, parameterized queries, Django auto-escaping, `textContent` in the browser | None expected |
| Web forms and moves | CSRF | Django CSRF tokens on all state-changing requests | None expected |
| Event stream (`/events`) | Information disclosure to anyone with the token | Same token requirement; events carry ids and status only, no comment bodies | All users may see all projects by design |
| Secrets | Leakage | Env-only configuration, `.env.example` without values, no secrets in logs | None expected |
| Transport | Eavesdropping | TLS terminated in front of both services in any deployed environment | Local development runs over HTTP |

Deployment boundary: Phase 1 MUST run only on a trusted network, not on the public internet, until the follow-up feature ships.

## Project Structure

### Documentation (this feature)

```text
specs/001-taskify-kanban-platform/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api-v1.openapi.yaml
└── tasks.md             # created later by /speckit-tasks
```

### Source Code (repository root)

```text
services/
├── api/
│   ├── README.md
│   ├── app/
│   │   ├── main.py          # app, health, router wiring
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── schemas.py       # Pydantic validation schemas
│   │   ├── db.py            # SQLite engine (WAL)
│   │   ├── seed.py          # 5 users, 3 projects, sample tasks
│   │   ├── events.py        # in-process pub/sub for SSE
│   │   ├── security.py      # service-token and acting-user dependencies
│   │   ├── services/        # business logic, e.g. notifications.py
│   │   └── routers/         # users, projects, tasks, comments, notifications, events
│   └── tests/
│       ├── contract/
│       ├── integration/
│       └── unit/
└── web/
    ├── README.md
    ├── manage.py
    ├── taskify_web/         # Django project settings
    ├── boards/
    │   ├── views.py         # pages, thin proxy for browser SSE
    │   ├── api_client.py    # httpx client to API service
    │   ├── templates/boards/
    │   └── static/boards/   # board.js (drag-drop, EventSource), board.css
    └── tests/
```

**Structure Decision**: Two-service web application (`services/api`, `services/web`), satisfying the microservices principle. The web service holds no business data and never opens the SQLite file.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| No end-user authentication (Principle I) | Spec explicitly scopes login out of phase one; allowed by the constitution's Phase-1 Authentication Exception | Adding login contradicts the approved spec. Time-boxed: expires when follow-up feature `002-user-authentication` (login, per-user authorization) ships; mitigated by service token, CSRF, strict validation, and the Threat Surface above |
| Two services for a small app | Constitution requires microservices | A single Django monolith violates Principle III |
