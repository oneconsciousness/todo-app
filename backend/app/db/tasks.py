"""Queries on the tasks table. Every one filters on the owner, so no query can reach another user's task."""

from datetime import date
from uuid import UUID

from sqlalchemy import insert, select
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


async def list_tasks(session: AsyncSession, owner_id: UUID) -> list[TaskRecord]:
    """Return the owner's tasks in rank order."""
    tasks = await session.scalars(select(Task).where(Task.owner_id == owner_id).order_by(Task.rank))
    return [TaskRecord.model_validate(task) for task in tasks]


async def get_task(session: AsyncSession, owner_id: UUID, task_id: UUID) -> TaskRecord | None:
    """Return one of the owner's tasks, or `None` when it is missing or belongs to someone else."""
    task = await session.scalar(select(Task).where(Task.id == task_id, Task.owner_id == owner_id))
    return TaskRecord.model_validate(task) if task is not None else None
