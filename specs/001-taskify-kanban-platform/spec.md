# Feature Specification: Taskify Kanban Platform

**Feature Branch**: `001-taskify-kanban-platform`

**Created**: 2026-10-23

**Status**: Draft

**Input**: User description: "Develop Taskify, a team productivity platform where predefined users create projects, assign tasks, comment, and move tasks across Kanban columns (To Do, In Progress, In Review, Done). Five users (one product manager, four engineers), three sample projects, no login for this first phase."

## Clarifications

### Session 2026-10-23

- Q: Who is allowed to comment on a task? → A: Any of the five users can comment on any task in any project (user unavailable; recommended option applied).
- Q: Who may move or (re)assign a task? → A: Any user may move or assign any task, regardless of the current assignee or role (recommended default applied).
- Q: Must a task have an assignee? → A: No; assignee is optional, and a task can be unassigned again (recommended default applied).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Choose a user and view project boards (Priority: P1)

A team member opens Taskify, sees the five predefined users (one product manager, four engineers), and picks who they are acting as. They then see the list of projects (three samples pre-loaded) and open one to see its Kanban board with four columns: To Do, In Progress, In Review, Done.

**Why this priority**: Without user selection and a visible board, nothing else is usable. It delivers a viewable MVP with sample data.

**Independent Test**: Open the app, pick a user, open each sample project, and confirm the four columns and pre-loaded tasks display.

**Acceptance Scenarios**:

1. **Given** the app is opened, **When** the user selects any of the five predefined users, **Then** the project list shows the three sample projects and the selected user is shown as the current user.
2. **Given** a project is opened, **When** the board loads, **Then** four columns appear in order: To Do, In Progress, In Review, Done, each showing its tasks.

---

### User Story 2 - Move tasks across Kanban columns (Priority: P1)

A user drags (or otherwise moves) a task card from one column to another to reflect progress; the new status persists.

**Why this priority**: Moving tasks across columns is the core Kanban value.

**Independent Test**: Move a task from To Do to In Progress, reload, and confirm it remains there.

**Acceptance Scenarios**:

1. **Given** a task in To Do, **When** the user moves it to In Progress, **Then** the task appears in In Progress and is gone from To Do.
2. **Given** a moved task, **When** the page is reloaded, **Then** the task is still in its new column.
3. **Given** a task, **When** the user moves it to any other column (including backward), **Then** the move is allowed.

---

### User Story 3 - Create projects and tasks, assign tasks (Priority: P2)

A user creates a new project, adds tasks to it with a title and description, and assigns each task to one of the five users. New tasks start in To Do.

**Why this priority**: Extends the sample data into real team usage.

**Independent Test**: Create a project, add a task, assign it to an engineer, and see it on the board with the assignee shown.

**Acceptance Scenarios**:

1. **Given** the project list, **When** a user creates a project with a valid name, **Then** it appears in the list with an empty four-column board.
2. **Given** a board, **When** a user creates a task with a valid title, **Then** it appears in To Do.
3. **Given** a task, **When** the user assigns or reassigns it to a predefined user, **Then** the assignee is displayed on the card.
4. **Given** a task form, **When** the title is empty or exceeds the allowed length, **Then** the task is rejected with a clear error message.

---

### User Story 4 - Comment on tasks (Priority: P3)

A user opens a task and adds comments; comments show the author and time, in chronological order.

**Why this priority**: Enables team discussion but the board works without it.

**Independent Test**: Open a task, add a comment, and see it listed with author and timestamp.

**Acceptance Scenarios**:

1. **Given** an open task, **When** the current user submits a non-empty comment, **Then** it appears in the list attributed to that user with a timestamp.
2. **Given** an open task, **When** a comment is empty or over the length limit, **Then** it is rejected with a clear error message.

---

### User Story 5 - Live board updates and notifications (Priority: P3)

While several team members work on the same board, changes made by others appear without reloading the page. A user is notified in-app when a task is assigned to them or when someone comments on a task they are involved in.

**Why this priority**: Keeps the team in sync, but the board is fully usable without it.

**Independent Test**: Open the same board in two browsers, move a card in one, and see it move in the other; assign a task to the second user and see their notification.

**Acceptance Scenarios**:

1. **Given** two users viewing the same board, **When** one moves, creates, or reassigns a task, **Then** the other sees the change within 2 seconds without reloading.
2. **Given** a task, **When** it is assigned to a different user, **Then** the new assignee receives one notification naming the task and who assigned it.
3. **Given** a task with an assignee and earlier commenters, **When** another user comments, **Then** the assignee and earlier commenters (not the author) each receive one notification.
4. **Given** a user performs an action on a task, **Then** that user receives no notification for their own action.
5. **Given** unread notifications, **When** the user marks one as read, **Then** it no longer counts as unread.
6. **Given** the live connection is lost and then restored, **When** the board reconnects, **Then** it shows the current state of the board without a manual reload.

