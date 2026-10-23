# Data Model: Taskify Kanban Platform

All entities live in the API service's SQLite database. IDs are integers.

## User
| Field | Type | Rules |
|-------|------|-------|
| id | int | PK |
| name | text | required, unique, 1-80 chars |
| role | enum | `product_manager` or `engineer` |

Seeded: 1 product manager, 4 engineers. Read-only via the API.

## Project
| Field | Type | Rules |
|-------|------|-------|
| id | int | PK |
| name | text | required, 1-100 chars, unique (case-insensitive) |
| description | text | optional, max 1000 chars |
| created_by | FK User | required |
| created_at | datetime | UTC, set by server |

Seeded: 3 sample projects.

## Task
| Field | Type | Rules |
|-------|------|-------|
| id | int | PK |
| project_id | FK Project | required, must exist |
| title | text | required, 1-150 chars |
| description | text | optional, max 2000 chars |
| status | enum | `todo`, `in_progress`, `in_review`, `done`; default `todo` |
| position | int | order within project+status column |
| assignee_id | FK User | nullable; must exist if set |
| created_by | FK User | required |
| created_at / updated_at | datetime | UTC, server-set |

State transitions: any status to any other status (including backward). Same-status move is a no-op.

## Comment
| Field | Type | Rules |
|-------|------|-------|
| id | int | PK |
| task_id | FK Task | required, must exist |
| author_id | FK User | required |
| body | text | required, 1-2000 chars, plain text |
| created_at | datetime | UTC, server-set |

## Activity
Append-only record of changes to a task (FR-012). Never updated or deleted through the API.

| Field | Type | Rules |
|-------|------|-------|
| id | int | PK |
| task_id | FK Task | required, must exist |
| actor_id | FK User | required; the acting user |
| action | enum | `created`, `moved`, `assigned`, `unassigned`, `commented` |
| from_value | text | nullable; previous status or assignee id |
| to_value | text | nullable; new status or assignee id |
| created_at | datetime | UTC, server-set |

Rules: one record is written in the same transaction as the change it describes, so a failed change leaves no record. Same-status moves and unchanged assignments write nothing. `GET /tasks/{id}` returns the 20 newest records (index on `task_id, created_at DESC`), exposed as `activity` in `TaskDetail`.

## Notification
| Field | Type | Rules |
|-------|------|-------|
| id | int | PK |
| recipient_id | FK User | required |
| type | enum | `task_assigned`, `task_commented` |
| task_id | FK Task | required |
| actor_id | FK User | who caused it |
| message | text | server-generated |
| read | bool | default false |
| created_at | datetime | UTC |

Rules: no notification when the actor is the recipient. `task_assigned` goes to the new assignee. `task_commented` goes to the task's assignee and prior commenters, excluding the author.

## Relationships
User 1-* Task (assignee); Project 1-* Task; Task 1-* Comment; Task 1-* Activity; User 1-* Activity (actor); User 1-* Notification.
