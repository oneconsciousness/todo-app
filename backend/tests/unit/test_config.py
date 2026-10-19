import pytest
from pydantic import ValidationError

from app.config import EXAMPLE_JWT_SECRET, Settings

DATABASE_URL = "postgresql+asyncpg://todo:todo@localhost:5432/todo"
SIGNING_KEY = "unit-test-signing-key-0123456789abcdef"


def test_settings_refuse_the_example_jwt_secret_with_secure_cookies() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(database_url=DATABASE_URL, jwt_secret=EXAMPLE_JWT_SECRET, cookie_secure=True)


def test_settings_strip_a_trailing_slash_from_the_app_origin() -> None:
    settings = Settings(database_url=DATABASE_URL, jwt_secret=SIGNING_KEY, app_origin="https://todo.example.com/")
    assert settings.app_origin == "https://todo.example.com"


@pytest.mark.parametrize(
    "origin",
    [
        "localhost:8080",
        "ftp://todo.example.com",
        "https://todo.example.com/app",
        "https://todo.example.com?next=1",
        "https://user@todo.example.com",
        "https://todo.example.com:not-a-port",
    ],
    ids=["no-scheme", "other-scheme", "path", "query", "credentials", "bad-port"],
)
def test_settings_refuse_an_app_origin_that_is_not_scheme_host_and_port(origin: str) -> None:
    with pytest.raises(ValidationError, match="APP_ORIGIN"):
        Settings(database_url=DATABASE_URL, jwt_secret=SIGNING_KEY, app_origin=origin)


def test_settings_allow_the_example_jwt_secret_over_local_http() -> None:
    settings = Settings(database_url=DATABASE_URL, jwt_secret=EXAMPLE_JWT_SECRET, cookie_secure=False)
    assert settings.jwt_secret.get_secret_value() == EXAMPLE_JWT_SECRET