---

### Edge Cases

- A task is moved to the column it is already in: no change and no error.
- A task is unassigned: the card shows "Unassigned" and the task stays in its column.
- Two users move the same task at nearly the same time: the last move wins and both users see the final state within 2 seconds.
- A project has no tasks: all four columns display as empty.
- Input contains markup or script text: it is stored and displayed as plain text and never executed.
- A task refers to a user or project that does not exist: the request is rejected with a clear error.
- A very long title, description, or comment: rejected with a message stating the limit.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide five predefined users: one product manager and four engineers, each with a name and role.
- **FR-002**: System MUST let a person choose which predefined user they are acting as, without any login or password.
- **FR-003**: System MUST provide three pre-loaded sample projects, each with sample tasks spread across the columns.
- **FR-004**: System MUST display each project as a Kanban board with exactly four columns: To Do, In Progress, In Review, Done.
- **FR-005**: Users MUST be able to create projects with a name (1-100 characters, unique ignoring letter case) and an optional description (up to 1000 characters).
- **FR-006**: Users MUST be able to create tasks in a project with a title (1-150 characters) and an optional description (up to 2000 characters); new tasks start in To Do.
- **FR-007**: Users MUST be able to assign a task to one predefined user, change the assignment later, or clear it so the task is unassigned. Tasks MAY be created without an assignee. Any user can assign any task, regardless of its current assignee.
- **FR-008**: Any user MUST be able to move any task to any of the four columns, regardless of who is assigned, and the new status MUST persist across reloads.
- **FR-009**: Any user MUST be able to add comments (1-2000 characters) to any task in any project; each comment records its author and creation time and is shown in chronological order.
- **FR-010**: System MUST validate all user input (required fields, length limits, valid references) on the server side and reject invalid input without changing any data. The error message MUST name the affected field and state the rule that was broken (for example, "Title must be 1-150 characters"), without technical details.
- **FR-011**: System MUST treat all user-entered text as plain text so it can never run as code.
- **FR-012**: System MUST record which user performed each create, assign, move, and comment action and when it happened, and show the recent activity (action, user, time) on the task's detail view.
- **FR-013**: Product manager and engineers have the same permissions in this phase.
- **FR-014**: System MUST show changes to a board (task created, moved, or reassigned, comment added) to every other user viewing it within 2 seconds, without a manual reload, and MUST show the current board state after a lost connection is restored.
- **FR-015**: System MUST notify a user in-app when a task is assigned to them, and when another user comments on a task they are assigned to or have commented on. Users MUST NOT be notified of their own actions.
- **FR-016**: Users MUST be able to see their notifications, newest first, and mark each as read; unread notifications are visibly distinguished.

### Key Entities

- **User**: A predefined team member with a name and a role (product manager or engineer). Cannot be created or removed in this phase.
- **Project**: A named container of tasks with an optional description.
- **Task**: A unit of work belonging to one project, with title, optional description, status (one of the four columns), and at most one optional assignee (unassigned is valid).
- **Comment**: A message on a task, with author (User), text, and creation time.
- **Activity**: A record that a user created, assigned, or moved a task, with the action, the user, and the time.
- **Notification**: An in-app message for one user about a task assignment or a new comment, with the task, the user who caused it, and a read/unread state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can select an identity and open a project board in under 15 seconds from first opening the app.
- **SC-002**: A user can move a task to another column in under 5 seconds, and the change is visible after reload 100% of the time.
- **SC-003**: A user can create a task and assign it in under 1 minute.
- **SC-004**: 90% of first-time users complete the flow of creating a task, assigning it, moving it, and commenting without help.
- **SC-005**: 100% of invalid submissions (empty, over-length, or unknown references) are rejected with an understandable message and no data is changed.
- **SC-006**: A board with up to 100 tasks appears in under 1 second after opening, and moves, assignments and comments made by one user appear to other viewers within 2 seconds, for all five users working at once.

## Assumptions

- No authentication in this phase; identity selection is a convenience, not a security boundary. Login is planned for a later phase.
- The five users and three sample projects are pre-loaded; user management is out of scope.
- Tasks can move freely between any columns; no workflow restrictions.
- Editing and deleting tasks, projects, and comments is out of scope for this phase except task reassignment and moving.
- All users see all projects; no per-project membership.
- Desktop web browsers are the target; mobile layouts are out of scope.
- Boards update live for all viewers without a refresh, and users receive in-app notifications (email and push are out of scope). This replaces the earlier "refresh only" assumption.
- Constitution requirements (server-side validation, documentation, independently deployable services) apply during planning and implementation.
