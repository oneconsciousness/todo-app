"""Values that flow through the domain core."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum, auto
from typing import TypedDict
from uuid import UUID


class Unset(Enum):
    """Marks a patch field the client did not send, which differs from sending `null`."""

    UNSET = auto()


@dataclass(frozen=True)
class TaskPatch:
    """The fields a client asked to change on a task; anything left `UNSET` stays as it is."""

    title: str | Unset = Unset.UNSET
    notes: str | Unset = Unset.UNSET
    completed: bool | Unset = Unset.UNSET
    due_date: date | Unset | None = Unset.UNSET


class TaskChanges(TypedDict, total=False):
    """Column values for an update, holding only the fields that were sent."""

    title: str
    notes: str
    completed: bool
    due_date: date | None


@dataclass(frozen=True)
class SessionClaims:
    """Who a session token belongs to, and when it was issued and expires."""

    user_id: UUID
    issued_at: datetime
    expires_at: datetime
