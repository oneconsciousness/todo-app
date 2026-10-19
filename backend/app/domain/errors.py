"""Errors the domain and services raise. They carry no HTTP knowledge; the API maps each one to a status."""


class DomainError(Exception):
    """Base class for every error a client can cause."""


class EmptyPatch(DomainError):
    """An update sent no fields to change."""
