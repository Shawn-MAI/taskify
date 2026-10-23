"""Project endpoints: list, board view, create."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_session
from ..models import Project, Status, Task, User
from ..schemas import BoardOut, Columns, ProjectCreate, ProjectOut, TaskOut
from ..security import get_acting_user

router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    _user: User = Depends(get_acting_user), session: Session = Depends(get_session)
) -> list[Project]:
    """Return all projects ordered by id. Errors: 401, 404/422 for the acting user."""
    return list(session.scalars(select(Project).order_by(Project.id)))


@router.get("/projects/{project_id}", response_model=BoardOut)
def get_board(
    project_id: int,
    _user: User = Depends(get_acting_user),
    session: Session = Depends(get_session),
) -> BoardOut:
    """Return a project with its tasks grouped into the four columns by position.

    Errors: 404 when the project does not exist.
    """
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    tasks = session.scalars(
        select(Task).where(Task.project_id == project_id).order_by(Task.position, Task.id)
    )
    grouped: dict[str, list[TaskOut]] = {s.value: [] for s in Status}
    for task in tasks:
        grouped[task.status.value].append(TaskOut.model_validate(task))
    return BoardOut(project=ProjectOut.model_validate(project), columns=Columns(**grouped))


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(
    body: ProjectCreate,
    user: User = Depends(get_acting_user),
    session: Session = Depends(get_session),
) -> Project:
    """Create a project. Errors: 409 when the name exists ignoring case, 422 invalid input."""
    if session.scalar(select(Project.id).where(func.lower(Project.name) == body.name.lower())):
        raise HTTPException(status_code=409, detail="A project with this name already exists")
    project = Project(name=body.name, description=body.description, created_by=user.id)
    session.add(project)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="A project with this name already exists")
    return project
