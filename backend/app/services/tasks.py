"""Task use cases. Each opens its one transaction itself."""

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import tasks as task_rows
from app.domain.errors import TaskNotFound, VersionMismatch
from app.domain.patch import apply_patch
from app.domain.ranks import rank_between
from app.domain.search import normalize_query, search_pattern
from app.domain.types import NewTask, TaskPatch, TaskRecord


async def list_tasks(session: AsyncSession, owner_id: UUID, q: str | None) -> list[TaskRecord]:
    """Return the owner's tasks in their order, only those whose title or notes contain `q` when it is not blank."""
    pattern = search_pattern(term) if (term := normalize_query(q)) else None
    async with session.begin():
        return await task_rows.list_tasks(session, owner_id, pattern)


async def get_task(session: AsyncSession, owner_id: UUID, task_id: UUID) -> TaskRecord:
    """Return one of the owner's tasks.

    Raises:
        TaskNotFound: when it is missing or belongs to someone else.
    """
    async with session.begin():
        task = await task_rows.get_task(session, owner_id, task_id)
    if task is None:
        raise TaskNotFound
    return task


async def update_task(
    session: AsyncSession, owner_id: UUID, task_id: UUID, patch: TaskPatch, if_match: int | None
) -> TaskRecord:
    """Apply the fields the client sent; with `if_match`, only if the task is still that version.

    Raises:
        EmptyPatch: when no field was sent.
        TaskNotFound: when the task is missing or belongs to someone else.
        VersionMismatch: when the task exists but has moved past `if_match`.
    """
    changes = apply_patch(patch)
    async with session.begin():
        task = await task_rows.update_task(session, owner_id, task_id, changes, expected_version=if_match)
        # Nothing matched: either the task is not this user's, or its version moved on.
        if task is None and await task_rows.get_task(session, owner_id, task_id) is not None:
            raise VersionMismatch
    if task is None:
        raise TaskNotFound
    return task


async def create_task(session: AsyncSession, owner_id: UUID, new_task: NewTask) -> TaskRecord:
    """Create a task at the top of the owner's list."""
    async with session.begin():
        top = await task_rows.first_rank(session, owner_id)
        return await task_rows.insert_task(
            session, owner_id, uuid4(), new_task.title, new_task.notes, new_task.due_date, rank_between(None, top)
        )
