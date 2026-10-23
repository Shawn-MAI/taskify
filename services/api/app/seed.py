"""Idempotent seed data: five users and three sample projects with tasks."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Project, Role, Status, Task, User

USERS = [
    ("Avery Morgan", Role.product_manager),
    ("Blake Chen", Role.engineer),
    ("Casey Patel", Role.engineer),
    ("Devon Rivera", Role.engineer),
    ("Emery Okafor", Role.engineer),
]

# project name, description, [(title, status, assignee index or None)]
PROJECTS = [
    (
        "Website Redesign",
        "Refresh the marketing site.",
        [
            ("Collect design references", Status.todo, 0),
            ("Draft new homepage layout", Status.todo, 1),
            ("Build navigation component", Status.in_progress, 2),
            ("Review accessibility audit", Status.in_review, 3),
            ("Publish brand colour palette", Status.done, 0),
        ],
    ),
    (
        "Mobile App Launch",
        "Ship the first public mobile release.",
        [
            ("Write release notes", Status.todo, None),
            ("Fix login crash on Android", Status.in_progress, 4),
            ("Prepare store screenshots", Status.in_progress, 0),
            ("QA regression pass", Status.in_review, 2),
            ("Set up crash reporting", Status.done, 1),
            ("Register developer accounts", Status.done, 0),
        ],
    ),
    (
        "Internal Tooling",
        "Small tools that save the team time.",
        [
            ("Evaluate CI speed-ups", Status.todo, 3),
            ("Automate weekly report", Status.in_progress, 1),
            ("Document on-call runbook", Status.in_review, 4),
            ("Retire legacy cron jobs", Status.done, 2),
        ],
    ),
]


def seed(session: Session) -> None:
    """Insert seed data if the database has no users yet (safe to call repeatedly)."""
    if session.scalar(select(User.id).limit(1)) is not None:
        return
    users = [User(name=name, role=role) for name, role in USERS]
    session.add_all(users)
    session.flush()
    creator = users[0]
    for name, description, tasks in PROJECTS:
        project = Project(name=name, description=description, created_by=creator.id)
        session.add(project)
        session.flush()
        positions: dict[Status, int] = {}
        for title, status, assignee in tasks:
            pos = positions.get(status, 0)
            positions[status] = pos + 1
            session.add(
                Task(
                    project_id=project.id,
                    title=title,
                    status=status,
                    position=pos,
                    assignee_id=users[assignee].id if assignee is not None else None,
                    created_by=creator.id,
                )
            )
    session.commit()
