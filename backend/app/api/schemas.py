"""Request and response bodies, camelCase on the wire."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints
from pydantic.alias_generators import to_camel


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


class UserRead(WireModel):
    """The signed-in user as the client sees them; never the password hash."""

    id: UUID
    email: str


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
