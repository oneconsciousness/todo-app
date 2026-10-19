"""Values that flow through the domain core."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum, auto
from typing import TypedDict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class SessionClaims(BaseModel):
    """Who a session token belongs to, and when it was issued and expires, read from the JWT's claims."""

    # JWT times are whole seconds since the epoch, never milliseconds (https://www.rfc-editor.org/rfc/rfc7519#section-2).
    model_config = ConfigDict(frozen=True, val_temporal_unit="seconds")

    user_id: UUID = Field(alias="sub")
    issued_at: datetime = Field(alias="iat")
    expires_at: datetime = Field(alias="exp")
