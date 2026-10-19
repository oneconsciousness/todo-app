"""Settings read from environment variables."""

from typing import Final, Literal, Self
from urllib.parse import SplitResult, urlsplit

from pydantic import Field, PostgresDsn, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The JWT_SECRET value in .env.example. Change both together.
EXAMPLE_JWT_SECRET: Final = "local-dev-jwt-secret-change-me-0123456789abcdef"


def has_a_valid_port(parts: SplitResult) -> bool:
    """Return whether the URL has no port or a positive numeric one; reading a malformed port raises."""
    try:
        return parts.port is None or parts.port > 0
    except ValueError:
        return False


class DatabaseSettings(BaseSettings):
    """The one setting migrations need, so the migrate container never sees the JWT secret."""

    model_config = SettingsConfigDict(extra="ignore", frozen=True, case_sensitive=False)

    database_url: PostgresDsn


class Settings(DatabaseSettings):
    """Everything the API reads from its environment."""

    jwt_secret: SecretStr = Field(min_length=32)
    app_origin: str = "http://localhost:8080"
    cookie_secure: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    db_pool_size: int = 10
    db_max_overflow: int = 5
    db_pool_timeout_seconds: float = 5.0

    @field_validator("app_origin")
    @classmethod
    def normalise_the_app_origin(cls, value: str) -> str:
        """Drop a trailing slash and require `scheme://host[:port]`, the exact form browsers send in Origin.

        A slash or a path would never equal a browser's Origin header, and every write would get 403
        (https://fetch.spec.whatwg.org/#origin-header).
        """
        origin = value.rstrip("/")
        parts = urlsplit(origin)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or not has_a_valid_port(parts):
            raise ValueError("APP_ORIGIN must be http(s)://host[:port]")
        if parts.path or parts.query or parts.fragment:
            raise ValueError("APP_ORIGIN must not have a path, query or fragment")
        return origin

    @model_validator(mode="after")
    def refuse_the_example_secret_with_secure_cookies(self) -> Self:
        """Refuse the public example secret when cookies are Secure, since that means the app runs beyond a laptop."""
        if self.cookie_secure and self.jwt_secret.get_secret_value() == EXAMPLE_JWT_SECRET:
            raise ValueError("JWT_SECRET is the example value from .env.example; set a real secret")
        return self
