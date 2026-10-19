"""Queries on the tasks table. Every one filters on the owner, so no query can reach another user's task."""

from datetime import date
from uuid import UUID

from sqlalchemy import ColumnElement, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Task
from app.domain.types import TaskRecord


async def first_rank(session: AsyncSession, owner_id: UUID) -> str | None:
    """Return the rank of the owner's top task, or `None` when the list is empty."""
    rank: str | None = await session.scalar(
        select(Task.rank).where(Task.owner_id == owner_id).order_by(Task.rank).limit(1)
    )
    return rank


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


async def get_task(session: AsyncSession, owner_id: UUID, task_id: UUID) -> TaskRecord | None:
    """Return one of the owner's tasks, or `None` when it is missing or belongs to someone else."""
    task = await session.scalar(select(Task).where(Task.id == task_id, Task.owner_id == owner_id))
    return TaskRecord.model_validate(task) if task is not None else None
