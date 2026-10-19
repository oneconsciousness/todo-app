"""Table mappings for queries. The schema itself is created by the alembic migrations."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, false, func, text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for the tables below."""


class User(Base):
    """A person who can sign in."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(CITEXT)
    password_hash: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Task(Base):
    """One item on a user's list. There are no relationships: every query names its owner."""

    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, server_default=text("''"))
    completed: Mapped[bool] = mapped_column(server_default=false())
    due_date: Mapped[date | None]
    rank: Mapped[str] = mapped_column(Text(collation="C"))
    version: Mapped[int] = mapped_column(server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
