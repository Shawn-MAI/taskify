# Tasks: Taskify Kanban Platform

**Input**: Design documents from `/specs/001-taskify-kanban-platform/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-v1.openapi.yaml, quickstart.md

**Tests**: Included, because constitution Principle V (Test-Driven Verification) makes tests mandatory: negative tests for validation, and contract tests for the API.

**Organization**: Grouped by user story so each can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US1-US5)

## Path Conventions

Two services per plan.md: `services/api/` (FastAPI + SQLite) and `services/web/` (Django). Every public module, class, and function MUST carry docstrings (constitution Principle IV).

---

## Phase 1: Setup

- [X] T001 Create the directory layout from plan.md under `services/api/app/{routers,services}/`, `services/api/tests/{contract,integration,unit}/`, `services/web/taskify_web/`, `services/web/boards/{templates/boards,static/boards}/`, `services/web/tests/`, and `deploy/`
- [X] T002 [P] Create `services/api/requirements.txt` (fastapi, pydantic>=2, sqlalchemy>=2, uvicorn, pytest, httpx, openapi-core or schemathesis for contract checks) and `services/api/README.md` (purpose, env vars, run, test)
- [X] T003 [P] Create `services/web/requirements.txt` (django>=5, httpx, pytest, pytest-django), initialize Django project in `services/web/taskify_web/` and app `services/web/boards/`, and add `services/web/README.md`
- [X] T004 [P] Add `.gitignore` (SQLite db files, `.env`, `__pycache__`) and `.env.example` listing `TASKIFY_API_TOKEN`, `DJANGO_SECRET_KEY`, `TASKIFY_ENV` with no real values
- [X] T005 [P] Add Dockerfiles `services/api/Dockerfile` and `services/web/Dockerfile`, each running as non-root

---

## Phase 2: Foundational (blocks all stories)

- [X] T006 Implement SQLite engine with WAL mode and session dependency in `services/api/app/db.py`
- [X] T007 Implement SQLAlchemy models in `services/api/app/models.py` per data-model.md: User(name unique 1-80 chars, role enum product_manager|engineer), Project(name required 1-100 chars unique case-insensitive, description optional max 1000, created_by, created_at UTC), Task(project_id, title required 1-150, description optional max 2000, status enum todo|in_progress|in_review|done default todo, position int, assignee_id nullable, created_by, created_at/updated_at UTC), Comment(task_id, author_id, body required 1-2000 plain text, created_at UTC), Activity(task_id, actor_id, action enum created|moved|assigned|unassigned|commented, from_value nullable, to_value nullable, created_at UTC, index on task_id + created_at DESC), Notification(recipient_id, type task_assigned|task_commented, task_id, actor_id, message, read default false, created_at)
- [X] T008 [P] Implement Pydantic request/response schemas in `services/api/app/schemas.py` matching contracts/api-v1.openapi.yaml (including `Activity` and `TaskDetail.activity`), with `extra="forbid"` and the exact length limits listed in T007
- [X] T009 [P] Implement bearer service-token and `X-Acting-User` dependencies in `services/api/app/security.py`: deny by default, 401 for missing or invalid token (constant-time compare), 404/422 for unknown acting user; token read from `TASKIFY_API_TOKEN`; expose a token-only dependency for endpoints that do not need an acting user
- [X] T010 [P] Implement in-process pub/sub in `services/api/app/events.py`
- [X] T011 Implement app entry in `services/api/app/main.py`: router wiring under `/api/v1`, unauthenticated `/health`, consistent error format (no stack traces), a validation-error handler whose message names the affected field and the rule broken (FR-010, e.g. "title: must be 1-150 characters"), structured logging without sensitive data
- [X] T012 Implement seed script in `services/api/app/seed.py`: 1 product manager and 4 engineers, 3 sample projects with tasks spread across all four columns; idempotent; run on startup
- [X] T013 [P] Implement `GET /api/v1/users` in `services/api/app/routers/users.py` using the token-only dependency from T009 (requires the service token, does not require `X-Acting-User`, because the user is chosen from this list)
- [X] T014 [P] Implement activity service in `services/api/app/services/activity.py`: `record_activity(session, task_id, actor_id, action, from_value, to_value)` that writes within the caller's transaction (no record if the change fails or is a no-op), and a query returning the 20 newest records for a task (FR-012)
- [X] T015 [P] Create shared test fixtures (temp SQLite db, seeded data, auth headers) in `services/api/tests/conftest.py`
- [X] T016 [P] Implement API client in `services/web/boards/api_client.py` (httpx, token from env, forwards acting user taken only from the Django session, never from browser-supplied headers, timeouts, safe error mapping)
- [X] T017 [P] Configure Django settings in `services/web/taskify_web/settings.py` (secret key from env, CSRF on, DEBUG off by default, secure headers, `SECURE_SSL_REDIRECT`, secure cookies and HSTS when `TASKIFY_ENV=production`) and base template `services/web/boards/templates/boards/base.html` with auto-escaping and user selector storing the selected user in the session

**Checkpoint**: Foundation ready.

---

## Phase 3: User Story 1 - Choose a user and view project boards (P1) MVP

**Goal**: Pick one of five users, list three sample projects, view a four-column board.

**Independent Test**: Quickstart scenarios 1-2.

- [X] T018 [P] [US1] Contract test for `GET /users`, `GET /projects`, `GET /projects/{id}` against the OpenAPI file in `services/api/tests/contract/test_read_endpoints.py`
- [X] T019 [P] [US1] Integration test in `services/api/tests/integration/test_seed_and_board.py`: seed yields 5 users (1 product_manager, 4 engineer), 3 projects, board columns in order; `GET /users` works with the service token alone and returns 401 without it; `GET /projects` returns 401 without a token and 404/422 with an unknown `X-Acting-User`; 404 for unknown project
- [X] T020 [US1] Implement `GET /projects` and `GET /projects/{id}` (board grouped by status, ordered by position) in `services/api/app/routers/projects.py`
- [X] T021 [P] [US1] Web test for user selection and board rendering in `services/web/tests/test_board_views.py`
- [X] T022 [US1] Implement views and URLs for user selection, project list, and board in `services/web/boards/views.py` and `services/web/boards/urls.py`
- [X] T023 [P] [US1] Create templates `services/web/boards/templates/boards/{users,projects,board}.html` and `services/web/boards/static/boards/board.css` with four columns (To Do, In Progress, In Review, Done) and empty-column state

---

## Phase 4: User Story 2 - Move tasks across columns (P1)

**Goal**: Drag a card between columns; persists and is recorded in activity.

**Independent Test**: Quickstart scenarios 3-4.

- [X] T024 [P] [US2] Contract and integration tests for `PUT /tasks/{id}/status` in `services/api/tests/contract/test_status.py` and `services/api/tests/integration/test_move.py`: any-to-any moves incl. backward, same-status no-op (no activity record), persistence, one `moved` activity record with actor and from/to status, 422 on unknown status or extra fields, 404 unknown task
- [X] T025 [P] [US2] Test SSE stream emits `task_moved` after a move in `services/api/tests/integration/test_events.py`
- [X] T026 [US2] Implement `PUT /tasks/{id}/status` (appends to end of target column unless `position` >= 0 given; records a `moved` activity via T014; last write wins) in `services/api/app/routers/tasks.py`
- [X] T027 [US2] Implement `GET /api/v1/events` SSE endpoint and publish `task_moved` in `services/api/app/routers/events.py`
- [X] T028 [US2] Implement web move endpoint (CSRF-protected) and SSE relay streaming view in `services/web/boards/views.py`
- [ ] T029 [US2] Implement drag-and-drop, keyboard "Move to" menu, and move-on-drop with rollback on error, using `textContent` not `innerHTML`, in `services/web/boards/static/boards/board.js`

---

## Phase 5: User Story 3 - Create projects and tasks, assign tasks (P2)

**Goal**: Create projects and tasks, assign/reassign/clear assignee, with clear validation messages and activity records.

**Independent Test**: Quickstart scenarios 5-6, 8.

- [X] T030 [P] [US3] Contract and negative tests for `POST /projects`, `POST /projects/{id}/tasks`, `PUT /tasks/{id}/assignee` in `services/api/tests/contract/test_create_assign.py` and `services/api/tests/integration/test_create_assign.py`: empty/over-length name (>100), title (>150), description (>1000/2000), duplicate project name 409 (case-insensitive), unknown assignee 404, null assignee clears; script text stored verbatim; each 422 message names the field and rule (FR-010); `created`, `assigned` and `unassigned` activity records written, none on failure or unchanged assignee
- [X] T031 [P] [US3] Notification tests for `GET /notifications` and `POST /notifications/{id}/read` in `services/api/tests/integration/test_notifications.py`: assignment notifies the new assignee, none when actor is recipient, newest first, `unread` filter, only the recipient can mark read
- [X] T032 [US3] Implement `POST /projects` in `services/api/app/routers/projects.py`
- [X] T033 [US3] Implement `POST /projects/{id}/tasks` and `PUT /tasks/{id}/assignee` with `task_created` and `task_assigned` events and activity records via T014 in `services/api/app/routers/tasks.py`
- [X] T034 [US3] Implement notification creation service in `services/api/app/services/notifications.py` and endpoints in `services/api/app/routers/notifications.py`; push `notification_created` events
- [X] T035 [P] [US3] Web forms and views for new project, new task, and assignee selector (including "Unassigned") in `services/web/boards/views.py` and `services/web/boards/templates/boards/`; show the API's field-and-rule error message next to the form
- [X] T036 [P] [US3] Web tests for form validation messages (field and rule shown) and output escaping in `services/web/tests/test_forms.py`

---

## Phase 6: User Story 4 - Comment on tasks (P3)

**Goal**: Any user comments on any task; task detail shows comments and recent activity; assignee and prior commenters notified.

**Independent Test**: Quickstart scenario 7.

- [X] T037 [P] [US4] Contract and negative tests for `GET /tasks/{id}` and `POST /tasks/{id}/comments` in `services/api/tests/contract/test_comments.py` and `services/api/tests/integration/test_comments.py`: empty body, body over 2000 chars, unknown task, chronological order, a `commented` activity record, `activity` in task detail limited to 20 newest-first records with actor and time (FR-012), `task_commented` notification recipients (assignee plus prior commenters, excluding author)
- [X] T038 [US4] Implement `GET /tasks/{id}` (task, comments, activity) and `POST /tasks/{id}/comments` with `comment_added` event and `commented` activity in `services/api/app/routers/comments.py` and `services/api/app/routers/tasks.py`
- [X] T039 [US4] Extend `services/api/app/services/notifications.py` with comment notification rules
- [X] T040 [P] [US4] Web task detail view/modal with comment list and form, and a recent-activity list (action, user, time), in `services/web/boards/views.py`, `services/web/boards/templates/boards/task_detail.html`, and `board.js`; web test in `services/web/tests/test_comments.py`

---

## Phase 7: User Story 5 - Live board updates and notifications (P3)

**Goal**: Other viewers see changes within 2 seconds without reload, boards resync after a lost connection, and users can read and clear their notifications.

**Independent Test**: Quickstart scenarios for live updates and notifications (two browsers, two users).

- [X] T041 [P] [US5] Integration tests in `services/api/tests/integration/test_events.py`: `task_created`, `task_moved`, `task_assigned`, `comment_added`, and `notification_created` events are each delivered to a connected subscriber within 2 seconds; the stream rejects requests without the service token; events carry ids and status only, no comment bodies
- [X] T042 [US5] Implement web relay of all event types and add `board.js` handlers that update the board for task created/moved/reassigned and comment added without reload (FR-014), in `services/web/boards/views.py` and `services/web/boards/static/boards/board.js`
- [ ] T043 [US5] Implement EventSource reconnect in `services/web/boards/static/boards/board.js`: show a "reconnecting" state and re-fetch the full board on reconnect so no change is missed (FR-014); web test in `services/web/tests/test_live_updates.py` that the board endpoint returns current state
- [X] T044 [P] [US5] Web notification list (newest first, unread visibly distinguished, mark as read) and unread badge updated live from `notification_created`, in `services/web/boards/views.py`, `services/web/boards/templates/boards/notifications.html`, and `board.js` (FR-015, FR-016); web test in `services/web/tests/test_notifications.py`

---

## Phase 8: Polish & Cross-Cutting

- [X] T045 [P] Generate and commit the OpenAPI document from the running API and diff it against `specs/001-taskify-kanban-platform/contracts/api-v1.openapi.yaml` in `services/api/tests/contract/test_openapi_sync.py`
- [X] T046 [P] Add CI workflow `.github/workflows/ci.yml` running pytest for both services, dependency vulnerability scan (pip-audit), and lint
- [X] T047 [P] Documentation audit: docstrings on all public modules/classes/functions, finalize both service READMEs with env vars and security notes (no-login limitation, trusted-network-only deployment, follow-up feature `002-user-authentication`)
- [X] T048 [P] Security tests: no stack traces in error bodies, no secrets in logs, CSRF enforced, response headers in `services/api/tests/integration/test_security.py` and `services/web/tests/test_security.py`
- [X] T049 [P] Spoofed acting-user tests (accepted Phase-1 risk, plan.md Threat Surface) in `services/api/tests/integration/test_acting_user.py` and `services/web/tests/test_acting_user.py`: no token with any `X-Acting-User` is 401; a valid token with an unknown user id is rejected and changes no data; with a valid token the header decides attribution (activity and notifications use that user), documenting the residual risk; the web service ignores any `X-Acting-User` header sent by the browser and uses only the session user
- [X] T050 [P] TLS in transit for deployed environments: add `deploy/Caddyfile` (or equivalent reverse proxy) terminating TLS in front of both services, `deploy/README.md` stating that the API port is not exposed publicly and that Phase 1 runs only on a trusted network, and a test in `services/web/tests/test_security.py` that with `TASKIFY_ENV=production` the web service redirects HTTP to HTTPS and sets secure cookies and HSTS
- [ ] T051 [P] Timing checks for the success criteria: automated test in `services/api/tests/integration/test_performance.py` that a 100-task board loads in under 1 s (SC-006) and live events arrive within 2 s with five concurrent subscribers; add a timed manual walkthrough to `specs/001-taskify-kanban-platform/quickstart.md` for SC-001 (identity to board under 15 s), SC-002 (move under 5 s), SC-003 (create and assign under 1 min), and SC-004 (first-time users, 90% unaided)
- [ ] T052 Run all quickstart.md scenarios end-to-end, including the timed walkthrough from T051 and the two-browser live update and notification scenarios

---

## Dependencies & Execution Order

- Phase 1 then Phase 2 (blocks everything). T014 (activity service) is needed by all stories that change tasks.
- US1 (Phase 3) and US2 (Phase 4) are both P1; US2 needs the board from US1 for the UI (T028-T029 depend on T022-T023), but its API tasks are independent.
- US3 depends on Phase 2 and the events stream (T027); US4 depends on T034 (notification service) and T033 (task router).
- US5 depends on US2 (event stream and web relay), US3 (notifications), and US4 (comment events).
- Polish last; T049-T051 need the endpoints from US1-US5.
- Within a story: tests first (confirm they fail), then models/services, endpoints, then UI.

## Parallel Examples

- Phase 2: T008, T009, T010, T013, T014, T015, T016, T017 together after T006-T007.
- US1: T018, T019, T021 together; then T020 and T022-T023.
- US5: T041 and T044 together; T042 then T043 (same files).
- Polish: T045-T051 together once all stories are done.
- Services `api` and `web` tasks within a story can proceed in parallel once the contract is fixed.

## Implementation Strategy

- **MVP**: Phases 1-3 (view seeded boards), then add US2 for the core Kanban value.
- Deliver incrementally: US2, US3, US4, then US5; validate each with its quickstart scenarios before moving on.
- Phase 1 is a documented, time-boxed no-login exception (constitution v1.1.0); T049-T050 and T047 keep its conditions evidenced.

## Phase 9: Convergence

- [ ] T053 Add a web test in `services/web/tests/test_live_updates.py` that simulates a dropped SSE stream and asserts the full board is re-fetched on reconnect, and verify the `board.js` reconnect state in a browser per FR-014 (partial)
- [ ] T054 Verify `board.js` drag-and-drop, keyboard "Move to" menu and move-on-drop in a real browser, and add rollback-on-error handling for failed moves per US2 / T029 (partial)
- [X] T055 Add `services/web/tests/` coverage for the task dialog, comments display order, and notification list ordering/unread styling that currently has only API-level tests per FR-009, FR-016 (partial)
- [X] T056 Add the SC-006 five-concurrent-subscriber timing check for live events and a 100-task board web render test per SC-006 (partial)
- [X] T057 Add missing docstrings to `check` in `services/api/app/schemas.py` and the `decorator`/`wrapper` in `services/web/boards/views.py` per Constitution IV (partial)
- [ ] T058 Run the manual quickstart walkthrough with both services live (timed SC-001..SC-003, two-browser live update and notifications) and record results in quickstart.md per SC-001, SC-002, SC-003 (missing)
- [ ] T059 Define a sample size and method for SC-004 usability measurement and record the result per SC-004 (missing)
