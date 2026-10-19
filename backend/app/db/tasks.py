"""Queries on the tasks table. Every one filters on the owner, so no query can reach another user's task."""

from datetime import date
from uuid import UUID

from sqlalchemy import ColumnElement, delete, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Task
from app.domain.types import TaskChanges, TaskRecord


async def lock_task_order(session: AsyncSession, owner_id: UUID) -> None:
    """Hold the owner's order lock until the transaction ends, so their creates and moves pick ranks one at a time."""
    # One lock per user, keyed by a hash of the id; other users never wait. https://www.postgresql.org/docs/18/explicit-locking.html#ADVISORY-LOCKS
    await session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(str(owner_id), 0))))


async def first_rank(session: AsyncSession, owner_id: UUID) -> str | None:
    """Return the rank of the owner's top task, or `None` when the list is empty."""
    rank: str | None = await session.scalar(
        select(Task.rank).where(Task.owner_id == owner_id).order_by(Task.rank).limit(1)
    )
    return rank


async def rank_of(session: AsyncSession, owner_id: UUID, task_id: UUID) -> str | None:
    """Return the rank of one of the owner's tasks, or `None` when it is missing or someone else's."""
    rank: str | None = await session.scalar(select(Task.rank).where(Task.id == task_id, Task.owner_id == owner_id))
    return rank


async def next_rank_after(session: AsyncSession, owner_id: UUID, rank: str, excluding: UUID) -> str | None:
    """Return the first rank below `rank` in the owner's list, skipping the task being moved."""
    statement = (
        select(Task.rank)
        .where(Task.owner_id == owner_id, Task.rank > rank, Task.id != excluding)
        .order_by(Task.rank)
        .limit(1)
    )
    next_rank: str | None = await session.scalar(statement)
    return next_rank


async def first_rank_excluding(session: AsyncSession, owner_id: UUID, excluding: UUID) -> str | None:
    """Return the owner's top rank, skipping the task being moved."""
    statement = select(Task.rank).where(Task.owner_id == owner_id, Task.id != excluding).order_by(Task.rank).limit(1)
    rank: str | None = await session.scalar(statement)
    return rank


async def set_rank(session: AsyncSession, owner_id: UUID, task_id: UUID, rank: str) -> TaskRecord | None:
    """Give a task a new rank, leaving its version and updated time as they are."""
    statement = update(Task).where(Task.id == task_id, Task.owner_id == owner_id).values(rank=rank).returning(Task)
    task = await session.scalar(statement)
    return TaskRecord.model_validate(task) if task is not None else None


async def delete_task(session: AsyncSession, owner_id: UUID, task_id: UUID) -> bool:
    """Delete one of the owner's tasks; return whether there was one to delete."""
    statement = delete(Task).where(Task.id == task_id, Task.owner_id == owner_id).returning(Task.id)
    return await session.scalar(statement) is not None


async def insert_task(
    session: AsyncSession, owner_id: UUID, task_id: UUID, title: str, notes: str, due_date: date | None, rank: str
) -> TaskRecord:
    """Insert a task and return the stored row, with its server defaults filled in."""
    statement = (
        insert(Task)
        .values(id=task_id, owner_id=owner_id, title=title, notes=notes, due_date=due_date, rank=rank)
        .returning(Task)
    )
    return TaskRecord.model_validate((await session.scalars(statement)).one())


def search_condition(pattern: str) -> ColumnElement[bool]:
    """Match tasks whose title or notes contain the search, ignoring case.

    The pattern is a bound parameter with `\\` as its escape character, so its `%` and `_` match literally
    (https://www.postgresql.org/docs/18/functions-matching.html#FUNCTIONS-LIKE). The trigram index can
    answer both halves of the OR (https://www.postgresql.org/docs/18/pgtrgm.html#PGTRGM-INDEX).
    """
    return or_(Task.title.ilike(pattern, escape="\\"), Task.notes.ilike(pattern, escape="\\"))


async def list_tasks(session: AsyncSession, owner_id: UUID, pattern: str | None) -> list[TaskRecord]:
    """Return the owner's tasks in rank order, only those matching `pattern` when one is given."""
    statement = select(Task).where(Task.owner_id == owner_id).order_by(Task.rank)
    if pattern is not None:
        statement = statement.where(search_condition(pattern))
    return [TaskRecord.model_validate(task) for task in await session.scalars(statement)]


async def update_task(
    session: AsyncSession, owner_id: UUID, task_id: UUID, changes: TaskChanges, expected_version: int | None
) -> TaskRecord | None:
    """Write the changes, bump the version and stamp the time, in one conditional UPDATE.

    With `expected_version`, the row changes only if it is still that version, so two edits from the
    same version cannot both land. Returns `None` when no row matched.
    """
    version_check = (Task.version == expected_version,) if expected_version is not None else ()
    statement = (
        update(Task)
        .where(Task.id == task_id, Task.owner_id == owner_id, *version_check)
        .values(**changes, version=Task.version + 1, updated_at=func.now())
        .returning(Task)
    )
    task = await session.scalar(statement)
    return TaskRecord.model_validate(task) if task is not None else None


async def get_task(session: AsyncSession, owner_id: UUID, task_id: UUID) -> TaskRecord | None:
    """Return one of the owner's tasks, or `None` when it is missing or belongs to someone else."""
    task = await session.scalar(select(Task).where(Task.id == task_id, Task.owner_id == owner_id))
    return TaskRecord.model_validate(task) if task is not None else None
