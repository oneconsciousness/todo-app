import pytest
from pydantic import ValidationError

from app.config import EXAMPLE_JWT_SECRET, Settings

DATABASE_URL = "postgresql+asyncpg://todo:todo@localhost:5432/todo"


def test_settings_refuse_the_example_jwt_secret_with_secure_cookies() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(database_url=DATABASE_URL, jwt_secret=EXAMPLE_JWT_SECRET, cookie_secure=True)


def test_settings_allow_the_example_jwt_secret_over_local_http() -> None:
    settings = Settings(database_url=DATABASE_URL, jwt_secret=EXAMPLE_JWT_SECRET, cookie_secure=False)
    assert settings.jwt_secret.get_secret_value() == EXAMPLE_JWT_SECRET
