"""Turn every error into the one error envelope, and map domain errors to HTTP in one table."""

import logging
from collections.abc import Callable, Coroutine, Mapping, Sequence
from types import MappingProxyType
from typing import Any, Final, NamedTuple

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.api.schemas import ErrorBody, ErrorDetail, ErrorEnvelope
from app.domain.errors import (
    DomainError,
    EmailTaken,
    EmptyPatch,
    ForbiddenOrigin,
    InvalidCredentials,
    NotAuthenticated,
)

log = logging.getLogger(__name__)


class HttpError(NamedTuple):
    """How one kind of error looks on the wire; `field` names the one field it concerns, if any."""

    status: int
    code: str
    message: str
    field: str | None = None


STATUS_BY_ERROR: Final[Mapping[type[DomainError], HttpError]] = MappingProxyType(
    {
        EmptyPatch: HttpError(400, "validation_failed", "Send at least one field to change."),
        NotAuthenticated: HttpError(401, "not_authenticated", "Sign in to continue."),
        InvalidCredentials: HttpError(401, "invalid_credentials", "The email or password is wrong."),
        ForbiddenOrigin: HttpError(403, "forbidden_origin", "This request came from another site."),
        EmailTaken: HttpError(409, "email_taken", "An account with this email already exists.", field="email"),
    }
)

HTTP_EXCEPTION_ERRORS: Final[Mapping[int, HttpError]] = MappingProxyType(
    {
        404: HttpError(404, "not_found", "There is nothing at this address."),
        405: HttpError(405, "method_not_allowed", "This address does not accept that method."),
    }
)

# A pool wait that ran out, a statement timeout, or a database that cannot be reached. OSError covers
# a refused or timed-out connection and a host name that does not resolve (socket.gaierror).
DATABASE_ERRORS: Final = (PoolTimeoutError, OperationalError, InterfaceError, OSError)

VALIDATION_FAILED: Final = HttpError(400, "validation_failed", "Some fields are not valid.")
SERVICE_UNAVAILABLE: Final = HttpError(503, "service_unavailable", "The service is busy. Try again in a moment.")
INTERNAL_ERROR: Final = HttpError(500, "internal_error", "Something went wrong on our side.")


def error_response(
    error: HttpError, details: Sequence[ErrorDetail] = (), headers: Mapping[str, str] | None = None
) -> JSONResponse:
    """Build the envelope response for an error."""
    body = ErrorEnvelope(error=ErrorBody(code=error.code, message=error.message, details=list(details)))
    return JSONResponse(body.model_dump(mode="json", by_alias=True), status_code=error.status, headers=headers)


def field_name(location: Sequence[str | int]) -> str | None:
    """Return the last name in a validation error's location, which is the field's camelCase wire name."""
    return next((part for part in reversed(location) if isinstance(part, str)), None)


async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    """Answer 400, not FastAPI's default 422, with one detail per field; log the field names, never the values."""
    details = [ErrorDetail(field=field_name(item["loc"]), message=item["msg"]) for item in error.errors()]
    log.warning(
        "request failed validation",
        extra={"where": "app.api.errors.handle_validation_error", "fields": [d.field for d in details], "then": 400},
    )
    return error_response(VALIDATION_FAILED, details)


async def handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
    """Answer with the status and code the table gives the error's type."""
    reply = STATUS_BY_ERROR[type(error)]
    details = [ErrorDetail(field=reply.field, message=reply.message)] if reply.field else []
    return error_response(reply, details)


async def handle_http_exception(request: Request, error: StarletteHTTPException) -> JSONResponse:
    """Wrap the router's own 404 and 405 in the envelope, keeping headers such as `Allow`."""
    reply = HTTP_EXCEPTION_ERRORS.get(error.status_code, HttpError(error.status_code, "http_error", str(error.detail)))
    return error_response(reply, headers=error.headers)


async def handle_database_error(request: Request, error: Exception) -> JSONResponse:
    """Answer 503 when the database is slow, saturated or down."""
    # A DBAPIError's own text can quote the SQL and its parameters, so only the driver's error is logged.
    cause = error.orig if isinstance(error, DBAPIError) else error
    log.warning(
        "database unavailable",
        extra={"where": "app.api.errors.handle_database_error", "why": f"{type(cause).__name__}: {cause}", "then": 503},
    )
    return error_response(SERVICE_UNAVAILABLE)


async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    """Answer 500 without revealing anything, and log the traceback."""
    log.error("unhandled error", exc_info=error, extra={"where": request.url.path, "then": 500})
    return error_response(INTERNAL_ERROR)


type ExceptionHandler = Callable[[Request, Any], Coroutine[Any, Any, Response]]


def exception_handlers() -> dict[int | type[Exception], ExceptionHandler]:
    """Return every handler, keyed by the error type it answers; Starlette picks the closest match."""
    return {
        RequestValidationError: handle_validation_error,
        DomainError: handle_domain_error,
        StarletteHTTPException: handle_http_exception,
        **dict.fromkeys(DATABASE_ERRORS, handle_database_error),
        Exception: handle_unexpected_error,
    }
