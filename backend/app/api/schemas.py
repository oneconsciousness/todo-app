"""Request and response bodies, camelCase on the wire."""

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, StrictBool, StringConstraints, field_validator
from pydantic.alias_generators import to_camel

from app.domain.types import AccountCredentials, NewTask, TaskPatch


class WireModel(BaseModel):
    """Base for every body: camelCase names on the wire, snake_case in Python, immutable once built."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


class RequestModel(WireModel):
    """Base for request bodies: an unknown key is a client bug, so it fails validation."""

    model_config = ConfigDict(extra="forbid")


# Never stripped: spaces at either end are part of the password.
Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]


class Credentials(RequestModel):
    """Email and password, for both sign-up and sign-in, so sign-in looks up the same normalised email.

    `EmailStr` checks the syntax with email-validator and returns its normalised form: the domain
    lowercased and decoded from punycode, the whole address NFC-normalised, the local part's case kept
    (https://github.com/JoshData/python-email-validator#normalization).
    """

    email: EmailStr
    password: Password

    def to_domain(self) -> AccountCredentials:
        """Return the validated values as the auth service takes them."""
        return AccountCredentials(email=self.email, password=self.password)


class UserRead(WireModel):
    """The signed-in user as the client sees them; never the password hash."""

    id: UUID
    email: str


# Surrounding spaces are dropped, so a title of only spaces is empty and refused.
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Notes = Annotated[str, StringConstraints(max_length=5000)]


class TaskCreate(RequestModel):
    """A new task: a title, with optional notes and due date."""

    title: Title
    notes: Notes = ""
    due_date: date | None = None

    def to_domain(self) -> NewTask:
        """Return the validated values as the tasks service takes them."""
        return NewTask(title=self.title, notes=self.notes, due_date=self.due_date)


class TaskUpdate(RequestModel):
    """The fields to change on a task; any left out stay as they are.

    Only `dueDate` may be sent as null, which clears it. `completed` must be a JSON boolean: a string
    such as "true" is a client bug, so it fails validation instead of being coerced.
    """

    title: Title | None = None
    notes: Notes | None = None
    completed: StrictBool | None = None
    due_date: date | None = None

    @field_validator("title", "notes", "completed", mode="before")
    @classmethod
    def refuse_null(cls, value: object) -> object:
        """Refuse an explicit null; leaving a field out is how a client keeps it."""
        if value is None:
            raise ValueError("may not be null")
        return value

    def to_patch(self) -> TaskPatch:
        """Return only the fields the client sent, as the domain's patch."""
        return TaskPatch(**{name: getattr(self, name) for name in self.model_fields_set})


class TaskMove(RequestModel):
    """Where to put a task: right after `afterId`, or at the top when it is null. The key is required."""

    after_id: UUID | None


class TaskRead(WireModel):
    """One task as the client sees it."""

    id: UUID
    title: str
    notes: str
    completed: bool
    due_date: date | None
    rank: str
    version: int
    created_at: datetime
    updated_at: datetime


class TaskList(WireModel):
    """The user's tasks in rank order, in an envelope so paging can be added later."""

    items: list[TaskRead]


class ErrorDetail(WireModel):
    """One problem with one field; `field` is `None` when the problem is not tied to a field."""

    field: str | None
    message: str


class ErrorBody(WireModel):
    """A stable machine `code`, a `message` safe to show a user, and per-field details."""

    code: str
    message: str
    details: list[ErrorDetail] = []


class ErrorEnvelope(WireModel):
    """The one shape every error response has."""

    error: ErrorBody


class ProbeStatus(WireModel):
    """A health probe's answer."""

    status: Literal["alive", "ready"]
