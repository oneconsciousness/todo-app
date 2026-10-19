from app.api.errors import STATUS_BY_ERROR
from app.domain.errors import DomainError


def all_subclasses(cls: type[DomainError]) -> set[type[DomainError]]:
    """Return every class below `cls`, however deep."""
    return {sub for direct in cls.__subclasses__() for sub in {direct, *all_subclasses(direct)}}


def test_every_domain_error_has_a_status_and_code() -> None:
    assert all_subclasses(DomainError) <= STATUS_BY_ERROR.keys()
