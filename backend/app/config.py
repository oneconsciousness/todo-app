"""Settings read from environment variables."""

from typing import Final, Literal, Self

from pydantic import Field, PostgresDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The JWT_SECRET value in .env.example. Change both together.
EXAMPLE_JWT_SECRET: Final = "local-dev-jwt-secret-change-me-0123456789abcdef"


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

    @model_validator(mode="after")
    def refuse_the_example_secret_with_secure_cookies(self) -> Self:
        """Refuse the public example secret when cookies are Secure, since that means the app runs beyond a laptop."""
        if self.cookie_secure and self.jwt_secret.get_secret_value() == EXAMPLE_JWT_SECRET:
            raise ValueError("JWT_SECRET is the example value from .env.example; set a real secret")
        return self
