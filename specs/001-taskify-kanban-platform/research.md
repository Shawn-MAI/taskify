# Research: Taskify Kanban Platform

## Decision 1: API service framework
- **Decision**: FastAPI + Pydantic v2 + SQLAlchemy 2.
- **Rationale**: Python, schema-driven validation (Principle II), auto-generated OpenAPI (Principle IV), native async streaming for SSE.
- **Alternatives**: Django REST Framework (would blur the separation from the Django web service); Flask (manual validation and docs).

## Decision 2: Storage
- **Decision**: SQLite in WAL mode, owned by the API service only.
- **Rationale**: Requested; fits 5 users. WAL allows concurrent reads during writes.
- **Alternatives**: PostgreSQL (unnecessary for scale and not requested).

## Decision 3: Real-time updates
- **Decision**: Server-Sent Events from the API (`GET /api/v1/events`), relayed to the browser through a Django streaming view; in-process pub/sub.
- **Rationale**: One-way server push is all that is needed; no extra infrastructure; works with native EventSource and reconnects automatically.
- **Alternatives**: WebSockets/Django Channels (heavier, needs a channel layer); polling (slower, wasteful).
- **Limit**: In-process pub/sub means a single API worker; acceptable at this scale.

## Decision 4: Drag-and-drop
- **Decision**: Native HTML5 drag-and-drop with a keyboard-accessible "Move to" menu fallback.
- **Rationale**: No dependency; accessible alternative.
- **Alternatives**: SortableJS (extra dependency, not needed).

## Decision 5: Notifications
- **Decision**: Stored in-app notifications created on task assignment to a user and on new comments on tasks assigned to or commented by others; exposed via REST (list, mark read) and pushed as SSE events.
- **Rationale**: User requested notification APIs; the spec was amended accordingly.
- **Alternatives**: Email/push (out of scope).

## Decision 6: Identity without login
- **Decision**: Browser sends the selected user id as `X-Acting-User` to the web service, which forwards it to the API with a shared service token (`TASKIFY_API_TOKEN` from env). API validates the user exists.
- **Rationale**: Meets FR-002 and FR-012 while keeping the API from being open; clearly documented as non-secure identity.
- **Alternatives**: Full auth (out of scope for this phase).

## Decision 7: Concurrency
- **Decision**: Last write wins on moves; each task has a `position` within its column, and moves append to the end of the target column unless a position is given.
- **Rationale**: Matches the spec edge case.

## Decision 8: Testing
- **Decision**: pytest with FastAPI TestClient; contract tests validate responses against the OpenAPI document; negative validation tests per endpoint.
