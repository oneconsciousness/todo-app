"""The signed-in user's tasks."""

import re
from typing import Annotated, Final
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.api.deps import CurrentUserDep, SessionDep
from app.api.schemas import ErrorEnvelope, TaskCreate, TaskList, TaskRead, TaskUpdate
from app.domain.errors import InvalidPrecondition
from app.domain.types import TaskRecord
from app.services import tasks as task_service

# No title is longer than 200 characters, and the cap bounds the trigram work a search can cause.
SearchTerm = Annotated[str | None, Query(max_length=200)]
QUOTED_VERSION: Final = re.compile(r'"([1-9][0-9]*)"')
# The version column is a Postgres integer.
LARGEST_VERSION: Final = 2**31 - 1

tasks_router = APIRouter(prefix="/tasks", tags=["tasks"], responses={401: {"model": ErrorEnvelope}})


def task_location(task_id: UUID) -> str:
    """Return the task's address, relative so it holds behind any proxy."""
    return f"/api/v1/tasks/{task_id}"


def read_with_etag(task: TaskRecord, response: Response) -> TaskRead:
    """Map the record to its wire shape and send its version as the ETag."""
    response.headers["ETag"] = f'"{task.version}"'
    return TaskRead.model_validate(task, from_attributes=True)


@tasks_router.get("", responses={400: {"model": ErrorEnvelope}})
async def list_tasks(claims: CurrentUserDep, session: SessionDep, q: SearchTerm = None) -> TaskList:
    """Return the user's tasks in their order, or only those whose title or notes contain `q`."""
    tasks = await task_service.list_tasks(session, claims.user_id, q)
    return TaskList(items=[TaskRead.model_validate(task, from_attributes=True) for task in tasks])


@tasks_router.post("", status_code=status.HTTP_201_CREATED, responses={400: {"model": ErrorEnvelope}})
async def create_task(body: TaskCreate, response: Response, claims: CurrentUserDep, session: SessionDep) -> TaskRead:
    """Create a task at the top of the list."""
    task = await task_service.create_task(session, claims.user_id, body.to_domain())
    response.headers["Location"] = task_location(task.id)
    return read_with_etag(task, response)


@tasks_router.get("/{task_id}", responses={400: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}})
async def get_task(task_id: UUID, response: Response, claims: CurrentUserDep, session: SessionDep) -> TaskRead:
    """Return one task."""
    return read_with_etag(await task_service.get_task(session, claims.user_id, task_id), response)


def expected_version(if_match: Annotated[str | None, Header()] = None) -> int | None:
    """Read the version an edit is based on from If-Match, written as the ETag was: a quoted number.

    Raises:
        InvalidPrecondition: when the header is anything else, or larger than the version column holds.
    """
    if if_match is None:
        return None
    match = QUOTED_VERSION.fullmatch(if_match)
    if match is None or int(match[1]) > LARGEST_VERSION:
        raise InvalidPrecondition
    return int(match[1])


@tasks_router.patch(
    "/{task_id}",
    responses={400: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}, 412: {"model": ErrorEnvelope}},
)
async def update_task(
    task_id: UUID,
    body: TaskUpdate,
    response: Response,
    claims: CurrentUserDep,
    session: SessionDep,
    if_match: Annotated[int | None, Depends(expected_version)],
) -> TaskRead:
    """Change the fields sent; with If-Match, only if the task is still that version (412 otherwise)."""
    task = await task_service.update_task(session, claims.user_id, task_id, body.to_patch(), if_match)
    return read_with_etag(task, response)
