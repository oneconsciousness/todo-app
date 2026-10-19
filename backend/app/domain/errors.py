"""Errors the domain and services raise. They carry no HTTP knowledge; the API maps each one to a status."""


class DomainError(Exception):
    """Base class for every error a client can cause."""


class EmptyPatch(DomainError):
    """An update sent no fields to change."""


class NotAuthenticated(DomainError):
    """The request has no session, or its session token is invalid or expired."""


class InvalidCredentials(DomainError):
    """The email is unknown or the password is wrong; the two are never told apart."""


class ForbiddenOrigin(DomainError):
    """A write came from a page on another origin."""


class EmailTaken(DomainError):
    """An account already uses this email, in any letter case."""


class TaskNotFound(DomainError):
    """No task with this id belongs to the signed-in user; another user's task counts as missing."""


class InvalidPrecondition(DomainError):
    """The If-Match header is not a quoted positive version number."""


class VersionMismatch(DomainError):
    """The task changed since the version the client named, so the edit was not applied."""
