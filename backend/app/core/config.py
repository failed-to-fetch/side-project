from functools import lru_cache

from cryptography.fernet import Fernet
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All backend configuration. Values come from environment variables
    (case-insensitive), falling back to backend/.env when run outside Docker."""

    # hide_input_in_errors keeps secrets out of startup tracebacks.
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    database_url: str
    redis_url: str

    # Fernet key for encrypting provider tokens at rest.
    token_encryption_key: SecretStr

    # GitHub App used for repository access (not for sign-in).
    github_client_id: str = ""
    github_client_secret: SecretStr = SecretStr("")
    github_redirect_uri: str = "http://localhost:8000/auth/github/callback"

    # Better Auth owns sign-in; the backend asks it who a session belongs to.
    auth_service_url: str = "http://auth:3001"
    # How long a checked session is cached, so also how long a sign-out takes to apply here.
    auth_session_cache_seconds: int = 60

    frontend_url: str = "http://localhost:3000"
    cookie_secure: bool = False

    @field_validator("token_encryption_key")
    @classmethod
    def _valid_fernet_key(cls, v: SecretStr) -> SecretStr:
        try:
            Fernet(v.get_secret_value())
        except ValueError as e:
            raise ValueError(
                "must be a Fernet key; generate one with scripts/generate-encryption-key.sh"
            ) from e
        return v

    @field_validator("frontend_url", "auth_service_url")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
