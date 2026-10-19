"""Request and response bodies, camelCase on the wire."""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class WireModel(BaseModel):
    """Base for every body: camelCase names on the wire, snake_case in Python, immutable once built."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)


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
